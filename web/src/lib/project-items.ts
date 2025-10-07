export interface ProjectItem {
  id: number;
  item_node_id: string;
  title?: string | null;
  status?: string | null;
  content_type?: string | null;
  iteration?: string | null;
  iteration_id?: string | null;
  estimate?: number | null;
  url?: string | null;
  assignees?: string[];
  updated_at?: string | null;
  last_synced_at?: string | null;
  remote_updated_at?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  due_date?: string | null;
  iteration_start?: string | null;
  iteration_end?: string | null;
  field_values?: Record<string, unknown> | null;
  epic_option_id?: string | null;
  epic_name?: string | null;
}

export interface ProjectItemComment {
  id: string;
  author: string | null;
  author_url?: string | null;
  author_avatar_url?: string | null;
  body: string;
  url?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface ProjectItemDetails {
  id: string;
  content_type?: string | null;
  number?: number | null;
  title?: string | null;
  body?: string | null;
  body_text?: string | null;
  state?: string | null;
  merged?: boolean | null;
  url?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  author?: {
    login?: string | null;
    url?: string | null;
    avatar_url?: string | null;
  } | null;
  labels: { name: string; color?: string | null }[];
}

export interface ItemClassification {
  typeLabel: string | null;
  accent: "epic" | "issue" | "pull-request" | "draft" | "other";
  epicName: string | null;
}

const TYPE_HINT_KEYS = ["type", "tipo", "work item type", "item type", "categoria", "category"];
const EPIC_HINT_VALUES = new Set(["epic", "épico", "epico", "epics"]);
const EPIC_LINK_KEYS = ["epic", "épico", "epic link", "parent epic", "parent issue", "epic name"];

function pickFieldValue(fieldValues: Record<string, unknown> | null | undefined, keys: string[]): string | null {
  if (!fieldValues) {
    return null;
  }
  const entries = Object.entries(fieldValues);
  for (const key of keys) {
    const match = entries.find(([candidate]) => candidate.toLowerCase().trim() === key.toLowerCase().trim());
    if (match) {
      const value = match[1];
      if (value === null || value === undefined) {
        continue;
      }
      const stringValue = String(value).trim();
      if (stringValue.length > 0) {
        return stringValue;
      }
    }
  }
  return null;
}

function normalizeType(value: string | null | undefined): string | null {
  if (!value) {
    return null;
  }
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

export function classifyProjectItem(item: ProjectItem): ItemClassification {
  const explicitEpic = normalizeType(item.epic_name);
  const typeFromFields = pickFieldValue(item.field_values, TYPE_HINT_KEYS);
  const normalizedFieldType = normalizeType(typeFromFields);
  const normalizedContentType = normalizeType(item.content_type);

  let typeLabel: string | null = null;
  let accent: ItemClassification["accent"] = "other";

  if (normalizedFieldType) {
    const lower = normalizedFieldType.toLowerCase();
    if (EPIC_HINT_VALUES.has(lower)) {
      typeLabel = "Épico";
      accent = "epic";
    } else if (lower === "issue" || lower === "história" || lower === "story") {
      typeLabel = "Issue";
      accent = "issue";
    } else if (lower === "pull request" || lower === "pr") {
      typeLabel = "Pull Request";
      accent = "pull-request";
    } else {
      typeLabel = normalizedFieldType;
      accent = "other";
    }
  } else if (normalizedContentType) {
    const lower = normalizedContentType.toLowerCase();
    if (lower === "issue") {
      typeLabel = "Issue";
      accent = "issue";
    } else if (lower === "pullrequest") {
      typeLabel = "Pull Request";
      accent = "pull-request";
    } else if (lower === "draftissue") {
      typeLabel = "Draft";
      accent = "draft";
    }
  }

  if (!typeLabel) {
    typeLabel = "Item";
    accent = "other";
  }

  const epicName = explicitEpic ?? pickFieldValue(item.field_values, EPIC_LINK_KEYS);

  return {
    typeLabel,
    accent,
    epicName,
  };
}

export function classificationBadgeClass(accent: ItemClassification["accent"]): string {
  switch (accent) {
    case "epic":
      return "bg-purple-100 text-purple-700 border border-purple-200 dark:bg-purple-950/40 dark:text-purple-100";
    case "issue":
      return "bg-blue-100 text-blue-700 border border-blue-200 dark:bg-blue-950/40 dark:text-blue-100";
    case "pull-request":
      return "bg-emerald-100 text-emerald-700 border border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-100";
    case "draft":
      return "bg-amber-100 text-amber-700 border border-amber-200 dark:bg-amber-950/40 dark:text-amber-100";
    default:
      return "bg-muted text-muted-foreground border border-border/60";
  }
}

export function formatDateForInput(value: string | null | undefined): string | null {
  if (!value) {
    return null;
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return null;
  }
  return parsed.toISOString().slice(0, 10);
}

export function convertDateInputToIso(value: string | null): string | null {
  if (!value) {
    return null;
  }
  const parsed = new Date(`${value}T00:00:00Z`);
  if (Number.isNaN(parsed.getTime())) {
    return null;
  }
  return parsed.toISOString();
}

export function formatDateDisplay(value: string | Date | null | undefined): string | null {
  if (!value) {
    return null;
  }
  const parsed = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return null;
  }
  return parsed.toLocaleString();
}
