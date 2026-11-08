import { createContext, useContext } from "react";
import type { ListStatus } from "../api/types";

export const listStatusLabels: Record<ListStatus, string> = {
  planning: "Planning", watching: "Watching", completed: "Completed", dropped: "Dropped", on_hold: "On hold",
};
export const listStatuses = Object.keys(listStatusLabels) as ListStatus[];
export const ListStatusContext = createContext<{ entries: Map<number, { status: ListStatus; rating: number | null }>; loading: boolean }>({ entries: new Map(), loading: false });

export function useCardListStatus(animeId: number) {
  const context = useContext(ListStatusContext);
  return { ...(context.entries.get(animeId) ?? { status: null, rating: null }), loading: context.loading };
}
