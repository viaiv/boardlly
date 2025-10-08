import { useMemo } from "react";
import type { ReactNode } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";

import { cn } from "@/lib/utils";
import { useSession } from "@/lib/session";
import { Avatar } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
  DropdownMenuItem,
} from "@/components/ui/dropdown-menu";
import { apiFetch } from "@/lib/api";

const baseNavigation = [
  { to: "/", label: "Overview" },
  { to: "/roadmap", label: "Roadmap" },
  { to: "/sprints", label: "Sprints" },
  { to: "/requests", label: "Solicitações" },
  { to: "/backlog", label: "Backlog" },
];

export function AppShell({ headerActions }: { headerActions?: ReactNode }) {
  const { user, refresh } = useSession();
  const location = useLocation();

  const handleLogout = async () => {
    await apiFetch("/api/auth/logout", { method: "POST", parseJson: false });
    await refresh();
  };

  const navigation = useMemo(() => {
    if (user?.role === "admin" || user?.role === "owner") {
      return [...baseNavigation, { to: "/team", label: "Time" }];
    }
    return baseNavigation;
  }, [user?.role]);

  const activeLabel = useMemo(() => {
    // Check settings first (not in main navigation)
    if (location.pathname.startsWith("/settings")) {
      return "Configurações";
    }

    const current = navigation.find((item) =>
      item.to === "/" ? location.pathname === "/" : location.pathname.startsWith(item.to),
    );
    return current?.label ?? "Dashboard";
  }, [location.pathname, navigation]);

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-background">
        <div className="flex flex-col gap-4 px-6 py-4 md:flex-row md:items-center md:justify-between">
          <div className="flex flex-col gap-1">
            <h1 className="text-xl font-semibold">Tactyo</h1>
            <p className="text-sm text-muted-foreground">
              Dashboard conectado ao GitHub Projects v2.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-4">
            <nav className="flex flex-wrap items-center gap-2 text-sm">
              {navigation.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) =>
                    cn(
                      "rounded-md px-3 py-2 font-medium transition hover:bg-accent hover:text-accent-foreground",
                      isActive ? "bg-accent text-accent-foreground" : "text-muted-foreground",
                    )
                  }
                  end={item.to === "/"}
                >
                  {item.label}
                </NavLink>
              ))}
            </nav>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button className="flex items-center gap-3 rounded-md border border-border px-3 py-2 text-left text-sm hover:bg-accent hover:text-accent-foreground">
                  <Avatar text={user?.name ?? user?.email ?? "Usuário"} />
                  <div className="hidden text-left md:block">
                    <p className="font-medium leading-none">{user?.name ?? user?.email ?? "Usuário"}</p>
                    <p className="text-xs uppercase text-muted-foreground">{user?.role ?? ""}</p>
                  </div>
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem asChild>
                  <NavLink to="/settings" className="cursor-pointer">
                    Configurações
                  </NavLink>
                </DropdownMenuItem>
                <DropdownMenuItem
                  onSelect={(event) => {
                    event.preventDefault();
                    void handleLogout();
                  }}
                >
                  Sair
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </header>

      <main className="flex w-full flex-col gap-6 px-6 py-10">
        <div className="flex flex-col gap-4 border-b pb-6 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
              Tactyo MVP
            </p>
            <h2 className="text-3xl font-semibold tracking-tight">{activeLabel}</h2>
          </div>
          {headerActions ? <div className="flex items-center gap-3">{headerActions}</div> : null}
        </div>
        <section className="pb-10">
          <Outlet />
        </section>
      </main>
    </div>
  );
}
