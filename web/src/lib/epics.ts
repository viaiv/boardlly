/**
 * API client for Epic management endpoints
 */

import { apiFetch } from "./api";

/**
 * Cores permitidas pelo GitHub Projects V2 para campos Single Select
 */
export const GITHUB_COLORS = [
  { value: "GRAY", label: "Cinza", hex: "#6b7280" },
  { value: "BLUE", label: "Azul", hex: "#3b82f6" },
  { value: "GREEN", label: "Verde", hex: "#10b981" },
  { value: "YELLOW", label: "Amarelo", hex: "#f59e0b" },
  { value: "ORANGE", label: "Laranja", hex: "#f97316" },
  { value: "RED", label: "Vermelho", hex: "#ef4444" },
  { value: "PURPLE", label: "Roxo", hex: "#a855f7" },
  { value: "PINK", label: "Rosa", hex: "#ec4899" },
  { value: "BROWN", label: "Marrom", hex: "#92400e" },
  { value: "BLACK", label: "Preto", hex: "#000000" },
] as const;

export type GithubColor = typeof GITHUB_COLORS[number]["value"];

/**
 * Mapeia o nome da cor do GitHub para o código hex correspondente
 */
export function getColorHex(colorName: string | null): string {
  if (!colorName) return GITHUB_COLORS[1].hex; // Default: BLUE
  const color = GITHUB_COLORS.find(c => c.value === colorName.toUpperCase());
  return color?.hex || GITHUB_COLORS[1].hex;
}

/**
 * Mapeia o código hex de volta para o nome da cor do GitHub
 */
export function getColorName(colorHex: string | null): string {
  if (!colorHex) return "BLUE"; // Default
  // Remove # se presente
  const hex = colorHex.replace('#', '').toLowerCase();
  const color = GITHUB_COLORS.find(c => c.hex.replace('#', '').toLowerCase() === hex);
  return color?.value || "BLUE";
}

export interface EpicOption {
  id: number;
  name: string;
  color: string | null;
  description?: string | null;
}

export interface EpicOptionCreate {
  name: string;
  color?: string;
  description?: string;
}

export interface EpicOptionUpdate {
  name?: string;
  color?: string;
  description?: string;
}

/**
 * List all epic options (from Epic field in GitHub Projects)
 */
export async function listEpics(): Promise<EpicOption[]> {
  return apiFetch<EpicOption[]>(`/api/projects/current/epics/options`);
}

/**
 * Get a specific epic
 */
export async function getEpic(epicId: number): Promise<EpicOption> {
  return apiFetch<EpicOption>(`/api/projects/current/epics/${epicId}`);
}

/**
 * Create a new epic (label) in all project repositories
 */
export async function createEpic(data: EpicOptionCreate): Promise<EpicOption> {
  return apiFetch<EpicOption>(`/api/projects/current/epics/options`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

/**
 * Update an existing epic (label) in all project repositories
 */
export async function updateEpic(
  epicId: number,
  data: EpicOptionUpdate
): Promise<EpicOption> {
  return apiFetch<EpicOption>(`/api/projects/current/epics/options/${epicId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

/**
 * Delete an epic (label) from all project repositories
 */
export async function deleteEpic(epicId: number): Promise<void> {
  await apiFetch(`/api/projects/current/epics/options/${epicId}`, {
    method: "DELETE",
    parseJson: false,
  });
}
