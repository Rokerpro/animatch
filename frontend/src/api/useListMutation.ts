import { useMutation, useQueryClient } from "@tanstack/react-query";
import type { AnimeCardData, ListEntryPut, ListEntryResponse, ListResponse, ListStatusesResponse, ListStatus } from "./types";
import { ApiError, api, getErrorMessage } from "./client";
import { useOptionalToast } from "../components/useToast";

type Change =
  | { kind: "put"; anime: AnimeCardData; body: ListEntryPut; status: ListStatus; rating: number | null }
  | { kind: "delete"; anime: AnimeCardData };

type Snapshot = {
  statuses: [readonly unknown[], ListStatusesResponse | undefined][];
  lists: [readonly unknown[], ListResponse | undefined][];
};

export function useListMutation() {
  const queryClient = useQueryClient();
  const { showToast } = useOptionalToast();
  return useMutation<ListEntryResponse | { message: string }, Error, Change, Snapshot>({
    mutationFn: (change: Change) => change.kind === "delete"
      ? api.deleteListEntry(change.anime.id)
      : api.updateListEntry(change.anime.id, change.body),
    onMutate: async (change): Promise<Snapshot> => {
      await Promise.all([
        queryClient.cancelQueries({ queryKey: ["list-statuses"] }),
        queryClient.cancelQueries({ queryKey: ["list"] }),
      ]);
      const snapshot: Snapshot = {
        statuses: queryClient.getQueriesData<ListStatusesResponse>({ queryKey: ["list-statuses"] }),
        lists: queryClient.getQueriesData<ListResponse>({ queryKey: ["list"] }),
      };
      queryClient.setQueriesData<ListStatusesResponse>({ queryKey: ["list-statuses"] }, (old) => {
        if (!old) return old;
        const items = old.items.filter((item) => item.animeId !== change.anime.id);
        if (change.kind === "put") items.push({ animeId: change.anime.id, status: change.status, rating: change.rating });
        return { ...old, items };
      });
      queryClient.setQueriesData<ListResponse>({ queryKey: ["list"] }, (old) => {
        if (!old) return old;
        const exists = old.items.some((entry) => entry.anime_id === change.anime.id);
        if (change.kind === "put" && exists) {
          return { ...old, items: old.items.map((entry) => entry.anime_id === change.anime.id
            ? { ...entry, status: change.status, rating: change.rating }
            : entry) };
        }
        if (change.kind === "delete" && exists) {
          const items = old.items.filter((entry) => entry.anime_id !== change.anime.id);
          const total = Math.max(0, old.page_info.total - 1);
          const lastPage = Math.max(1, Math.ceil(total / old.page_info.per_page));
          return { ...old, items, page_info: { ...old.page_info, total, last_page: lastPage, has_next_page: old.page_info.current_page < lastPage } };
        }
        return old;
      });
      return snapshot;
    },
    onError: (error, change, snapshot) => {
      snapshot?.statuses.forEach(([key, value]) => queryClient.setQueryData(key, value));
      snapshot?.lists.forEach(([key, value]) => queryClient.setQueryData(key, value));
      const message = change.kind === "put" && error instanceof ApiError && error.status === 404
        ? "This title is hidden by your content settings"
        : getErrorMessage(error, "Could not update your list.");
      showToast(message, "error");
    },
    onSuccess: (_result, change) => {
      if (change.kind === "delete") showToast("Removed from My list", "success");
      else showToast("My list updated", "success");
    },
    onSettled: () => Promise.all([
      queryClient.invalidateQueries({ queryKey: ["list-statuses"] }),
      queryClient.invalidateQueries({ queryKey: ["list"] }),
      queryClient.invalidateQueries({ queryKey: ["my-recommendations"] }),
    ]),
  });
}

export type { Change as ListChange };
