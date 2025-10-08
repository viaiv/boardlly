import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useSession } from "./session";
import { useProject } from "./project";

interface AuthGuardProps {
  redirectTo?: string;
}

export function AuthGuard({ redirectTo = "/login" }: AuthGuardProps) {
  const location = useLocation();
  const { status, user } = useSession();
  const { status: projectStatus, activeProject, projects } = useProject();

  if (status === "loading" || projectStatus === "loading") {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-sm text-muted-foreground">Carregando...</p>
      </div>
    );
  }

  if (status === "unauthenticated") {
    return <Navigate to={redirectTo} replace />;
  }

  if (
    status === "authenticated" &&
    user?.needsAccountSetup &&
    !location.pathname.startsWith("/onboarding/account")
  ) {
    return <Navigate to="/onboarding/account" replace />;
  }

  // Se o usuário está autenticado, passou pelo setup, mas não tem projeto ativo
  // Redireciona para seleção de projeto (exceto se já está nessa página ou em settings)
  if (
    status === "authenticated" &&
    !user?.needsAccountSetup &&
    projectStatus === "ready" &&
    !activeProject &&
    projects.length > 0 &&
    !location.pathname.startsWith("/project-selection") &&
    !location.pathname.startsWith("/settings")
  ) {
    return <Navigate to="/project-selection" replace />;
  }

  return <Outlet />;
}
