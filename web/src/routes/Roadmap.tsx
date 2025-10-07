import { type DragEvent, useCallback, useEffect, useMemo, useState } from "react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api";
import { useSession } from "@/lib/session";
import { cn } from "@/lib/utils";
import {
  buildBoardColumns,
  buildColumnKey,
  normalizeStatusValue,
} from "./roadmapBoardUtils";
import { ProjectItemEditor, type ProjectItemEditorValues } from "@/components/project-item-editor";
import {
  classifyProjectItem,
  classificationBadgeClass,
  convertDateInputToIso,
  formatDateForInput,
  type ProjectItem,
  type ProjectItemComment,
  type ProjectItemDetails,
} from "@/lib/project-items";

interface ProjectInfo {
  id: number;
  name: string | null;
  owner_login: string;
  project_number: number;
  last_synced_at?: string | null;
  status_columns?: string[] | null;
}

type TimelinePreparedItem = ProjectItem & {
  startDate: Date;
  endDate: Date;
};

const DAY_IN_MS = 24 * 60 * 60 * 1000;
const DRAG_DATA_MIME = "application/json";

export function Roadmap() {
  const { user, status: sessionStatus } = useSession();
  const [project, setProject] = useState<ProjectInfo | null>(null);
  const [items, setItems] = useState<ProjectItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [interactionError, setInteractionError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<"board" | "timeline">("board");
  const [draggingId, setDraggingId] = useState<number | null>(null);
  const [activeColumn, setActiveColumn] = useState<string | null>(null);
  const [savingItemId, setSavingItemId] = useState<number | null>(null);
  const [editorItem, setEditorItem] = useState<ProjectItem | null>(null);
  const [editorSubmitting, setEditorSubmitting] = useState(false);
  const [editorDetails, setEditorDetails] = useState<ProjectItemDetails | null>(null);
  const [editorDetailsLoading, setEditorDetailsLoading] = useState(false);
  const [editorDetailsError, setEditorDetailsError] = useState<string | null>(null);
  const [editorComments, setEditorComments] = useState<ProjectItemComment[]>([]);
  const [editorCommentsLoading, setEditorCommentsLoading] = useState(false);
  const [editorCommentsError, setEditorCommentsError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setLoadError(null);
      setInteractionError(null);
      try {
        const projectData = await apiFetch<ProjectInfo>("/api/projects/current");
        setProject(projectData);
        const itemsData = await apiFetch<ProjectItem[]>("/api/projects/current/items");
        setItems(itemsData);
      } catch (err) {
        const message = err instanceof Error ? err.message : "Falha ao carregar roadmap";
        setLoadError(message);
      } finally {
        setLoading(false);
      }
    };

    void load();
  }, []);

  const getErrorMessage = (err: unknown, fallback: string): string =>
    err instanceof Error ? err.message : fallback;

  const loadEditorData = useCallback(
    async (itemId: number, signal?: AbortSignal) => {
      setEditorDetails(null);
      setEditorDetailsLoading(true);
      setEditorDetailsError(null);
      setEditorComments([]);
      setEditorCommentsLoading(true);
      setEditorCommentsError(null);

      const detailsPromise = apiFetch<ProjectItemDetails>(
        `/api/projects/current/items/${itemId}/details`,
        { signal },
      );
      const commentsPromise = apiFetch<ProjectItemComment[]>(
        `/api/projects/current/items/${itemId}/comments`,
        { signal },
      );

      const [detailsResult, commentsResult] = await Promise.allSettled([detailsPromise, commentsPromise]);

      if (signal?.aborted) {
        return;
      }

      if (detailsResult.status === "fulfilled") {
        setEditorDetails(detailsResult.value);
        setEditorDetailsError(null);
      } else {
        setEditorDetails(null);
        setEditorDetailsError(getErrorMessage(detailsResult.reason, "Falha ao carregar detalhes"));
      }
      setEditorDetailsLoading(false);

      if (commentsResult.status === "fulfilled") {
        setEditorComments(commentsResult.value);
        setEditorCommentsError(null);
      } else {
        setEditorComments([]);
        setEditorCommentsError(getErrorMessage(commentsResult.reason, "Falha ao carregar comentários"));
      }
      setEditorCommentsLoading(false);

      setInteractionError(null);
    },
    [],
  );

  useEffect(() => {
    if (!editorItem) {
      setEditorDetails(null);
      setEditorDetailsError(null);
      setEditorDetailsLoading(false);
      setEditorComments([]);
      setEditorCommentsError(null);
      setEditorCommentsLoading(false);
      return;
    }

    const controller = new AbortController();
    void loadEditorData(editorItem.id, controller.signal);
    return () => controller.abort();
  }, [editorItem?.id, loadEditorData]);

  const columns = useMemo(
    () => buildBoardColumns(project?.status_columns, items),
    [project?.status_columns, items],
  );

  const columnItems = useMemo(() => {
    const buckets = new Map<string, ProjectItem[]>(columns.map((column) => [column.key, []]));
    for (const item of items) {
      const key = buildColumnKey(normalizeStatusValue(item.status));
      const bucket = buckets.get(key) ?? buckets.get(columns[0]?.key ?? "");
      if (bucket) {
        bucket.push(item);
      }
    }

    return columns.map((column) => ({
      column,
      items: (buckets.get(column.key) ?? []).slice().sort((a, b) => {
        const aTime = a.updated_at ? new Date(a.updated_at).getTime() : 0;
        const bTime = b.updated_at ? new Date(b.updated_at).getTime() : 0;
        return bTime - aTime;
      }),
    }));
  }, [columns, items]);

  const canEdit = useMemo(() => {
    if (!user?.role) {
      return false;
    }
    const normalized = user.role.toLowerCase().trim();
    return normalized === "owner" || normalized === "admin";
  }, [user?.role]);

  const handleDrop = async (
    event: DragEvent<HTMLDivElement>,
    column: (typeof columns)[number],
  ): Promise<void> => {
    if (!canEdit) {
      return;
    }
    event.preventDefault();
    setActiveColumn(null);

    const rawPayload =
      event.dataTransfer.getData(DRAG_DATA_MIME) || event.dataTransfer.getData("text/plain");

    if (!rawPayload) {
      setDraggingId(null);
      return;
    }

    let payload: { itemId: number } | null = null;
    try {
      payload = JSON.parse(rawPayload);
    } catch {
      const parsed = Number(rawPayload);
      if (!Number.isNaN(parsed)) {
        payload = { itemId: parsed };
      }
    }

    if (!payload) {
      setDraggingId(null);
      return;
    }

    const item = items.find((candidate) => candidate.id === payload?.itemId);
    if (!item) {
      setDraggingId(null);
      return;
    }

    const currentStatus = normalizeStatusValue(item.status);
    const nextStatus = normalizeStatusValue(column.status);

    if (currentStatus === nextStatus) {
      setDraggingId(null);
      return;
    }

    const itemId = item.id;
    const previousStatus = currentStatus;
    const previousRemoteUpdatedAt = item.remote_updated_at ?? undefined;

    setItems((prev) =>
      prev.map((candidate) => (candidate.id === itemId ? { ...candidate, status: nextStatus } : candidate)),
    );
    setSavingItemId(itemId);

    const body: Record<string, unknown> = {
      status: nextStatus,
    };
    if (previousRemoteUpdatedAt) {
      body.remote_updated_at = previousRemoteUpdatedAt;
    }

    try {
      const updated = await apiFetch<ProjectItem>(`/api/projects/current/items/${itemId}`, {
        method: "PATCH",
        body: JSON.stringify(body),
      });
      setItems((prev) =>
        prev.map((candidate) => (candidate.id === itemId ? { ...candidate, ...updated } : candidate)),
      );
      setInteractionError(null);
    } catch (err) {
      setItems((prev) =>
        prev.map((candidate) => (candidate.id === itemId ? { ...candidate, status: previousStatus } : candidate)),
      );
      const message = err instanceof Error ? err.message : "Falha ao mover item";
      setInteractionError(message);
    } finally {
      setSavingItemId((current) => (current === itemId ? null : current));
      setDraggingId(null);
    }
  };

  const handleCardClick = (item: ProjectItem) => {
    if (editorSubmitting || savingItemId === item.id || draggingId === item.id) {
      return;
    }
    setEditorItem(item);
  };

  const handleEditorSubmit = async (values: ProjectItemEditorValues) => {
    const item = editorItem;
    if (!item) {
      return;
    }

    const payload: Record<string, unknown> = {};
    const currentStart = formatDateForInput(item.start_date);
    const currentEnd = formatDateForInput(item.end_date);
    const currentDue = formatDateForInput(item.due_date);

    if (values.startDate !== currentStart) {
      payload.start_date = convertDateInputToIso(values.startDate);
    }
    if (values.endDate !== currentEnd) {
      payload.end_date = convertDateInputToIso(values.endDate);
    }
    if (values.dueDate !== currentDue) {
      payload.due_date = convertDateInputToIso(values.dueDate);
    }

    if (!Object.keys(payload).length) {
      throw new Error("Nenhuma alteração para salvar.");
    }

    if (item.remote_updated_at) {
      payload.remote_updated_at = item.remote_updated_at;
    }

    setEditorSubmitting(true);
    setSavingItemId(item.id);
    try {
      const updated = await apiFetch<ProjectItem>(`/api/projects/current/items/${item.id}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
      setItems((prev) =>
        prev.map((candidate) => (candidate.id === item.id ? { ...candidate, ...updated } : candidate)),
      );
      setEditorItem((current) => (current && current.id === item.id ? { ...current, ...updated } : current));
      setInteractionError(null);
    } finally {
      setEditorSubmitting(false);
      setSavingItemId((current) => (current === item.id ? null : current));
    }
  };

  const handleRefreshDetails = useCallback(async () => {
    if (!editorItem) {
      return;
    }
    await loadEditorData(editorItem.id);
  }, [editorItem?.id, loadEditorData]);

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

  if (loadError) {
    return (
      <div className="rounded-lg border border-dashed border-border p-8 text-center text-sm text-red-500">
        {loadError}
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
        items.length === 0 ? (
          <div className="rounded-lg border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
            Nenhum item sincronizado ainda.
          </div>
        ) : (
          <div className="space-y-4">
            {interactionError ? (
              <div className="rounded-md border border-red-200 bg-red-50 p-3 text-xs text-red-600">
                {interactionError}
              </div>
            ) : null}

            {sessionStatus === "authenticated" && !canEdit ? (
              <div className="rounded-md border border-dashed border-border bg-muted/20 p-3 text-xs text-muted-foreground">
                Apenas owners ou admins podem reorganizar itens. Você pode visualizar o board, mas drag and drop está desativado.
              </div>
            ) : null}

            <div className="overflow-x-auto pb-2">
              <div className="grid min-w-full gap-4 [grid-template-columns:repeat(auto-fit,minmax(280px,1fr))]">
                {columnItems.map(({ column, items: columnItemsList }) => (
                  <Card
                    key={column.key}
                    className={cn(
                      "flex h-full min-h-[280px] flex-col border transition",
                      activeColumn === column.key && draggingId !== null
                        ? "border-primary shadow-sm"
                        : "border-border",
                      sessionStatus === "authenticated" && !canEdit ? "opacity-90" : null,
                    )}
                    onDragEnter={(event) => {
                      if (!canEdit) return;
                      event.preventDefault();
                      setActiveColumn(column.key);
                    }}
                    onDragOver={(event) => {
                      if (!canEdit) return;
                      event.preventDefault();
                      event.dataTransfer.dropEffect = "move";
                      if (activeColumn !== column.key) {
                        setActiveColumn(column.key);
                      }
                    }}
                    onDragLeave={(event) => {
                      if (!canEdit) return;
                      if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
                        setActiveColumn((current) => (current === column.key ? null : current));
                      }
                    }}
                    onDrop={(event) => (canEdit ? void handleDrop(event, column) : undefined)}
                  >
                    <CardHeader className="flex flex-row items-center justify-between gap-2 pb-2">
                      <CardTitle className="text-base font-semibold">
                        {column.status === null ? "Sem status" : column.title}
                      </CardTitle>
                      <span className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
                        {columnItemsList.length}
                      </span>
                    </CardHeader>
                    <CardContent className="flex flex-1 flex-col gap-3">
                      {columnItemsList.map((item) => {
                        const isDragging = draggingId === item.id;
                        const isSaving = savingItemId === item.id;
                        const classification = classifyProjectItem(item);
                        const epicName = item.epic_name ?? classification.epicName;
                        const epicBadge = epicName &&
                          (!item.title || epicName.trim().toLowerCase() !== item.title.trim().toLowerCase());
                        return (
                          <article
                            key={item.id}
                            draggable={canEdit && !isSaving ? true : undefined}
                            onClick={() => handleCardClick(item)}
                            onKeyDown={(event) => {
                              if (event.key === "Enter" || event.key === " ") {
                                event.preventDefault();
                                handleCardClick(item);
                              }
                            }}
                            role="button"
                            tabIndex={0}
                            onDragStart={(event) => {
                              if (!canEdit) return;
                              event.dataTransfer.effectAllowed = "move";
                              event.dataTransfer.setData("text/plain", "move");
                              const payload = JSON.stringify({ itemId: item.id });
                              event.dataTransfer.setData(DRAG_DATA_MIME, payload);
                              setDraggingId(item.id);
                            }}
                            onDragEnd={() => {
                              setDraggingId(null);
                              setActiveColumn(null);
                            }}
                          className={cn(
                            "rounded-md border border-border bg-background p-3 text-sm shadow-sm transition",
                            isDragging ? "opacity-60 ring-2 ring-primary" : "hover:border-primary/60 hover:shadow",
                            isSaving
                              ? "cursor-wait opacity-80"
                              : canEdit
                                ? "cursor-grab"
                                : "cursor-pointer",
                      )}
                    >
                          <p className="text-sm font-medium leading-snug">
                            {item.title?.trim() && item.title.trim().length > 0 ? item.title : "Sem título"}
                          </p>
                          <div className="mt-2 flex flex-wrap items-center gap-2">
                            <span
                              className={cn(
                                "inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold uppercase",
                                classificationBadgeClass(classification.accent),
                              )}
                            >
                              {classification.typeLabel}
                            </span>
                            {epicBadge ? (
                              <span className="inline-flex items-center rounded-full bg-muted px-2 py-0.5 text-[11px] font-medium text-muted-foreground">
                                Épico: {epicName}
                              </span>
                            ) : null}
                            {!epicName && classification.accent !== "epic" ? (
                              <span className="inline-flex items-center rounded-full border border-amber-500 bg-amber-100 px-2 py-0.5 text-[11px] font-medium text-amber-700">
                                Sem épico
                              </span>
                            ) : null}
                          </div>
                            <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                              <span className="uppercase">{item.status ?? "—"}</span>
                              {item.iteration ? <span>{item.iteration}</span> : null}
                              {item.estimate ? <span>Estimativa: {item.estimate}</span> : null}
                              {item.updated_at ? (
                                <span>Atualizado: {new Date(item.updated_at).toLocaleDateString()}</span>
                              ) : null}
                            </div>
                          </article>
                        );
                      })}

                      {columnItemsList.length === 0 ? (
                        <div className="flex flex-1 items-center justify-center rounded-md border border-dashed border-border p-4 text-xs text-muted-foreground">
                          Arraste itens para esta etapa
                        </div>
                      ) : null}
                    </CardContent>
                  </Card>
                ))}
              </div>
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
                  const classification = classifyProjectItem(item);
                  const epicName = item.epic_name ?? classification.epicName;
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
                    <div
                      key={item.id}
                      className="space-y-2 rounded-md border border-transparent p-2 transition cursor-pointer hover:border-primary/50"
                      role="button"
                      tabIndex={0}
                      onClick={() => handleCardClick(item)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter" || event.key === " ") {
                          event.preventDefault();
                          handleCardClick(item);
                        }
                      }}
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
                        <div className="flex flex-col">
                          <span className="text-sm font-medium text-foreground">{item.title ?? "Sem título"}</span>
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="uppercase">{item.status ?? "—"}</span>
                            {epicName ? (
                              <span className="rounded-full bg-muted px-2 py-0.5 text-[11px] font-medium text-muted-foreground">
                                Épico: {epicName}
                              </span>
                            ) : classification.accent !== "epic" ? (
                              <span className="rounded-full border border-amber-500 bg-amber-100 px-2 py-0.5 text-[11px] font-medium text-amber-700">
                                Sem épico
                              </span>
                            ) : null}
                          </div>
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
                {undatedItems.map((item) => {
                  const classification = classifyProjectItem(item);
                  const epicName = item.epic_name ?? classification.epicName;
                  const showMissingEpic = !epicName && classification.accent !== "epic";

                  return (
                    <div
                      key={item.id}
                      className="rounded-md border border-border p-3 transition cursor-pointer hover:border-primary/60"
                      onClick={() => handleCardClick(item)}
                      onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        handleCardClick(item);
                      }
                    }}
                    role="button"
                    tabIndex={0}
                    >
                      <p className="text-sm font-medium">{item.title ?? "Sem título"}</p>
                      <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                        <span className="uppercase">{item.status ?? "—"}</span>
                        {epicName ? (
                          <span className="rounded-full bg-muted px-2 py-0.5 text-[11px] font-medium text-muted-foreground">
                            Épico: {epicName}
                          </span>
                        ) : null}
                        {showMissingEpic ? (
                          <span className="rounded-full border border-amber-500 bg-amber-100 px-2 py-0.5 text-[11px] font-medium text-amber-700">
                            Sem épico
                          </span>
                        ) : null}
                        {item.iteration ? <span>{item.iteration}</span> : null}
                        {item.updated_at ? (
                          <span>Atualizado: {new Date(item.updated_at).toLocaleDateString()}</span>
                        ) : null}
                      </div>
                    </div>
                  );
                })}
              </CardContent>
            </Card>
          ) : null}
        </div>
      ) : (
        <div className="rounded-lg border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
          Nenhum item possui datas configuradas ainda.
        </div>
      )}

      <ProjectItemEditor
        item={editorItem}
        open={Boolean(editorItem)}
        canEdit={canEdit}
        onClose={() => {
          if (!editorSubmitting) {
            setEditorItem(null);
          }
        }}
        onSubmit={handleEditorSubmit}
        submitting={editorSubmitting}
        details={editorDetails}
        detailsLoading={editorDetailsLoading}
        detailsError={editorDetailsError}
        comments={editorComments}
        commentsLoading={editorCommentsLoading}
        commentsError={editorCommentsError}
        onRefresh={handleRefreshDetails}
      />
    </div>
  );
}
