import type { AnimeDetailData, AnimeListParams, AnimeListResponse, AuthProvidersResponse, CsrfTokenResponse, FiltersResponse, LoginRequest, Recommendation, RegisterRequest, UserResponse, UserUpdateRequest, QuizQuestion, QuizResponse } from "./types";

export function normalizeApiBaseUrl(configuredBase: string | undefined) {
  const value = configuredBase ?? "http://localhost:8000";
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
    try { const data = await response.json(); message = data.detail ?? message; } catch { /* response has no JSON body */ }
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
  anime: (params: AnimeListParams) => request<AnimeListResponse>(`/api/anime?${buildAnimeQuery(params)}`),
  filters: (includeMature: boolean) => request<FiltersResponse>(`/api/anime/filters?includeMature=${includeMature}`),
  detail: (id: number, includeMature: boolean) => request<AnimeDetailData>(`/api/anime/${id}?includeMature=${includeMature}`),
  similar: (id: number, includeMature: boolean) => request<Recommendation[]>(`/api/recs/similar/${id}?includeMature=${includeMature}`),
  quiz: () => request<QuizQuestion[]>("/api/quiz"),
  quizRecommendations: (answers: Record<string, string>, includeMature: boolean) => request<QuizResponse>("/api/recs/quiz", { method: "POST", body: JSON.stringify({ answers, includeMature }) }),
  me: () => request<UserResponse>("/api/auth/me"),
  providers: () => request<AuthProvidersResponse>("/api/auth/providers"),
  login: (body: LoginRequest) => request<UserResponse>("/api/auth/login", { method: "POST", body: JSON.stringify(body) }),
  register: (body: RegisterRequest) => request<UserResponse>("/api/auth/register", { method: "POST", body: JSON.stringify(body) }),
  googleLogin: () => `${baseUrl}/api/auth/google/login`,
  csrf: () => request<CsrfTokenResponse>("/api/auth/csrf"),
  updateMe: async (body: UserUpdateRequest) => {
    const csrf = await api.csrf();
    return request<UserResponse>("/api/auth/me", { method: "PATCH", headers: { "X-CSRF-Token": csrf.csrf_token }, body: JSON.stringify(body) });
  },
};
