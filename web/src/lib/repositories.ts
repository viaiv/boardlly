/**
 * API client for Project Repository management endpoints
 */

import { apiFetch } from "./api";

export interface ProjectRepository {
  id: number;
  project_id: number;
  owner: string;
  repo_name: string;
  repo_node_id: string | null;
  is_primary: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProjectRepositoryCreate {
  owner: string;
  repo_name: string;
  is_primary?: boolean;
}

export interface ProjectRepositoryUpdate {
  is_primary?: boolean;
}

/**
 * Lista todos os repositórios vinculados ao projeto
 */
export async function listRepositories(): Promise<ProjectRepository[]> {
  return apiFetch<ProjectRepository[]>(`/api/projects/current/repositories`);
}

/**
 * Adiciona um repositório ao projeto
 */
export async function createRepository(
  data: ProjectRepositoryCreate
): Promise<ProjectRepository> {
  return apiFetch<ProjectRepository>(`/api/projects/current/repositories`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

/**
 * Atualiza um repositório do projeto
 */
export async function updateRepository(
  repositoryId: number,
  data: ProjectRepositoryUpdate
): Promise<ProjectRepository> {
  return apiFetch<ProjectRepository>(
    `/api/projects/current/repositories/${repositoryId}`,
    {
      method: "PATCH",
      body: JSON.stringify(data),
    }
  );
}

/**
 * Remove um repositório do projeto
 */
export async function deleteRepository(repositoryId: number): Promise<void> {
  await apiFetch(`/api/projects/current/repositories/${repositoryId}`, {
    method: "DELETE",
    parseJson: false,
  });
}
