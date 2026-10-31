import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";

type FilterState = {
  genres: string[];
  format: string;
  yearMin: string;
  yearMax: string;
  sort: string;
  tags: string[];
  minScore: string;
  maxEpisodes: string;
  status: string;
};

export function useFilterParams() {
  const [params, setParams] = useSearchParams();

  const state: FilterState = useMemo(
    () => ({
      genres: params.getAll("genres"),
      format: params.get("format") ?? "",
      yearMin: params.get("yearMin") ?? "",
      yearMax: params.get("yearMax") ?? "",
      sort: params.get("sort") ?? "popularity",
      tags: params.getAll("tags"),
      minScore: params.get("minScore") ?? "",
      maxEpisodes: params.get("maxEpisodes") ?? "",
      status: params.get("status") ?? "",
    }),
    [params]
  );

  const setFilter = useCallback(
    (key: keyof FilterState, value: string | string[]) => {
      const next = new URLSearchParams(params);
      const paramMap: Partial<Record<keyof FilterState, string>> = {
        format: "format",
        yearMin: "yearMin",
        yearMax: "yearMax",
        sort: "sort",
        minScore: "minScore",
        maxEpisodes: "maxEpisodes",
        status: "status",
      };
      const paramName = paramMap[key];

      if (key === "genres" || key === "tags") {
        next.delete(key);
        (value as string[]).forEach((item) => next.append(key, item));
      } else if (paramName) {
        const scalar = value as string;
        if (scalar && !(key === "sort" && scalar === "popularity")) {
          next.set(paramName, scalar);
        } else {
          next.delete(paramName);
        }
      }
      next.delete("page");
      setParams(next);
    },
    [params, setParams]
  );

  const clearFilters = useCallback(() => {
    const next = new URLSearchParams();
    const q = params.get("q");
    if (q) next.set("q", q);
    setParams(next);
  }, [params, setParams]);

  return { state, setFilter, clearFilters };
}
