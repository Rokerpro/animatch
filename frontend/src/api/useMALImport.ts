import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "./client";
import type { MALImportResponse } from "./types";

export function useMALImport() {
  const queryClient = useQueryClient();
  return useMutation<MALImportResponse, Error, { file: File; dryRun: boolean }>({
    mutationFn: ({ file, dryRun }) => api.importMALList(file, dryRun),
    onSuccess: (_result, variables) => variables.dryRun ? undefined : Promise.all([
      queryClient.invalidateQueries({ queryKey: ["list-statuses"] }),
      queryClient.invalidateQueries({ queryKey: ["list"] }),
      queryClient.invalidateQueries({ queryKey: ["my-recommendations"] }),
    ]),
  });
}
