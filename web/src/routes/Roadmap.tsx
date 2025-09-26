import { useEffect, useMemo, useState } from "react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api";

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
  title: string | null;
  status: string | null;
  iteration: string | null;
  estimate: number | null;
  updated_at: string | null;
  iteration_id: string | null;
  iteration_start: string | null;
  iteration_end: string | null;
  start_date: string | null;
  end_date: string | null;
  due_date: string | null;
  remote_updated_at: string | null;
  last_local_edit_at: string | null;
}

type TimelinePreparedItem = ProjectItem & {
  startDate: Date;
  endDate: Date;
};

const DAY_IN_MS = 24 * 60 * 60 * 1000;

export function Roadmap() {
  const [project, setProject] = useState<ProjectInfo | null>(null);
  const [items, setItems] = useState<ProjectItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<"board" | "timeline">("board");

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
        const message = err instanceof Error ? err.message : "Falha ao carregar roadmap";
        setError(message);
      } finally {
        setLoading(false);
      }
    };

    void load();
  }, []);

  const columns = useMemo(() => {
    const configured = project?.status_columns ?? [];
    const withoutDone = configured.filter((name) => name.toLowerCase() !== "done");
    const baseColumns = [...withoutDone, "Done"];
    const statusesFromItems = items
      .map((item) => item.status)
      .filter((status): status is string => Boolean(status));
    statusesFromItems.forEach((status) => {
      if (!baseColumns.includes(status) && status.toLowerCase() !== "done") {
        baseColumns.splice(baseColumns.length - 1, 0, status);
      }
    });
    if (!baseColumns.length) {
      return ["Sem status"];
    }
    return baseColumns;
  }, [project?.status_columns, items]);

  const groups = useMemo(() => {
    const grouped = new Map<string, ProjectItem[]>();
    const fallbackKey = "Sem status";

    columns.forEach((column) => grouped.set(column, []));
    grouped.set(fallbackKey, []);

    items.forEach((item) => {
      const key = item.status && columns.includes(item.status) ? item.status : fallbackKey;
      grouped.get(key)?.push(item);
    });

    return columns
      .map((column) => ({
        name: column,
        items: (grouped.get(column) ?? []).sort((a, b) => {
          const aDate = a.updated_at ? new Date(a.updated_at).getTime() : 0;
          const bDate = b.updated_at ? new Date(b.updated_at).getTime() : 0;
          return bDate - aDate;
        }),
      }))
      .concat(
        grouped.get("Sem status")?.length
          ? [
              {
                name: "Sem status",
                items: (grouped.get("Sem status") ?? []).sort((a, b) => {
                  const aDate = a.updated_at ? new Date(a.updated_at).getTime() : 0;
                  const bDate = b.updated_at ? new Date(b.updated_at).getTime() : 0;
                  return bDate - aDate;
                }),
              },
            ]
          : [],
      );
  }, [columns, items]);

  const timeline = useMemo(() => {
    const withDates: TimelinePreparedItem[] = items
      .map((item) => {
        const startIso = item.start_date ?? item.iteration_start ?? item.due_date;
        const endIso = item.end_date ?? item.due_date ?? item.iteration_end ?? startIso;

        if (!startIso || !endIso) {
          return null;
        }

        const startDate = new Date(startIso);
        let endDate = new Date(endIso);
        if (Number.isNaN(startDate.getTime()) || Number.isNaN(endDate.getTime())) {
          return null;
        }
        if (endDate.getTime() < startDate.getTime()) {
          endDate = startDate;
        }

        return {
          ...item,
          startDate,
          endDate,
        } satisfies TimelinePreparedItem;
      })
      .filter((value): value is TimelinePreparedItem => Boolean(value));

    if (!withDates.length) {
      return null;
    }

    const min = withDates.reduce((acc, current) => (current.startDate < acc ? current.startDate : acc), withDates[0].startDate);
    const max = withDates.reduce((acc, current) => (current.endDate > acc ? current.endDate : acc), withDates[0].endDate);
    const totalMs = Math.max(max.getTime() - min.getTime(), DAY_IN_MS);

    return {
      items: withDates,
      range: {
        min,
        max,
        totalMs,
      },
    };
  }, [items]);

  const timelineItemIds = useMemo(() => new Set(timeline?.items.map((item) => item.id) ?? []), [timeline]);

  const undatedItems = useMemo(
    () => items.filter((item) => !timelineItemIds.has(item.id)),
    [items, timelineItemIds],
  );

  if (loading) {
    return (
      <div className="rounded-lg border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
        Carregando roadmap...
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

  const formatDate = (value: Date) => value.toLocaleDateString();

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <header className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">Roadmap</h1>
          <p className="text-sm text-muted-foreground">
            {project.name ?? "Projeto sem título"} · {project.owner_login} · #{project.project_number}
          </p>
          <p className="text-xs text-muted-foreground">
            Visualize o progresso por etapas ou em formato de linha do tempo. Cartões sem status conhecido ficam em "Sem status".
          </p>
        </header>
        <div className="flex items-center gap-2">
          <Button
            variant={viewMode === "board" ? "default" : "outline"}
            onClick={() => setViewMode("board")}
          >
            Board
          </Button>
          <Button
            variant={viewMode === "timeline" ? "default" : "outline"}
            onClick={() => setViewMode("timeline")}
          >
            Timeline
          </Button>
        </div>
      </div>

      {viewMode === "board" ? (
        groups.length === 0 ? (
          <div className="rounded-lg border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
            Nenhum item sincronizado ainda.
          </div>
        ) : (
          <div className="overflow-x-auto pb-2">
            <div className="grid min-w-full gap-4 [grid-template-columns:repeat(auto-fit,minmax(280px,1fr))]">
              {groups.map((group) => (
                <Card key={group.name} className="h-full">
                  <CardHeader>
                    <CardTitle>{group.name}</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {group.items.length === 0 ? (
                      <p className="text-sm text-muted-foreground">Nenhum item nesta etapa.</p>
                    ) : (
                      group.items.map((item) => (
                        <div key={item.id} className="rounded-md border border-border p-3">
                          <p className="text-sm font-medium">{item.title ?? "Sem título"}</p>
                          <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                            <span className="uppercase">{item.status ?? "—"}</span>
                            {item.iteration ? <span>{item.iteration}</span> : null}
                            {item.estimate ? <span>Estimativa: {item.estimate}</span> : null}
                            {item.updated_at ? (
                              <span>Atualizado: {new Date(item.updated_at).toLocaleDateString()}</span>
                            ) : null}
                          </div>
                        </div>
                      ))
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        )
      ) : timeline ? (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Visão Timeline</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>{formatDate(timeline.range.min)}</span>
                <span>{formatDate(timeline.range.max)}</span>
              </div>
              <div className="space-y-6">
                {timeline.items.map((item) => {
                  const base = timeline.range.min.getTime();
                  const total = timeline.range.totalMs;
                  const startMs = item.startDate.getTime();
                  const endMs = item.endDate.getTime();
                  const computedLeft = ((startMs - base) / total) * 100;
                  const leftPercentage = Math.min(Math.max(computedLeft, 0), 99);
                  const durationMs = Math.max(endMs - startMs, DAY_IN_MS);
                  const computedWidth = (durationMs / total) * 100;
                  const widthPercentage = Math.max(Math.min(computedWidth, 100 - leftPercentage), 1);

                  return (
                    <div key={item.id} className="space-y-2">
                      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
                        <div className="flex flex-col">
                          <span className="text-sm font-medium text-foreground">{item.title ?? "Sem título"}</span>
                          {item.status ? <span className="uppercase">{item.status}</span> : null}
                        </div>
                        <span>
                          {formatDate(item.startDate)} → {formatDate(item.endDate)}
                        </span>
                      </div>
                      <div className="relative h-6 rounded bg-muted">
                        <div
                          className="absolute top-0 h-6 rounded bg-primary/70"
                          style={{ left: `${leftPercentage}%`, width: `${widthPercentage}%` }}
                          aria-hidden
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          {undatedItems.length ? (
            <Card>
              <CardHeader>
                <CardTitle>Itens sem datas</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {undatedItems.map((item) => (
                  <div key={item.id} className="rounded-md border border-border p-3">
                    <p className="text-sm font-medium">{item.title ?? "Sem título"}</p>
                    <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                      <span className="uppercase">{item.status ?? "—"}</span>
                      {item.iteration ? <span>{item.iteration}</span> : null}
                      {item.updated_at ? (
                        <span>Atualizado: {new Date(item.updated_at).toLocaleDateString()}</span>
                      ) : null}
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          ) : null}
        </div>
      ) : (
        <div className="rounded-lg border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
          Nenhum item possui datas configuradas ainda.
        </div>
      )}
    </div>
  );
}
