import { useMemo, useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiFetch } from "@/lib/api";
import { mapToSessionUser, useSession } from "@/lib/session";
import type { SessionUser } from "@/lib/session";

const ROLE_OPTIONS: SessionUser["role"][] = ["viewer", "editor", "pm", "admin"];

export function Register() {
  const navigate = useNavigate();
  const { status, user, refresh } = useSession();
  const [searchParams] = useSearchParams();

  // Capturar invite_token da URL
  const inviteToken = searchParams.get("invite_token");

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [name, setName] = useState("");
  const [role, setRole] = useState<SessionUser["role"]>("viewer");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const isAuthenticated = status === "authenticated";
  const canAssignRole = isAuthenticated && ["admin", "owner"].includes(user?.role ?? "");
  const isFirstUserFlow = !isAuthenticated;
  const hasInvite = !!inviteToken;
  const passwordMismatch = password !== confirmPassword && confirmPassword.length > 0;

  const formTitle = useMemo(() => {
    if (hasInvite) {
      return "Aceitar Convite";
    }
    if (isFirstUserFlow) {
      return "Criar primeira conta";
    }
    return "Adicionar novo usuário";
  }, [isFirstUserFlow, hasInvite]);

  const formDescription = useMemo(() => {
    if (hasInvite) {
      return "Complete seu cadastro para aceitar o convite e acessar o projeto.";
    }
    if (isFirstUserFlow) {
      return "Informe seus dados para acessar o Tactyo. Na próxima etapa você criará a conta.";
    }
    return "Somente administradores ou owners podem adicionar novos membros.";
  }, [isFirstUserFlow, hasInvite]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (passwordMismatch) {
      setError("As senhas não conferem.");
      return;
    }
    setIsSubmitting(true);
    setError(null);
    setSuccess(null);
    try {
      const payload: Record<string, unknown> = {
        email,
        password,
        name: name || undefined,
      };
      if (canAssignRole) {
        payload.role = role;
      }
      // Adicionar invite_token se presente na URL
      if (inviteToken) {
        payload.invite_token = inviteToken;
      }

      const response = await apiFetch<{ [key: string]: unknown }>("/api/auth/register", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      const sessionUser = mapToSessionUser(response);

      if (isFirstUserFlow || sessionUser.needsAccountSetup) {
        await refresh();
        navigate("/onboarding/account");
        return;
      }

      setSuccess(`Usuário ${sessionUser.email} criado com sucesso.`);
      setEmail("");
      setPassword("");
      setConfirmPassword("");
      setName("");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Falha ao registrar usuário";
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background px-6 py-12">
      <div className="w-full max-w-lg space-y-6">
        <div className="space-y-1 text-center">
          <h1 className="text-2xl font-semibold tracking-tight">{formTitle}</h1>
          <p className="text-sm text-muted-foreground">
            {formDescription}
          </p>
        </div>
        <form className="space-y-4" onSubmit={handleSubmit}>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="name">Nome</Label>
              <Input
                id="name"
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="Nome completo"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
              />
            </div>
          </div>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="password">Senha</Label>
              <Input
                id="password"
                type="password"
                autoComplete="new-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
                minLength={8}
              />
              <p className="text-xs text-muted-foreground">Mínimo de 8 caracteres.</p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="confirmPassword">Confirmar senha</Label>
              <Input
                id="confirmPassword"
                type="password"
                autoComplete="new-password"
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                required
              />
              {passwordMismatch ? <p className="text-xs text-red-500">Senhas não conferem.</p> : null}
            </div>
          </div>
          {canAssignRole ? (
            <div className="space-y-2">
              <Label htmlFor="role">Permissão</Label>
              <select
                id="role"
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={role}
                onChange={(event) => setRole(event.target.value as SessionUser["role"])}
              >
                {ROLE_OPTIONS.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
              <p className="text-xs text-muted-foreground">
                Escolha o nível de acesso (viewer, editor, pm ou admin). Owners podem ser promovidos posteriormente via banco.
              </p>
            </div>
          ) : null}
          {error ? <p className="text-sm text-red-500">{error}</p> : null}
          {success ? <p className="text-sm text-emerald-600">{success}</p> : null}
          <Button type="submit" className="w-full" disabled={isSubmitting || passwordMismatch}>
            {isSubmitting ? "Salvando..." : isFirstUserFlow ? "Criar conta" : "Adicionar usuário"}
          </Button>
        </form>
        <p className="text-center text-sm text-muted-foreground">
          {isFirstUserFlow ? (
            <span>
              Já possui conta? <Link className="text-primary underline" to="/login">Entrar</Link>.
            </span>
          ) : (
            <span>
              Retornar ao painel? <Link className="text-primary underline" to="/">Ir para dashboard</Link>.
            </span>
          )}
        </p>
      </div>
    </div>
  );
}
