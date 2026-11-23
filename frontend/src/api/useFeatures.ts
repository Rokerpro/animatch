import { useQuery } from "@tanstack/react-query";
import { api } from "./client";

export const featuresQueryKey = ["features"] as const;

export function useFeatures() {
  return useQuery({
    queryKey: featuresQueryKey,
    queryFn: ({ signal }) => api.features(signal),
    retry: false,
    staleTime: Infinity,
  });
}
