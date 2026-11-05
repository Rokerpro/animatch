import type { AnimeDetailData, AnimeListParams, AnimeListResponse, AuthProvidersResponse, CsrfTokenResponse, FiltersResponse, LoginRequest, Recommendation, RegisterRequest, UserResponse, UserUpdateRequest, QuizQuestion, QuizResponse, TasteProfile } from "./types";

export function normalizeApiBaseUrl(configuredBase: string | undefined) {
  // Use the same origin by default so Vite or Nginx can proxy /api to the backend.
  const value = configuredBase ?? "/api";
  return value.replace(/\/api\/?$/, "").replace(/\/$/, "");
}
const baseUrl = normalizeApiBaseUrl(import.meta.env.VITE_API_URL);
export class ApiError extends Error {
  constructor(message: string, public status: number) { super(message); this.name = "ApiError"; }
}
async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`, {
    ...init, credentials: "include",
    headers: { ...(init.body ? { "Content-Type": "application/json" } : {}), ...init.headers },
  });
  if (!response.ok) {
    let message = response.statusText;
    try {
      const data: unknown = await response.json();
      if (data && typeof data === "object" && "detail" in data) {
        const detail = (data as { detail?: unknown }).detail;
        if (typeof detail === "string") message = detail;
        else if (Array.isArray(detail)) {
          const messages = detail.flatMap((item: unknown) => {
            if (!item || typeof item !== "object" || !("msg" in item)) return [];
            const value = (item as { msg?: unknown }).msg;
            return typeof value === "string" ? [value] : [];
          });
          if (messages.length) message = messages.join("; ");
        }
      }
    } catch { /* response has no JSON body */ }
    throw new ApiError(typeof message === "string" ? message : "Request failed", response.status);
  }
  return response.json() as Promise<T>;
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
  anime: (params: AnimeListParams, signal?: AbortSignal) => request<AnimeListResponse>(`/api/anime?${buildAnimeQuery(params)}`, { signal }),
  filters: (includeMature: boolean) => request<FiltersResponse>(`/api/anime/filters?includeMature=${includeMature}`),
  detail: (id: number, includeMature: boolean) => request<AnimeDetailData>(`/api/anime/${id}?includeMature=${includeMature}`),
  similar: (id: number, includeMature: boolean) => request<Recommendation[]>(`/api/recs/similar/${id}?includeMature=${includeMature}`),
  quiz: (signal?: AbortSignal) => request<QuizQuestion[]>("/api/quiz", { signal }),
  quizRecommendations: (answers: Record<string, string>, includeMature: boolean) => request<QuizResponse>("/api/recs/quiz", { method: "POST", body: JSON.stringify({ answers, includeMature }) }),
  startRecommendations: (likedIds: number[], includeMature: boolean) => request<Recommendation[]>("/api/recs/start", { method: "POST", body: JSON.stringify({ liked_ids: likedIds, include_mature: includeMature }) }),
  myRecommendations: (includeMature: boolean) => request<Recommendation[]>(`/api/recs/me?includeMature=${includeMature}`),
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
  csrf: () => request<CsrfTokenResponse>("/api/auth/csrf"),
  updateMe: async (body: UserUpdateRequest) => {
    const csrf = await api.csrf();
    return request<UserResponse>("/api/auth/me", { method: "PATCH", headers: { "X-CSRF-Token": csrf.csrf_token }, body: JSON.stringify(body) });
  },
};
