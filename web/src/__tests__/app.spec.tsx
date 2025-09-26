import { render, screen } from "@testing-library/react";
import { BrowserRouter, Outlet } from "react-router-dom";
import type { ReactNode } from "react";

import App from "../App";

vi.mock("@/lib/auth-guard", () => ({
  AuthGuard: () => <Outlet />,
}));

vi.mock("@/lib/session", () => ({
  SessionProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
  useSession: () => ({
    status: "authenticated" as const,
    user: { id: "1", email: "demo@tactyo.com", role: "viewer" as const },
    refresh: async () => undefined,
  }),
  useRequireRole: () => true,
}));

describe("App", () => {
  it("render overview heading", () => {
    render(
      <BrowserRouter>
        <App />
      </BrowserRouter>,
    );

    expect(screen.getByText(/Visão Geral/i)).toBeInTheDocument();
  });
});
