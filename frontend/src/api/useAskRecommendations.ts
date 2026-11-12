import { useEffect, useRef } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "./client";
import type { NaturalLanguageRequest } from "./types";

export function useAskRecommendations() {
  const queryClient = useQueryClient();
  const controllerRef = useRef<AbortController | null>(null);
  const mutation = useMutation({
    mutationFn: (body: NaturalLanguageRequest) => {
      const controller = new AbortController();
      controllerRef.current = controller;
      return api.askRecommendations(body, controller.signal).finally(() => {
        if (controllerRef.current === controller) controllerRef.current = null;
      });
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["my-recommendations"] }),
  });
  useEffect(() => () => controllerRef.current?.abort(), []);
  return { ...mutation, abort: () => controllerRef.current?.abort() };
}
