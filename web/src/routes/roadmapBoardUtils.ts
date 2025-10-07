const DEFAULT_STATUSES = ["Backlog", "Sprint Atual", "In Review", "Done"];
const UNASSIGNED_COLUMN_KEY = "__unassigned__";

export interface BoardColumn {
  key: string;
  title: string;
  status: string | null;
}

export interface ProjectItemLike {
  status?: string | null;
}

export function normalizeStatusValue(value: string | null | undefined): string | null {
  if (!value) {
    return null;
  }
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function slugifyStatus(value: string): string {
  return value
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 40) || "stage";
}

export function buildColumnKey(status: string | null): string {
  if (status === null) {
    return UNASSIGNED_COLUMN_KEY;
  }
  return `stage-${slugifyStatus(status)}`;
}

export function buildBoardColumns(
  projectStatuses: string[] | null | undefined,
  items: ProjectItemLike[],
): BoardColumn[] {
  const normalizedStatuses = (projectStatuses && projectStatuses.length > 0 ? projectStatuses : DEFAULT_STATUSES)
    .map(normalizeStatusValue)
    .filter((status): status is string => status !== null);

  const uniqueStatuses: string[] = [];
  const seen = new Set<string>();
  let doneLabel: string | null = null;

  for (const status of normalizedStatuses) {
    if (seen.has(status)) {
      continue;
    }
    if (status.toLowerCase() === "done") {
      doneLabel = status;
      seen.add(status);
      continue;
    }
    uniqueStatuses.push(status);
    seen.add(status);
  }

  for (const item of items) {
    const status = normalizeStatusValue(item.status ?? null);
    if (!status || seen.has(status)) {
      continue;
    }
    if (status.toLowerCase() === "done") {
      doneLabel = status;
    } else {
      uniqueStatuses.push(status);
    }
    seen.add(status);
  }

  const orderedStatuses = doneLabel ? [...uniqueStatuses, doneLabel] : uniqueStatuses;

  return [
    { key: UNASSIGNED_COLUMN_KEY, title: "Sem etapa", status: null },
    ...orderedStatuses.map((status) => ({
      key: buildColumnKey(status),
      title: status,
      status,
    })),
  ];
}

export { DEFAULT_STATUSES, UNASSIGNED_COLUMN_KEY };
