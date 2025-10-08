/**
 * API client for Epic management endpoints
 */

import { apiFetch } from "./api";

export interface EpicOption {
  id: string;
  name: string;
  color: string | null;
}

export interface EpicOptionCreate {
  option_name: string;
  color?: string;
  description?: string;
}

export interface EpicOptionUpdate {
  option_name?: string;
  color?: string;
  description?: string;
}

/**
 * List all epics for the current project
 */
export async function listEpics(): Promise<EpicOption[]> {
  return apiFetch<EpicOption[]>(`/api/projects/current/epics`);
}

/**
 * Get a specific epic
 */
export async function getEpic(epicId: string): Promise<EpicOption> {
  return apiFetch<EpicOption>(`/api/projects/current/epics/${epicId}`);
}

/**
 * Create a new epic
 * Note: Creating epics should be done in GitHub Projects V2
 */
export async function createEpic(data: EpicOptionCreate): Promise<EpicOption> {
  return apiFetch<EpicOption>(`/api/projects/current/epics`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

/**
 * Update an existing epic
 * Note: Updating epics should be done in GitHub Projects V2
 */
export async function updateEpic(
  epicId: string,
  data: EpicOptionUpdate
): Promise<EpicOption> {
  return apiFetch<EpicOption>(`/api/projects/current/epics/${epicId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

/**
 * Delete an epic
 * Note: Deleting epics should be done in GitHub Projects V2
 */
export async function deleteEpic(epicId: string): Promise<void> {
  await apiFetch(`/api/projects/current/epics/${epicId}`, {
    method: "DELETE",
    parseJson: false,
  });
}
