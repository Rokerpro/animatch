import { useQuery } from "@tanstack/react-query";
import { api } from "./client";
import type { AnimeListParams } from "./types";
export const queryKeys = {
  anime: (params: AnimeListParams) => ["anime", params] as const,
  filters: (mature: boolean) => ["filters", mature] as const,
  detail: (id: number, mature: boolean) => ["detail", id, mature] as const,
  similar: (id: number, mature: boolean) => ["similar", id, mature] as const,
  me: ["me"] as const,
  providers: ["providers"] as const,
};
export const useAnime = (params: AnimeListParams) => useQuery({ queryKey: queryKeys.anime(params), queryFn: () => api.anime(params) });
export const useFilters = (mature: boolean) => useQuery({ queryKey: queryKeys.filters(mature), queryFn: () => api.filters(mature) });
export const useAnimeDetail = (id: number, mature: boolean) => useQuery({ queryKey: queryKeys.detail(id, mature), queryFn: () => api.detail(id, mature) });
export const useSimilar = (id: number, mature: boolean) => useQuery({ queryKey: queryKeys.similar(id, mature), queryFn: () => api.similar(id, mature) });
export const useMe = () => useQuery({ queryKey: queryKeys.me, queryFn: () => api.me(), retry: false });
export const useProviders = () => useQuery({ queryKey: queryKeys.providers, queryFn: () => api.providers() });
