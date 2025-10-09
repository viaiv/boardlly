from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.security import clear_session, ensure_password_strength, establish_session
from app.models.account import Account
from app.models.user import AppUser
from app.models.project_invite import ProjectInvite
from app.models.github_project import GithubProject
from app.models.project_member import ProjectMember
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    ResendVerificationRequest,
    UserResponse,
    VerifyEmailRequest,
)
from app.services.auth import (
    authenticate_user,
    count_users,
    create_user,
    get_user_by_email,
)
from app.services.email import send_email_verification
from app.core.security import generate_verification_token
from datetime import datetime, timedelta, timezone
from sqlalchemy import select

router = APIRouter(prefix="/auth", tags=["auth"])


def build_user_response(user: AppUser) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        account_id=user.account_id,
        needs_account_setup=user.account_id is None,
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    payload: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser | None = Depends(deps.get_optional_current_user),
) -> UserResponse:
    total_users = await count_users(db)
    email_exists = await get_user_by_email(db, payload.email)
    if email_exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="E-mail já cadastrado")

    ensure_password_strength(payload.password)

    account: Account | None = None
    role: str
    project_invite: ProjectInvite | None = None
    is_invite_registration = False

    # Verificar se há um token de convite
    if payload.invite_token:
        # Buscar convite pelo token
        stmt = select(ProjectInvite).where(
            ProjectInvite.invite_token == payload.invite_token,
            ProjectInvite.status == "pending"
        )
        result = await db.execute(stmt)
        project_invite = result.scalar_one_or_none()

        if not project_invite:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                detail="Convite inválido ou já utilizado"
            )

        # Verificar se o email corresponde ao convite
        if project_invite.invited_email.lower() != payload.email.lower():
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=f"Este convite foi enviado para {project_invite.invited_email}. Use o email correto."
            )

        # Buscar o projeto e a conta associada
        project = await db.get(GithubProject, project_invite.project_id)
        if not project:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                detail="Projeto não encontrado"
            )

        account = await db.get(Account, project.account_id)
        if not account:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                detail="Conta não encontrada"
            )

        # Usar role do convite
        role = project_invite.role
        is_invite_registration = True

    elif total_users == 0:
        # Primeiro usuário do sistema
        role = "owner"
    else:
        # Registro manual (requer autenticação ou convite)
        if current_user is None:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail="Você precisa de um convite para se registrar na plataforma. Entre em contato com o administrador."
            )
        if current_user.role not in {"admin", "owner"}:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Permissão insuficiente")
        account = await db.get(Account, current_user.account_id)
        if not account:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Conta não encontrada")
        role = payload.role

    # Criar usuário
    user = await create_user(
        db,
        account=account,
        email=payload.email,
        password=payload.password,
        role=role,
        name=payload.name,
    )

    # Tratamento pós-criação
    if is_invite_registration and project_invite:
        # Usuário via convite: verificar email automaticamente e criar membro do projeto
        user.email_verified = True
        user.email_verification_token = None
        user.email_verification_token_expires = None

        # Criar ProjectMember
        project_member = ProjectMember(
            project_id=project_invite.project_id,
            user_id=user.id,
            role=project_invite.role
        )
        db.add(project_member)

        # Marcar convite como aceito
        project_invite.status = "accepted"

        # Fazer login automático
        establish_session(request, str(user.id))

    elif total_users == 0:
        # Primeiro usuário (owner) é verificado automaticamente
        user.email_verified = True
        user.email_verification_token = None
        user.email_verification_token_expires = None
        establish_session(request, str(user.id))
    else:
        # Enviar email de verificação para novos usuários (registro manual)
        try:
            await send_email_verification(
                to_email=user.email,
                verification_token=user.email_verification_token,
                user_name=user.name,
            )
        except Exception as e:
            # Log error but don't fail registration
            print(f"⚠️  Falha ao enviar email de verificação: {e}")

    await db.commit()
    await db.refresh(user)

    return build_user_response(user)


@router.post("/login", response_model=UserResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(deps.get_db),
) -> UserResponse:
    user = await authenticate_user(db, payload.email, payload.password)
    establish_session(request, str(user.id))
    await db.commit()
    await db.refresh(user)
    return build_user_response(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def logout(request: Request) -> Response:
    clear_session(request)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/verify-email", status_code=status.HTTP_200_OK)
async def verify_email(
    payload: VerifyEmailRequest,
    db: AsyncSession = Depends(deps.get_db),
) -> dict[str, str]:
    """
    Verifica o email de um usuário usando o token enviado por email.
    """
    # Buscar usuário com o token
    stmt = select(AppUser).where(AppUser.email_verification_token == payload.token)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail="Token de verificação inválido"
        )

    # Verificar se o token expirou
    if user.email_verification_token_expires and user.email_verification_token_expires < datetime.now(timezone.utc):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Token de verificação expirado. Solicite um novo email de verificação."
        )

    # Verificar email
    user.email_verified = True
    user.email_verification_token = None
    user.email_verification_token_expires = None

    await db.commit()

    return {"message": "Email verificado com sucesso! Você já pode fazer login."}


@router.post("/resend-verification", status_code=status.HTTP_200_OK)
async def resend_verification(
    payload: ResendVerificationRequest,
    db: AsyncSession = Depends(deps.get_db),
) -> dict[str, str]:
    """
    Reenvia o email de verificação para um usuário.
    """
    user = await get_user_by_email(db, payload.email)

    if not user:
        # Por segurança, não revela se o email existe ou não
        return {"message": "Se o email existir, um novo link de verificação foi enviado."}

    # Se já verificado, retorna mensagem genérica
    if user.email_verified:
        return {"message": "Se o email existir, um novo link de verificação foi enviado."}

    # Gerar novo token e expiração
    new_token = generate_verification_token()
    user.email_verification_token = new_token
    user.email_verification_token_expires = datetime.now(timezone.utc) + timedelta(hours=24)

    await db.commit()

    # Enviar email
    try:
        await send_email_verification(
            to_email=user.email,
            verification_token=new_token,
            user_name=user.name,
        )
    except Exception as e:
        print(f"⚠️  Falha ao enviar email de verificação: {e}")
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao enviar email de verificação. Tente novamente mais tarde."
        )

    return {"message": "Se o email existir, um novo link de verificação foi enviado."}
