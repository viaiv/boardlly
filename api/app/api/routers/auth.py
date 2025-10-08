from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.security import clear_session, ensure_password_strength, establish_session
from app.models.account import Account
from app.models.user import AppUser
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

    if total_users == 0:
        role = "owner"
    else:
        if current_user is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Autenticação necessária")
        if current_user.role not in {"admin", "owner"}:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Permissão insuficiente")
        account = await db.get(Account, current_user.account_id)
        if not account:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Conta não encontrada")
        role = payload.role

    user = await create_user(
        db,
        account=account,
        email=payload.email,
        password=payload.password,
        role=role,
        name=payload.name,
    )

    # Primeiro usuário (owner) é verificado automaticamente
    if total_users == 0:
        user.email_verified = True
        user.email_verification_token = None
        user.email_verification_token_expires = None
        establish_session(request, str(user.id))
    else:
        # Enviar email de verificação para novos usuários
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
