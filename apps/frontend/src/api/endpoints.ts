import { ApiClient } from "./client";
import type {
  AIResult,
  AISettings,
  Attempt,
  Decision,
  Lab,
  MaterialField,
  MaterialFile,
  Materials,
  Page,
  Profile,
  Statistics,
  SubmissionDetail,
  SubmissionRow,
} from "./types";
const id = encodeURIComponent;
export const getProfile = (api: ApiClient, signal?: AbortSignal) =>
  api.request<Profile>("/me", { signal });
export const getLab = (api: ApiClient, labId: string, signal?: AbortSignal) =>
  api.request<Lab>(`/labs/${id(labId)}`, { signal });
export const getSubmissions = (
  api: ApiClient,
  labId: string,
  query: URLSearchParams,
  signal?: AbortSignal,
) =>
  api.request<Page<SubmissionRow>>(`/labs/${id(labId)}/submissions?${query}`, {
    signal,
  });
export const getStatistics = (
  api: ApiClient,
  labId: string,
  signal?: AbortSignal,
) =>
  api.request<{ statistics: Statistics }>(
    `/labs/${id(labId)}/submissions/statistics`,
    { signal },
  );
export const getGroups = (
  api: ApiClient,
  labId: string,
  signal?: AbortSignal,
) =>
  api.request<{ items: { Academic_group: string }[] }>(
    `/labs/${id(labId)}/submission-groups`,
    { signal },
  );
export const getSubmission = (
  api: ApiClient,
  attemptId: string,
  signal?: AbortSignal,
) =>
  api.request<SubmissionDetail>(`/instructor/attempts/${id(attemptId)}`, {
    signal,
  });
export const review = (
  api: ApiClient,
  attemptId: string,
  decision: Decision,
  comment: string,
  signal?: AbortSignal,
) =>
  api.request(`/instructor/attempts/${id(attemptId)}/review`, {
    method: "POST",
    body: JSON.stringify({ decision, comment }),
    signal,
  });
export const getAttempts = (
  api: ApiClient,
  labId: string,
  page: number,
  signal?: AbortSignal,
) =>
  api.request<Page<Attempt>>(
    `/labs/${id(labId)}/attempts?page=${page}&page_size=7`,
    { signal },
  );
export const getAttempt = (
  api: ApiClient,
  attemptId: string,
  signal?: AbortSignal,
) => api.request<Attempt>(`/attempts/${id(attemptId)}`, { signal });
export const getResult = (
  api: ApiClient,
  attemptId: string,
  signal?: AbortSignal,
) => api.request<AIResult>(`/attempts/${id(attemptId)}/ai-result`, { signal });
export const createAttempt = (
  api: ApiClient,
  labId: string,
  file: File,
  signal?: AbortSignal,
) => {
  const body = new FormData();
  body.set("file", file);
  return api.request<Attempt>(`/labs/${id(labId)}/attempts`, {
    method: "POST",
    body,
    signal,
  });
};
export const submitAttempt = (
  api: ApiClient,
  attemptId: string,
  signal?: AbortSignal,
) =>
  api.request(`/attempts/${id(attemptId)}/submit-to-teacher`, {
    method: "POST",
    signal,
  });
export const uploadMaterial = (
  api: ApiClient,
  labId: string,
  field: MaterialField,
  file: File,
  signal?: AbortSignal,
) => {
  const body = new FormData();
  body.set("field", field);
  body.set("file", file);
  return api.request<MaterialFile>(`/labs/${id(labId)}/ai-settings/files`, {
    method: "POST",
    body,
    signal,
  });
};
export const saveMaterials = (
  api: ApiClient,
  labId: string,
  materials: Materials,
  signal?: AbortSignal,
) =>
  api.request<{ version: number }>(`/labs/${id(labId)}/ai-settings`, {
    method: "PUT",
    body: JSON.stringify(materials),
    signal,
  });
export const deleteMaterial = (
  api: ApiClient,
  labId: string,
  field: MaterialField,
  signal?: AbortSignal,
) =>
  api.request<void>(`/labs/${id(labId)}/ai-settings/${field}`, {
    method: "DELETE",
    signal,
  });
export async function downloadFile(
  api: ApiClient,
  fileId: string,
  name: string,
  signal?: AbortSignal,
) {
  const blob = await api.request<Blob>(
    `/files/${id(fileId)}/download`,
    { signal },
    "blob",
  );
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export const getMaterials = (
  api: ApiClient,
  labId: string,
  signal?: AbortSignal,
) => api.request<AISettings>(`/labs/${id(labId)}/ai-settings`, { signal });
