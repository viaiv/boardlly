import { type DragEvent, useCallback, useEffect, useMemo, useState } from "react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
import { HierarchyView } from "@/components/hierarchy-view";
import { getProjectHierarchy, type HierarchyResponse } from "@/lib/hierarchy";

interface ProjectInfo {
  id: number;
  name: string | null;
  owner_login: string;
  project_number: number;
  last_synced_at?: string | null;
  status_columns?: string[] | null;
}

interface StatusBreakdownEntry {
  status: string | null;
  count: number;
  total_estimate: number | null;
}

interface IterationSummary {
  iteration_id: string | null;
  name: string | null;
  start_date: string | null;
  end_date: string | null;
  item_count: number;
  completed_count: number;
  total_estimate: number | null;
  completed_estimate: number | null;
  status_breakdown: StatusBreakdownEntry[];
}

interface IterationOption {
  id: string;
  name: string;
  start_date: string | null;
  end_date: string | null;
}

interface IterationDashboard {
  summaries: IterationSummary[];
  options: IterationOption[];
}

interface EpicSummary {
  epic_option_id: string | null;
  name: string | null;
  item_count: number;
  completed_count: number;
  total_estimate: number | null;
  completed_estimate: number | null;
  status_breakdown: StatusBreakdownEntry[];
}

interface EpicOption {
  id: string;
  name: string;
  color: string | null;
}

interface EpicDashboard {
  summaries: EpicSummary[];
  options: EpicOption[];
}

interface FilterOption {
  value: string;
  label: string;
  hint?: string | null;
}

type TimelinePreparedItem = ProjectItem & {
  startDate: Date;
  endDate: Date;
};

const DAY_IN_MS = 24 * 60 * 60 * 1000;
const DRAG_DATA_MIME = "application/json";

const ALL_ITERATION_VALUE = "all";
const WITHOUT_ITERATION_VALUE = "__without_iteration__";
const ALL_EPIC_VALUE = "all";
const WITHOUT_EPIC_VALUE = "__without_epic__";
const ESTIMATE_FORMATTER = new Intl.NumberFormat("pt-BR", {
  maximumFractionDigits: 1,
  minimumFractionDigits: 0,
});

function formatDashboardDate(value?: string | null): string | null {
  if (!value) {
    return null;
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return null;
  }
  return parsed.toLocaleDateString();
}

function formatDashboardRange(start?: string | null, end?: string | null): string | null {
  const startLabel = formatDashboardDate(start);
  const endLabel = formatDashboardDate(end);
  if (startLabel && endLabel) {
    return `${startLabel} – ${endLabel}`;
  }
  if (startLabel) {
    return `Início: ${startLabel}`;
  }
  if (endLabel) {
    return `Entrega: ${endLabel}`;
  }
  return null;
}

function calculateCompletionPercentage(completed: number, total: number): number {
  if (!total) {
    return 0;
  }
  return Math.round((completed / total) * 100);
}

function isIterationSelected(summary: IterationSummary, selectedValue: string): boolean {
  if (selectedValue === ALL_ITERATION_VALUE) {
    return false;
  }
  if (selectedValue === WITHOUT_ITERATION_VALUE) {
    return summary.iteration_id === null;
  }
  return summary.iteration_id === selectedValue;
}

function isEpicSelected(summary: EpicSummary, selectedValue: string): boolean {
  if (selectedValue === ALL_EPIC_VALUE) {
    return false;
  }
  if (selectedValue === WITHOUT_EPIC_VALUE) {
    return summary.epic_option_id === null;
  }
  return summary.epic_option_id === selectedValue;
}

function formatEstimateValue(value: number): string {
  return ESTIMATE_FORMATTER.format(Math.round(value * 10) / 10);
}

export function Roadmap() {
  const { user, status: sessionStatus } = useSession();
  const [project, setProject] = useState<ProjectInfo | null>(null);
  const [items, setItems] = useState<ProjectItem[]>([]);
  const [iterationDashboard, setIterationDashboard] = useState<IterationDashboard | null>(null);
  const [epicDashboard, setEpicDashboard] = useState<EpicDashboard | null>(null);
  const [dashboardsLoading, setDashboardsLoading] = useState(false);
  const [dashboardsError, setDashboardsError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [interactionError, setInteractionError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<"board" | "timeline">("board");
  const [selectedIteration, setSelectedIteration] = useState<string>(ALL_ITERATION_VALUE);
  const [selectedEpic, setSelectedEpic] = useState<string>(ALL_EPIC_VALUE);
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
  const [hierarchy, setHierarchy] = useState<HierarchyResponse | null>(null);
  const [hierarchyLoading, setHierarchyLoading] = useState(false);
  const [hierarchyViewMode, setHierarchyViewMode] = useState<"list" | "flow">("list");

  const fetchDashboards = useCallback(async () => {
    setDashboardsLoading(true);
    try {
      const [iterationData, epicData] = await Promise.all([
        apiFetch<IterationDashboard>("/api/projects/current/iterations/dashboard"),
        apiFetch<EpicDashboard>("/api/projects/current/epics/dashboard"),
      ]);
      setIterationDashboard(iterationData);
      setEpicDashboard(epicData);
      setDashboardsError(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Falha ao carregar dados agregados";
      setDashboardsError(message);
    } finally {
      setDashboardsLoading(false);
    }
  }, []);

  const fetchHierarchy = useCallback(async () => {
    setHierarchyLoading(true);
    try {
      const data = await getProjectHierarchy();
      setHierarchy(data);
    } catch (err) {
      console.error("Erro ao carregar hierarquia:", err);
      setHierarchy(null);
    } finally {
      setHierarchyLoading(false);
    }
  }, []);

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
        void fetchDashboards();
      } catch (err) {
        const message = err instanceof Error ? err.message : "Falha ao carregar roadmap";
        setLoadError(message);
      } finally {
        setLoading(false);
      }
    };

    void load();
  }, [fetchDashboards]);

  useEffect(() => {
    void fetchHierarchy();
  }, [fetchHierarchy]);

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
  }, [editorItem, loadEditorData]);

  const filteredItems = useMemo(
    () =>
      items.filter((item) => {
        const matchesIteration =
          selectedIteration === ALL_ITERATION_VALUE ||
          (selectedIteration === WITHOUT_ITERATION_VALUE && !item.iteration_id) ||
          item.iteration_id === selectedIteration;
        const matchesEpic =
          selectedEpic === ALL_EPIC_VALUE ||
          (selectedEpic === WITHOUT_EPIC_VALUE && !item.epic_option_id) ||
          item.epic_option_id === selectedEpic;
        return matchesIteration && matchesEpic;
      }),
    [items, selectedIteration, selectedEpic],
  );

  const columns = useMemo(
    () => buildBoardColumns(project?.status_columns, items),
    [project?.status_columns, items],
  );

  const columnItems = useMemo(() => {
    const buckets = new Map<string, ProjectItem[]>(columns.map((column) => [column.key, []]));
    for (const item of filteredItems) {
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
  }, [columns, filteredItems]);

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
      void fetchDashboards();
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

    const nextIterationId = values.iterationId ?? null;
    const currentIterationId = item.iteration_id ?? null;
    if (nextIterationId !== currentIterationId) {
      payload.iteration_id = nextIterationId;
      payload.iteration_title = values.iterationTitle ?? null;
    }

    const nextEpicId = values.epicOptionId ?? null;
    const currentEpicId = item.epic_option_id ?? null;
    if (nextEpicId !== currentEpicId) {
      payload.epic_option_id = nextEpicId;
      payload.epic_name = values.epicName ?? null;
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
      void fetchDashboards();
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
  }, [editorItem, loadEditorData]);

  const timeline = useMemo(() => {
    const withDates: TimelinePreparedItem[] = filteredItems
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
  }, [filteredItems]);

  const timelineItemIds = useMemo(() => new Set(timeline?.items.map((item) => item.id) ?? []), [timeline]);

  const undatedItems = useMemo(
    () => filteredItems.filter((item) => !timelineItemIds.has(item.id)),
    [filteredItems, timelineItemIds],
  );

  const hasAnyItems = items.length > 0;
  const hasFilteredItems = filteredItems.length > 0;

  const iterationOptionsForEditor = useMemo(() => {
    const map = new Map<string, IterationOption>();
    for (const option of iterationDashboard?.options ?? []) {
      map.set(option.id, option);
    }
    for (const item of items) {
      if (item.iteration_id && !map.has(item.iteration_id)) {
        map.set(item.iteration_id, {
          id: item.iteration_id,
          name: item.iteration ?? item.iteration_id,
          start_date: item.iteration_start ?? item.start_date ?? null,
          end_date: item.iteration_end ?? item.end_date ?? null,
        });
      }
    }
    return Array.from(map.values()).sort((a, b) => {
      const aKey = (a.start_date ?? "") + (a.name ?? "");
      const bKey = (b.start_date ?? "") + (b.name ?? "");
      return aKey.localeCompare(bKey, "pt", { sensitivity: "base" });
    });
  }, [iterationDashboard?.options, items]);

  const epicOptionsForEditor = useMemo(() => {
    const map = new Map<string, EpicOption>();
    for (const option of epicDashboard?.options ?? []) {
    map.set(option.id, { ...option });
  }
  for (const item of items) {
    if (item.epic_option_id && !map.has(item.epic_option_id)) {
      map.set(item.epic_option_id, {
        id: item.epic_option_id,
        name: item.epic_name ?? item.epic_option_id,
        color: null,
      });
    }
  }
  return Array.from(map.values()).sort((a, b) =>
    a.name.localeCompare(b.name, "pt", { sensitivity: "base" }),
    );
  }, [epicDashboard?.options, items]);

  const iterationFilterOptions = useMemo<FilterOption[]>(() => {
    const options: FilterOption[] = [{ value: ALL_ITERATION_VALUE, label: "Todas as sprints" }];
    for (const option of iterationOptionsForEditor) {
      options.push({
        value: option.id,
        label: option.name,
        hint: formatDashboardRange(option.start_date, option.end_date),
      });
    }
    const hasUnassigned =
      (iterationDashboard?.summaries ?? []).some((summary) => summary.iteration_id === null) ||
      items.some((item) => !item.iteration_id);
    if (hasUnassigned) {
      options.push({ value: WITHOUT_ITERATION_VALUE, label: "Sem sprint" });
    }
    return options;
  }, [iterationOptionsForEditor, iterationDashboard?.summaries, items]);

  const epicFilterOptions = useMemo<FilterOption[]>(() => {
    const options: FilterOption[] = [{ value: ALL_EPIC_VALUE, label: "Todos os épicos" }];
    for (const option of epicOptionsForEditor) {
      options.push({ value: option.id, label: option.name });
    }
    const hasUnassigned =
      (epicDashboard?.summaries ?? []).some((summary) => summary.epic_option_id === null) ||
      items.some((item) => !item.epic_option_id);
    if (hasUnassigned) {
      options.push({ value: WITHOUT_EPIC_VALUE, label: "Sem épico" });
    }
    return options;
  }, [epicOptionsForEditor, epicDashboard?.summaries, items]);

  const iterationSummariesForDisplay = useMemo(() => {
    if (!iterationDashboard?.summaries) {
      return [] as IterationSummary[];
    }
    const summaries = iterationDashboard.summaries.slice();
    summaries.sort((a, b) => {
      const aSelected = isIterationSelected(a, selectedIteration);
      const bSelected = isIterationSelected(b, selectedIteration);
      if (aSelected !== bSelected) {
        return aSelected ? -1 : 1;
      }
      const aStart = a.start_date ?? "";
      const bStart = b.start_date ?? "";
      const startCompare = aStart.localeCompare(bStart);
      if (startCompare !== 0) {
        return startCompare;
      }
      const aName = a.name ?? "";
      const bName = b.name ?? "";
      return aName.localeCompare(bName, "pt", { sensitivity: "base" });
    });
    return summaries;
  }, [iterationDashboard?.summaries, selectedIteration]);

  const epicSummariesForDisplay = useMemo(() => {
    if (!epicDashboard?.summaries) {
      return [] as EpicSummary[];
    }
    const summaries = epicDashboard.summaries.slice();
    summaries.sort((a, b) => {
      const aSelected = isEpicSelected(a, selectedEpic);
      const bSelected = isEpicSelected(b, selectedEpic);
      if (aSelected !== bSelected) {
        return aSelected ? -1 : 1;
      }
      const aName = a.name ?? "";
      const bName = b.name ?? "";
      return aName.localeCompare(bName, "pt", { sensitivity: "base" });
    });
    return summaries;
  }, [epicDashboard?.summaries, selectedEpic]);

  useEffect(() => {
    if (
      selectedIteration !== ALL_ITERATION_VALUE &&
      selectedIteration !== WITHOUT_ITERATION_VALUE &&
      !iterationOptionsForEditor.some((option) => option.id === selectedIteration)
    ) {
      setSelectedIteration(ALL_ITERATION_VALUE);
    }
  }, [iterationOptionsForEditor, selectedIteration]);

  useEffect(() => {
    if (
      selectedEpic !== ALL_EPIC_VALUE &&
      selectedEpic !== WITHOUT_EPIC_VALUE &&
      !epicOptionsForEditor.some((option) => option.id === selectedEpic)
    ) {
      setSelectedEpic(ALL_EPIC_VALUE);
    }
  }, [epicOptionsForEditor, selectedEpic]);

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

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="space-y-1">
          <Label htmlFor="filter-iteration">Filtrar por sprint</Label>
          <Select value={selectedIteration} onValueChange={setSelectedIteration}>
            <SelectTrigger id="filter-iteration">
              <SelectValue placeholder="Todas as sprints" />
            </SelectTrigger>
            <SelectContent>
              {iterationFilterOptions.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  <div className="flex flex-col">
                    <span>{option.label}</span>
                    {option.hint ? (
                      <span className="text-xs text-muted-foreground">{option.hint}</span>
                    ) : null}
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1">
          <Label htmlFor="filter-epic">Filtrar por épico</Label>
          <Select value={selectedEpic} onValueChange={setSelectedEpic}>
            <SelectTrigger id="filter-epic">
              <SelectValue placeholder="Todos os épicos" />
            </SelectTrigger>
            <SelectContent>
              {epicFilterOptions.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {dashboardsError ? (
        <div className="rounded-md border border-amber-300 bg-amber-100 p-3 text-xs text-amber-900">
          {dashboardsError}
        </div>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Resumo de sprints</CardTitle>
            <p className="text-xs text-muted-foreground">
              Acompanhe itens sincronizados por iteração.
            </p>
          </CardHeader>
          <CardContent className="space-y-3">
            {dashboardsLoading && !iterationSummariesForDisplay.length ? (
              <p className="text-xs text-muted-foreground">Carregando resumo de sprints...</p>
            ) : iterationSummariesForDisplay.length ? (
              <div className="space-y-3 max-h-72 overflow-y-auto pr-1">
                {iterationSummariesForDisplay.slice(0, 6).map((summary) => {
                  const completion = calculateCompletionPercentage(
                    summary.completed_count,
                    summary.item_count,
                  );
                  const rangeLabel = formatDashboardRange(summary.start_date, summary.end_date);
                  const isActive = isIterationSelected(summary, selectedIteration);
                  const totalEstimate = summary.total_estimate ?? 0;
                  const completedEstimate = summary.completed_estimate ?? 0;
                  const showEstimate = totalEstimate > 0;

                  return (
                    <div
                      key={summary.iteration_id ?? WITHOUT_ITERATION_VALUE}
                      className={cn(
                        "rounded-md border p-3 text-xs transition",
                        isActive ? "border-primary/70 bg-primary/5" : "border-border/60 bg-muted/40",
                      )}
                    >
                      <div className="flex items-center justify-between gap-3">
                        <div>
                          <p className="text-sm font-semibold text-foreground">
                            {summary.name ?? "Sem sprint"}
                          </p>
                          {rangeLabel ? (
                            <p className="text-[11px] text-muted-foreground">{rangeLabel}</p>
                          ) : null}
                          {showEstimate ? (
                            <p className="text-[11px] text-muted-foreground">
                              {formatEstimateValue(completedEstimate)} / {formatEstimateValue(totalEstimate)} pts
                            </p>
                          ) : null}
                        </div>
                        <div className="text-right">
                          <p className="text-sm font-semibold text-foreground">{completion}%</p>
                          <p className="text-[11px] text-muted-foreground">
                            {summary.completed_count}/{summary.item_count} itens
                          </p>
                        </div>
                      </div>
                      <div className="mt-2 h-2 rounded bg-muted">
                        <div
                          className="h-2 rounded bg-primary"
                          style={{ width: `${completion}%` }}
                          aria-hidden
                        />
                      </div>
                      <div className="mt-2 flex flex-wrap gap-2 text-[11px] text-muted-foreground">
                        {summary.status_breakdown.slice(0, 3).map((status) => (
                          <span
                            key={status.status ?? "sem-status"}
                            className="rounded-full bg-background px-2 py-0.5"
                          >
                            {`${status.status ?? "Sem status"}: ${status.count}`}
                          </span>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground">Sem dados de sprint no momento.</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Resumo de épicos</CardTitle>
            <p className="text-xs text-muted-foreground">Entenda o volume por épico sincronizado.</p>
          </CardHeader>
          <CardContent className="space-y-3">
            {dashboardsLoading && !epicSummariesForDisplay.length ? (
              <p className="text-xs text-muted-foreground">Carregando resumo de épicos...</p>
            ) : epicSummariesForDisplay.length ? (
              <div className="space-y-3 max-h-72 overflow-y-auto pr-1">
                {epicSummariesForDisplay.slice(0, 6).map((summary) => {
                  const completion = calculateCompletionPercentage(
                    summary.completed_count,
                    summary.item_count,
                  );
                  const isActive = isEpicSelected(summary, selectedEpic);
                  const totalEstimate = summary.total_estimate ?? 0;
                  const completedEstimate = summary.completed_estimate ?? 0;
                  const showEstimate = totalEstimate > 0;

                  return (
                    <div
                      key={summary.epic_option_id ?? WITHOUT_EPIC_VALUE}
                      className={cn(
                        "rounded-md border p-3 text-xs transition",
                        isActive ? "border-primary/70 bg-primary/5" : "border-border/60 bg-muted/40",
                      )}
                    >
                      <div className="flex items-center justify-between gap-3">
                        <div>
                          <p className="text-sm font-semibold text-foreground">
                            {summary.name ?? "Sem épico"}
                          </p>
                          {showEstimate ? (
                            <p className="text-[11px] text-muted-foreground">
                              {formatEstimateValue(completedEstimate)} / {formatEstimateValue(totalEstimate)} pts
                            </p>
                          ) : null}
                        </div>
                        <div className="text-right">
                          <p className="text-sm font-semibold text-foreground">{completion}%</p>
                          <p className="text-[11px] text-muted-foreground">
                            {summary.completed_count}/{summary.item_count} itens
                          </p>
                        </div>
                      </div>
                      <div className="mt-2 h-2 rounded bg-muted">
                        <div
                          className="h-2 rounded bg-primary"
                          style={{ width: `${completion}%` }}
                          aria-hidden
                        />
                      </div>
                      <div className="mt-2 flex flex-wrap gap-2 text-[11px] text-muted-foreground">
                        {summary.status_breakdown.slice(0, 3).map((status) => (
                          <span
                            key={status.status ?? "sem-status"}
                            className="rounded-full bg-background px-2 py-0.5"
                          >
                            {`${status.status ?? "Sem status"}: ${status.count}`}
                          </span>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground">Sem dados de épico no momento.</p>
            )}
          </CardContent>
        </Card>
      </div>

      {viewMode === "board" ? (
        !hasAnyItems ? (
          <div className="rounded-lg border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
            Nenhum item sincronizado ainda.
          </div>
        ) : !hasFilteredItems ? (
          <div className="rounded-lg border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
            Nenhum item corresponde aos filtros selecionados.
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
      ) : !hasAnyItems ? (
        <div className="rounded-lg border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
          Nenhum item sincronizado ainda.
        </div>
      ) : !hasFilteredItems ? (
        <div className="rounded-lg border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
          Nenhum item corresponde aos filtros selecionados.
        </div>
      ) : !timeline ? (
        <div className="rounded-lg border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
          Nenhum item possui datas configuradas para os filtros atuais.
        </div>
      ) : (
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
      )}

      {/* Hierarquia de Épicos e Histórias */}
      <div className="space-y-4 mt-12 pt-12 border-t">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-semibold tracking-tight">Hierarquia de Épicos e Histórias</h2>
            <p className="text-sm text-muted-foreground">
              Visualize a organização épico → história → tarefa
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant={hierarchyViewMode === "list" ? "default" : "outline"}
              onClick={() => setHierarchyViewMode("list")}
              size="sm"
            >
              Lista
            </Button>
            <Button
              variant={hierarchyViewMode === "flow" ? "default" : "outline"}
              onClick={() => setHierarchyViewMode("flow")}
              size="sm"
            >
              Diagrama
            </Button>
          </div>
        </div>

        {hierarchyLoading ? (
          <div className="rounded-lg border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
            Carregando hierarquia...
          </div>
        ) : (
          <HierarchyView
            hierarchy={hierarchy}
            viewMode={hierarchyViewMode}
            onItemClick={handleCardClick}
          />
        )}
      </div>

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
        iterationOptions={iterationOptionsForEditor}
        epicOptions={epicOptionsForEditor}
      />
    </div>
  );
}
