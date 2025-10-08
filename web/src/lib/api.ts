export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") || "http://localhost:8000";

const ACTIVE_PROJECT_KEY = "tactyo:active-project-id";

type HttpMethod = "GET" | "POST" | "PATCH" | "PUT" | "DELETE";

export interface ApiRequestOptions extends RequestInit {
  method?: HttpMethod;
  parseJson?: boolean;
}

export async function apiFetch<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
  const { parseJson = true, headers, ...rest } = options;

  // Ler projeto ativo do localStorage e incluir no header
  const activeProjectId = localStorage.getItem(ACTIVE_PROJECT_KEY);
  const projectHeaders: Record<string, string> = {};
  if (activeProjectId) {
    projectHeaders["X-Project-Id"] = activeProjectId;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...projectHeaders,
      ...headers,
    },
    ...rest,
  });

  if (!response.ok) {
    const message = await extractErrorMessage(response);
    throw new Error(message);
  }

  if (!parseJson) {
    // @ts-expect-error intentionally returning raw response when caller opts out of JSON parsing
    return response;
  }

  return (await response.json()) as T;
}

async function extractErrorMessage(response: Response): Promise<string> {
  try {
    const data = await response.json();
    if (typeof data === "string") {
      return data;
    }
    if (data?.detail) {
      if (typeof data.detail === "string") {
        return data.detail;
      }
      if (Array.isArray(data.detail)) {
        const firstDetail = data.detail[0];
        if (typeof firstDetail === "string") {
          return firstDetail;
        }
        if (firstDetail?.msg) {
          return firstDetail.msg as string;
        }
      }
    }
    if (data?.message) {
      return data.message;
    }
  } catch {
    // ignore JSON parse errors
  }
  return `${response.status} ${response.statusText}`;
}
