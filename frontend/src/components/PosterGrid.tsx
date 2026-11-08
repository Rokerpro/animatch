import type { ReactNode } from "react";
import { useMemo } from "react";
import { useAuth } from "../auth/useAuth";
import { useListStatuses } from "../api/hooks";
import { ListStatusContext } from "./listStatus";
export function PosterGrid({ children, label = "Anime results", animeIds = [] }: { children: ReactNode; label?: string; animeIds: number[] }) {
  const { user, mature } = useAuth();
  const ids = useMemo(() => [...new Set(animeIds)], [animeIds]);
  const statuses = useListStatuses(ids, mature, Boolean(user));
  const entries = useMemo(() => new Map((statuses.data?.items ?? []).map((item) => [item.animeId, { status: item.status, rating: item.rating }])), [statuses.data]);
  return <ListStatusContext.Provider value={{ entries, loading: Boolean(user) && statuses.isLoading }}><div className="poster-grid" aria-label={label}>{children}</div></ListStatusContext.Provider>;
}
