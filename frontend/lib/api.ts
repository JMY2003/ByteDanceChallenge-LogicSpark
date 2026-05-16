import type {
  AgentRun,
  CompetitorProfile,
  DagResponse,
  EvidenceItem,
  ProjectCreated,
  ProjectHistoryItem,
  ProjectStatus,
  ReportResponse
} from "@/types/api";

function getApiBase() {
  if (typeof window === "undefined") {
    return process.env.INTERNAL_API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
  }
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${getApiBase()}${path}`;
  let response: Response;
  try {
    response = await fetch(url, {
      ...init,
      cache: "no-store",
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers ?? {})
      }
    });
  } catch {
    throw new Error(`无法连接后端 API：${url}。请确认 FastAPI 已启动，且 CORS 允许当前前端地址。`);
  }
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`${response.status} ${response.statusText}: ${detail}`);
  }
  return (await response.json()) as T;
}

export async function createProject(payload: {
  query: string;
  mode: string;
  language: string;
  output_formats: string[];
  max_competitors: number;
  enable_deep_review: boolean;
}): Promise<ProjectCreated> {
  return apiFetch<ProjectCreated>("/api/projects", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function runProject(projectId: string): Promise<ProjectStatus> {
  return apiFetch<ProjectStatus>(`/api/projects/${projectId}/run`, { method: "POST" });
}

export async function getProjectStatus(projectId: string): Promise<ProjectStatus> {
  return apiFetch<ProjectStatus>(`/api/projects/${projectId}/status`);
}

export async function getProjectHistory(): Promise<ProjectHistoryItem[]> {
  const response = await apiFetch<{ projects: ProjectHistoryItem[] }>("/api/projects/history");
  return response.projects;
}

export async function getDag(projectId: string): Promise<DagResponse> {
  return apiFetch<DagResponse>(`/api/projects/${projectId}/dag`);
}

export async function getAgentRuns(projectId: string): Promise<AgentRun[]> {
  return apiFetch<AgentRun[]>(`/api/projects/${projectId}/agent-runs`);
}

export async function getCompetitors(projectId: string): Promise<CompetitorProfile[]> {
  const response = await apiFetch<{ competitors: CompetitorProfile[] }>(`/api/projects/${projectId}/competitors`);
  return response.competitors;
}

export async function getEvidence(projectId: string): Promise<EvidenceItem[]> {
  const response = await apiFetch<{ evidence: EvidenceItem[] }>(`/api/projects/${projectId}/evidence`);
  return response.evidence;
}

export async function getEvidenceItem(projectId: string, evidenceId: string): Promise<EvidenceItem> {
  return apiFetch<EvidenceItem>(`/api/projects/${projectId}/evidence/${evidenceId}`);
}

export async function getReport(projectId: string): Promise<ReportResponse> {
  return apiFetch<ReportResponse>(`/api/projects/${projectId}/report`);
}

export async function saveReport(projectId: string, markdown: string): Promise<ReportResponse> {
  return apiFetch<ReportResponse>(`/api/projects/${projectId}/report`, {
    method: "PATCH",
    body: JSON.stringify({ markdown })
  });
}

export async function exportReport(projectId: string, format: "markdown" | "html" | "json" | "ppt_outline") {
  return apiFetch<{ filename: string; content_type: string; content: string }>(`/api/projects/${projectId}/export`, {
    method: "POST",
    body: JSON.stringify({ format })
  });
}
