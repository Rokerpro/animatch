import type { AnimeDetailData, AnimeListParams, AnimeListResponse, AuthProvidersResponse, CsrfTokenResponse, FeaturesResponse, FiltersResponse, LoginRequest, NaturalLanguageRequest, NaturalLanguageResponse, Recommendation, RegisterRequest, UserResponse, UserUpdateRequest, QuizQuestion, QuizResponse, TasteProfile, ListEntryPut, ListEntryResponse, ListParams, ListResponse, ListStatusesResponse, MALImportResponse, NewRecommendationsRequest, NewRecommendationsResponse } from "./types";

export function normalizeApiBaseUrl(configuredBase: string | undefined) {
  // Use the same origin by default so Vite or Nginx can proxy /api to the backend.
  const value = configuredBase ?? "/api";
  return value.replace(/\/api\/?$/, "").replace(/\/$/, "");
}
const baseUrl = normalizeApiBaseUrl(import.meta.env.VITE_API_URL);
export class ApiError extends Error {
  constructor(message: string, public status: number, public code?: string) { super(message); this.name = "ApiError"; }
}
export function apiDetailMessage(detail: unknown, fallback = "Request failed"): string {
  if (typeof detail === "string" && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    const messages = detail.flatMap((item: unknown) => {
      if (!item || typeof item !== "object" || !("msg" in item)) return [];
      const value = (item as { msg?: unknown }).msg;
      return typeof value === "string" && value.trim() ? [value] : [];
    });
    if (messages.length) return messages.join("; ");
  }
  return fallback;
}
export function getErrorMessage(error: unknown, fallback: string): string {
  return error instanceof Error && error.message.trim() ? error.message : fallback;
}
async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const controller = new AbortController();
  let timedOut = false;
  const timeoutId = window.setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, 15_000);
  const forwardAbort = () => controller.abort();
  if (init.signal?.aborted) controller.abort();
  else init.signal?.addEventListener("abort", forwardAbort, { once: true });

  try {
    const response = await fetch(`${baseUrl}${path}`, {
      ...init,
      credentials: "include",
      signal: controller.signal,
      headers: { ...(init.body ? { "Content-Type": "application/json" } : {}), ...init.headers },
    });
    if (!response.ok) {
      let message = response.statusText || "Request failed";
      let code: string | undefined;
      try {
        const data: unknown = await response.json();
        if (data && typeof data === "object" && "detail" in data) {
          message = apiDetailMessage((data as { detail?: unknown }).detail, message);
        }
        if (data && typeof data === "object" && "code" in data && typeof (data as { code?: unknown }).code === "string") code = (data as { code: string }).code;
      } catch { /* response has no JSON body */ }
      throw new ApiError(typeof message === "string" ? message : "Request failed", response.status, code);
    }
    return await response.json() as T;
  } catch (error) {
    if (timedOut) {
      throw new ApiError("The server took too long to respond. Check that the backend is running and try again.", 0);
    }
    throw error;
  } finally {
    window.clearTimeout(timeoutId);
    init.signal?.removeEventListener("abort", forwardAbort);
  }
}
export function buildAnimeQuery(params: AnimeListParams): string {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === "") continue;
    if (Array.isArray(value)) value.forEach((item) => query.append(key, item));
    else query.set(key, String(value));
  }
  return query.toString();
}
export const api = {
  features: (signal?: AbortSignal) => request<FeaturesResponse>("/api/features", { signal }),
  askRecommendations: async (body: NaturalLanguageRequest, signal?: AbortSignal) => {
    const csrf = await api.csrf(signal);
    return request<NaturalLanguageResponse>("/api/recs/ask", { method: "POST", headers: { "X-CSRF-Token": csrf.csrf_token }, body: JSON.stringify(body), signal });
  },
  anime: (params: AnimeListParams, signal?: AbortSignal) => request<AnimeListResponse>(`/api/anime?${buildAnimeQuery(params)}`, { signal }),
  filters: (includeMature: boolean) => request<FiltersResponse>(`/api/anime/filters?includeMature=${includeMature}`),
  detail: (id: number, includeMature: boolean) => request<AnimeDetailData>(`/api/anime/${id}?includeMature=${includeMature}`),
  similar: (id: number, includeMature: boolean) => request<Recommendation[]>(`/api/recs/similar/${id}?includeMature=${includeMature}`),
  quiz: (signal?: AbortSignal) => request<QuizQuestion[]>("/api/quiz", { signal }),
  newRecommendations: async (body: NewRecommendationsRequest) => {
    const csrf = await api.csrf();
    return request<NewRecommendationsResponse>("/api/recs/new", { method: "POST", headers: { "X-CSRF-Token": csrf.csrf_token }, body: JSON.stringify(body) });
  },
  quizRecommendations: (answers: Record<string, string>, includeMature: boolean) => request<QuizResponse>("/api/recs/quiz", { method: "POST", body: JSON.stringify({ answers, includeMature }) }),
  startRecommendations: (likedIds: number[], includeMature: boolean) => request<Recommendation[]>("/api/recs/start", { method: "POST", body: JSON.stringify({ liked_ids: likedIds, include_mature: includeMature }) }),
  myRecommendations: (includeMature: boolean) => request<Recommendation[]>(`/api/recs/me?includeMature=${includeMature}`),
  list: (params: ListParams) => {
    const query = new URLSearchParams({ sort: params.sort, page: String(params.page), pageSize: String(params.pageSize), includeMature: String(params.includeMature) });
    if (params.status) query.set("status", params.status);
    return request<ListResponse>(`/api/list?${query.toString()}`);
  },
  listStatuses: (ids: number[], includeMature: boolean) => request<ListStatusesResponse>(`/api/list/statuses?ids=${ids.join(",")}&includeMature=${includeMature}`),
  updateListEntry: async (animeId: number, body: ListEntryPut) => {
    const csrf = await api.csrf();
    return request<ListEntryResponse>(`/api/list/${animeId}`, { method: "PUT", headers: { "X-CSRF-Token": csrf.csrf_token }, body: JSON.stringify(body) });
  },
  importMALList: async (file: File, dryRun: boolean) => {
    const csrf = await api.csrf();
    return request<MALImportResponse>(`/api/list/import?dry_run=${dryRun}`, { method: "POST", headers: { "X-CSRF-Token": csrf.csrf_token, "Content-Type": "application/octet-stream" }, body: file });
  },
  deleteListEntry: async (animeId: number) => {
    const csrf = await api.csrf();
    return request<{ message: string }>(`/api/list/${animeId}`, { method: "DELETE", headers: { "X-CSRF-Token": csrf.csrf_token } });
  },
  me: () => request<UserResponse | null>("/api/auth/me"),
  providers: () => request<AuthProvidersResponse>("/api/auth/providers"),
  login: (body: LoginRequest) => request<UserResponse>("/api/auth/login", { method: "POST", body: JSON.stringify(body) }),
  register: (body: RegisterRequest) => request<UserResponse>("/api/auth/register", { method: "POST", body: JSON.stringify(body) }),
  logout: async () => {
    const csrf = await api.csrf();
    return request<Record<string, string>>("/api/auth/logout", { method: "POST", headers: { "X-CSRF-Token": csrf.csrf_token } });
  },
  tasteProfile: () => request<TasteProfile>("/api/auth/me/taste-profile"),
  saveTasteProfile: async (body: TasteProfile) => {
    const csrf = await api.csrf();
    return request<TasteProfile>("/api/auth/me/taste-profile", { method: "PUT", headers: { "X-CSRF-Token": csrf.csrf_token }, body: JSON.stringify(body) });
  },
  deleteMe: async () => {
    const csrf = await api.csrf();
    return request<Record<string, string>>("/api/auth/me", { method: "DELETE", headers: { "X-CSRF-Token": csrf.csrf_token } });
  },
  googleLogin: () => `${baseUrl}/api/auth/google/login`,
  csrf: (signal?: AbortSignal) => request<CsrfTokenResponse>("/api/auth/csrf", { signal }),
  updateMe: async (body: UserUpdateRequest) => {
    const csrf = await api.csrf();
    return request<UserResponse>("/api/auth/me", { method: "PATCH", headers: { "X-CSRF-Token": csrf.csrf_token }, body: JSON.stringify(body) });
  },
};
