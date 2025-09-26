import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useSession } from "./session";

interface AuthGuardProps {
  redirectTo?: string;
}

export function AuthGuard({ redirectTo = "/login" }: AuthGuardProps) {
  const location = useLocation();
  const { status, user } = useSession();

  if (status === "loading") {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-sm text-muted-foreground">Carregando sessão...</p>
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

  return <Outlet />;
}
