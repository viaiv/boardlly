/**
 * API client and types for Project Hierarchy (Epic > Story > Task)
 */

import { apiFetch } from "./api";

export type ItemType = "story" | "task" | "feature" | "bug";

export interface HierarchyItem {
  id: number;
  item_node_id: string;
  title: string | null;
  item_type: ItemType | null;
  status: string | null;
  epic_name: string | null;
  parent_item_id: number | null;
  labels: string[] | null;
  children: HierarchyItem[];
}

export interface HierarchyEpic {
  epic_option_id: string | null;
  epic_name: string | null;
  items: HierarchyItem[];
}

export interface HierarchyResponse {
  epics: HierarchyEpic[];
  orphans: HierarchyItem[];
}

/**
 * Get the complete hierarchy for the current project
 */
export async function getProjectHierarchy(): Promise<HierarchyResponse> {
  return apiFetch<HierarchyResponse>(`/api/projects/current/hierarchy`);
}

/**
 * Helper to flatten hierarchy into a list
 */
export function flattenHierarchy(hierarchy: HierarchyResponse): HierarchyItem[] {
  const items: HierarchyItem[] = [];

  function collectItems(item: HierarchyItem) {
    items.push(item);
    item.children.forEach(collectItems);
  }

  hierarchy.epics.forEach((epic) => {
    epic.items.forEach(collectItems);
  });

  hierarchy.orphans.forEach(collectItems);

  return items;
}

/**
 * Helper to count items by type
 */
export function countByType(hierarchy: HierarchyResponse): Record<string, number> {
  const items = flattenHierarchy(hierarchy);
  const counts: Record<string, number> = {};

  items.forEach((item) => {
    const type = item.item_type || "undefined";
    counts[type] = (counts[type] || 0) + 1;
  });

  return counts;
}

/**
 * Helper to get all stories
 */
export function getStories(hierarchy: HierarchyResponse): HierarchyItem[] {
  return flattenHierarchy(hierarchy).filter((item) => item.item_type === "story");
}

/**
 * Helper to get all tasks
 */
export function getTasks(hierarchy: HierarchyResponse): HierarchyItem[] {
  return flattenHierarchy(hierarchy).filter(
    (item) => item.item_type === "task" || item.item_type === "feature" || item.item_type === "bug"
  );
}
