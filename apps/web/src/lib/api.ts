const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface UploadResponse {
  project_id: string;
  image_url: string;
  status: string;
}

export interface ProjectResponse {
  id: string;
  image_url: string;
  status: string;
  created_at: string;
  layers: Array<Record<string, unknown>>;
  psd_url: string | null;
}

export interface UsageResponse {
  remaining: number;
  plan: string;
  total: number;
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const { headers: customHeaders, ...rest } = options ?? {};

  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...customHeaders,
    },
    ...rest,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail ?? `API error: ${response.status}`);
  }

  return response.json();
}

export async function uploadImage(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE}/api/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Upload failed" }));
    throw new Error(error.detail ?? "Upload failed");
  }

  return response.json();
}

export async function getProject(projectId: string): Promise<ProjectResponse> {
  return apiFetch<ProjectResponse>(`/api/project/${projectId}`);
}

export async function getUsage(): Promise<UsageResponse> {
  return apiFetch<UsageResponse>("/api/usage");
}

export interface RemoveElementResponse {
  success: boolean;
  background_url: string;
  quality_score: number;
  warning: string | null;
}

export async function removeElement(
  projectId: string,
  layerId: string,
): Promise<RemoveElementResponse> {
  return apiFetch<RemoveElementResponse>(
    `/api/project/${projectId}/layer/${layerId}/remove`,
    { method: "POST" },
  );
}

export interface BatchRemoveResult {
  layer_id: string;
  quality_score: number;
  warning: string | null;
}

export interface BatchRemoveResponse {
  success: boolean;
  results: BatchRemoveResult[];
  background_url: string;
}

export async function removeElementsBatch(
  projectId: string,
  layerIds: string[],
): Promise<BatchRemoveResponse> {
  return apiFetch<BatchRemoveResponse>(
    `/api/project/${projectId}/layers/remove-batch`,
    {
      method: "POST",
      body: JSON.stringify({ layer_ids: layerIds }),
    },
  );
}
