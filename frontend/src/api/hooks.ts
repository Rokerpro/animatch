import { useQuery } from "@tanstack/react-query";
import { api } from "./client";
import type { AnimeListParams, ListParams, ListStatusesResponse } from "./types";
export const queryKeys = {
  anime: (params: AnimeListParams) => ["anime", params] as const,
  filters: (mature: boolean) => ["filters", mature] as const,
  detail: (id: number, mature: boolean) => ["detail", id, mature] as const,
  similar: (id: number, mature: boolean) => ["similar", id, mature] as const,
  me: ["me"] as const,
  providers: ["providers"] as const,
  list: (params: ListParams) => ["list", params] as const,
  listStatuses: (mature: boolean, ids: number[]) => ["list-statuses", mature, [...ids].sort((a, b) => a - b)] as const,
};
export const useAnime = (params: AnimeListParams) => useQuery({ queryKey: queryKeys.anime(params), queryFn: () => api.anime(params) });
export const useFilters = (mature: boolean) => useQuery({ queryKey: queryKeys.filters(mature), queryFn: () => api.filters(mature) });
export const useAnimeDetail = (id: number, mature: boolean, enabled = true) => useQuery({ queryKey: queryKeys.detail(id, mature), queryFn: () => api.detail(id, mature), enabled });
export const useSimilar = (id: number, mature: boolean) => useQuery({ queryKey: queryKeys.similar(id, mature), queryFn: () => api.similar(id, mature) });
export const useMe = () => useQuery({ queryKey: queryKeys.me, queryFn: () => api.me(), retry: false });
export const useProviders = () => useQuery({ queryKey: queryKeys.providers, queryFn: () => api.providers() });
export const useList = (params: ListParams, enabled = true) => useQuery({ queryKey: queryKeys.list(params), queryFn: () => api.list(params), retry: false, enabled, placeholderData: (previous) => previous });
export const useListStatuses = (ids: number[], mature: boolean, enabled = true) => useQuery<ListStatusesResponse>({
  queryKey: queryKeys.listStatuses(mature, ids),
  queryFn: () => api.listStatuses(ids, mature),
  enabled: enabled && ids.length > 0 && ids.length <= 50,
  retry: false,
});
