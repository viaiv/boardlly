import { useEffect, useState } from "react";

import { apiFetch } from "@/lib/api";
import { useSession } from "@/lib/session";

interface TeamMember {
  id: string;
  email: string;
  name?: string;
  role: string;
}

export function Team() {
  const { user } = useSession();
  const [members, setMembers] = useState<TeamMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchMembers = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await apiFetch<TeamMember[]>("/api/users");
        setMembers(data);
      } catch (err) {
        const message = err instanceof Error ? err.message : "Não foi possível carregar o time";
        setError(message);
      } finally {
        setLoading(false);
      }
    };

    if (user?.role === "admin" || user?.role === "owner") {
      void fetchMembers();
    }
  }, [user?.role]);

  if (user?.role !== "admin" && user?.role !== "owner") {
    return (
      <div className="rounded-lg border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
        Apenas administradores ou owners podem gerenciar o time.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight">Time</h1>
        <p className="text-sm text-muted-foreground">
          Visualize quem tem acesso à conta e os papéis atribuídos.
        </p>
      </header>
      <div className="rounded-lg border border-border bg-card">
        <table className="min-w-full divide-y divide-border">
          <thead className="bg-muted/50 text-sm uppercase text-muted-foreground">
            <tr>
              <th className="px-4 py-3 text-left font-medium">Nome</th>
              <th className="px-4 py-3 text-left font-medium">Email</th>
              <th className="px-4 py-3 text-left font-medium">Permissão</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border text-sm">
            {loading ? (
              <tr>
                <td className="px-4 py-6 text-center" colSpan={3}>
                  Carregando...
                </td>
              </tr>
            ) : error ? (
              <tr>
                <td className="px-4 py-6 text-center text-red-500" colSpan={3}>
                  {error}
                </td>
              </tr>
            ) : members.length === 0 ? (
              <tr>
                <td className="px-4 py-6 text-center" colSpan={3}>
                  Nenhum membro encontrado.
                </td>
              </tr>
            ) : (
              members.map((member) => (
                <tr key={member.id}>
                  <td className="px-4 py-3">{member.name ?? "—"}</td>
                  <td className="px-4 py-3">{member.email}</td>
                  <td className="px-4 py-3 uppercase text-muted-foreground">{member.role}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
