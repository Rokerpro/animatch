// Response and request shapes mirror docs/openapi.json.
export interface AnimeCardData {
  id: number; title: string; titleRomaji?: string | null; titleEnglish?: string | null;
  titleNative?: string | null; coverImage?: string | null; bannerImage?: string | null;
  format?: string | null; status?: string | null; episodes?: number | null; duration?: number | null;
  year?: number | null; score?: number | null; popularity?: number; isAdult?: boolean; genres?: string[];
}
export interface AnimeDetailData extends AnimeCardData {
  synopsis?: string | null; season?: string | null; seasonYear?: number | null; studio?: string | null;
  source?: string | null; idMal?: number | null; synonyms?: string[]; tags?: string[]; tagDetails?: TagDetail[];
}
export interface TagDetail { name: string; rank?: number; isSpoiler?: boolean }
export interface PageInfo { total: number; currentPage: number; lastPage: number; perPage: number; hasNextPage: boolean }
export interface AnimeListResponse { items: AnimeCardData[]; pageInfo: PageInfo }
export interface Explanation { sharedGenres?: string[]; sharedTags?: string[]; seedTitles?: string[]; quizAnswers?: string[] }
export interface Recommendation extends AnimeCardData {
  reason?: string; similarity?: number; rawCosine?: number | null; rankSim?: number | null;
  rankTaste?: number | null; qualityScore?: number | null; finalScore?: number | null;
  preMmrRank?: number | null; explanation?: Explanation;
}
export interface QuizAnswerOption { id: string; label: string }
export interface QuizQuestion { id: string; label: string; type?: string; answers: QuizAnswerOption[] }
export interface QuizResponse { results: Recommendation[]; quizVecStored: boolean }
export interface FiltersResponse { genres: string[]; tags: string[] }
export interface UserResponse {
  id: number; email: string; display_name: string; show_mature: boolean;
  taste_profile?: Record<string, unknown> | null; created_at: string;
}
export interface AuthProvidersResponse { google: boolean }
export interface CsrfTokenResponse { csrf_token: string }
export interface LoginRequest { email: string; password: string }
export interface RegisterRequest extends LoginRequest { display_name?: string | null }
export interface UserUpdateRequest { display_name?: string | null; show_mature?: boolean | null }
export interface TasteProfile { quiz_answers: Record<string, string> | null; liked_ids: number[] }
export interface AnimeListParams {
  q?: string; genres?: string[]; excludeGenres?: string[]; tags?: string[]; format?: string;
  yearMin?: number; yearMax?: number; minScore?: number; maxEpisodes?: number; status?: string;
  sort?: string; page?: number; pageSize?: number; includeMature: boolean;
}
export type ListStatus = "planning" | "watching" | "completed" | "dropped" | "on_hold";
export type ListSort = "updated" | "rating" | "title";
export interface ListEntryPut { status?: ListStatus; rating?: number | null }
export interface ListEntryResponse {
  id: number; anime_id: number; anime: AnimeCardData; status: ListStatus; rating: number | null;
  source: "manual" | "mal_import"; added_at: string; updated_at: string;
}
export interface ListPageInfo { total: number; current_page: number; last_page: number; per_page: number; has_next_page: boolean }
export interface ListResponse { items: ListEntryResponse[]; page_info: ListPageInfo }
export interface ListAnimeStatus { animeId: number; status: ListStatus; rating: number | null }
export interface ListStatusesResponse { items: ListAnimeStatus[] }
export interface ListParams { status?: ListStatus; sort: ListSort; page: number; pageSize: number; includeMature: boolean }
export interface MALUnmatchedEntry { title: string; }
export interface MALImportResponse { total_entries: number; to_import: number; skipped_existing: number; unmatched_count: number; unmatched: MALUnmatchedEntry[] }
