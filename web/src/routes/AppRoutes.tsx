import { Routes, Route, Navigate } from "react-router-dom";
import { AuthGuard } from "@/lib/auth-guard";
import { AppShell } from "@/components/layout/AppShell";
import { Overview } from "@/routes/Overview";
import { Roadmap } from "@/routes/Roadmap";
import { Requests } from "@/routes/Requests";
import { RequestNew } from "@/routes/RequestNew";
import { RequestDetail } from "@/routes/RequestDetail";
import { Backlog } from "@/routes/Backlog";
import { Sprints } from "@/routes/Sprints";
import { Settings } from "@/routes/Settings";
import { ProjectSettings } from "@/routes/ProjectSettings";
import { Team } from "@/routes/Team";
import { Login } from "@/routes/Login";
import { Register } from "@/routes/Register";
import { AccountSetup } from "@/routes/AccountSetup";

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<AuthGuard />}>
        <Route path="/onboarding/account" element={<AccountSetup />} />
        <Route element={<AppShell />}>
          <Route index element={<Overview />} />
          <Route path="roadmap" element={<Roadmap />} />
          <Route path="items" element={<Navigate to="/roadmap" replace />} />
          <Route path="requests" element={<Requests />} />
          <Route path="requests/new" element={<RequestNew />} />
          <Route path="requests/:requestId" element={<RequestDetail />} />
          <Route path="backlog" element={<Backlog />} />
          <Route path="sprints" element={<Sprints />} />
          <Route path="team" element={<Team />} />
          <Route path="settings" element={<Settings />} />
          <Route path="settings/projects/:projectId" element={<ProjectSettings />} />
        </Route>
      </Route>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
    </Routes>
  );
}
