import { useEffect, useMemo, useState } from "react";

import { apiFetch } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface ProjectInfo {
  id: number;
  name: string | null;
  owner_login: string;
  project_number: number;
  last_synced_at?: string | null;
  status_columns?: string[] | null;
}

interface ProjectItem {
  id: number;
  item_node_id: string;
  content_type?: string | null;
  title?: string | null;
  status?: string | null;
  iteration?: string | null;
  estimate?: number | null;
  url?: string | null;
  assignees?: string[];
  updated_at?: string | null;
  last_synced_at?: string | null;
}

export function Items() {
  const [project, setProject] = useState<ProjectInfo | null>(null);
  const [items, setItems] = useState<ProjectItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const projectData = await apiFetch<ProjectInfo>("/api/projects/current");
        setProject(projectData);
        const itemsData = await apiFetch<ProjectItem[]>("/api/projects/current/items");
        setItems(itemsData);
      } catch (err) {
        const message = err instanceof Error ? err.message : "Falha ao carregar itens";
        setError(message);
      } finally {
        setLoading(false);
      }
    };

    void load();
  }, []);

  const lastSynced = useMemo(() => {
    if (!project?.last_synced_at) {
      return null;
    }
    return new Date(project.last_synced_at).toLocaleString();
  }, [project?.last_synced_at]);

  if (loading) {
    return (
      <div className="rounded-lg border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
        Carregando itens do Project...
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-dashed border-border p-8 text-center text-sm text-red-500">
        {error}
      </div>
    );
  }

  if (!project) {
    return (
      <div className="rounded-lg border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
        Nenhum Project conectado. Configure as integrações em Configurações.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">Itens do Project</h1>
        <p className="text-sm text-muted-foreground">
          {project.name ?? "Projeto sem título"} · {project.owner_login} · #{project.project_number}
        </p>
        {lastSynced ? (
          <p className="text-xs text-muted-foreground">Última sincronização: {lastSynced}</p>
        ) : (
          <p className="text-xs text-muted-foreground">Ainda não sincronizado. Utilize Configurações para sincronizar.</p>
        )}
      </header>

      {items.length === 0 ? (
        <div className="rounded-lg border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
          Nenhum item encontrado neste Project.
        </div>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>Itens sincronizados</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-border text-sm">
                <thead className="bg-muted/50 text-muted-foreground">
                  <tr>
                    <th className="px-4 py-2 text-left font-medium">Título</th>
                    <th className="px-4 py-2 text-left font-medium">Status</th>
                    <th className="px-4 py-2 text-left font-medium">Responsáveis</th>
                    <th className="px-4 py-2 text-left font-medium">Estimate</th>
                    <th className="px-4 py-2 text-left font-medium">Atualizado</th>
                    <th className="px-4 py-2 text-left font-medium">Link</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {items.map((item) => (
                    <tr key={item.id}>
                      <td className="px-4 py-3">
                        <div className="max-w-xs truncate font-medium" title={item.title ?? "Sem título"}>
                          {item.title ?? "Sem título"}
                        </div>
                        <p className="text-xs text-muted-foreground uppercase">{item.content_type ?? ""}</p>
                      </td>
                      <td className="px-4 py-3">
                        {item.status ? (
                          <span className="rounded-full bg-muted px-2 py-1 text-xs uppercase text-muted-foreground">
                            {item.status}
                          </span>
                        ) : (
                          "—"
                        )}
                      </td>
                      <td className="px-4 py-3">
                        {item.assignees && item.assignees.length > 0 ? item.assignees.join(", ") : "—"}
                      </td>
                      <td className="px-4 py-3">{item.estimate ?? "—"}</td>
                      <td className="px-4 py-3">
                        {item.updated_at ? new Date(item.updated_at).toLocaleDateString() : "—"}
                      </td>
                      <td className="px-4 py-3">
                        {item.url ? (
                          <a
                            href={item.url}
                            target="_blank"
                            rel="noreferrer"
                            className="text-primary underline"
                          >
                            GitHub
                          </a>
                        ) : (
                          "—"
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
