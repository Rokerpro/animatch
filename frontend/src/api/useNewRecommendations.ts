import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "./client";
import type { NewRecommendationsRequest } from "./types";

export function useNewRecommendationQuiz(enabled = true) {
  return useQuery({ queryKey: ["quiz"], queryFn: () => api.quiz(), retry: false, enabled });
}

export function useNewRecommendations() {
  return useMutation({ mutationFn: (body: NewRecommendationsRequest) => api.newRecommendations(body) });
}
