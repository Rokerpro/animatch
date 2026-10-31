import { useEffect, useState } from "react";
import type { FiltersResponse } from "../api/types";
import { MultiSelectFilter } from "./MultiSelectFilter";
import { useFilterParams } from "../hooks/useFilterParams";

export function FilterBar({ options }: { options?: FiltersResponse }) {
  const [more, setMore] = useState(false);
  const [drawer, setDrawer] = useState(false);
  const [entering, setEntering] = useState(false);
  const { state, setFilter, clearFilters } = useFilterParams();

  useEffect(() => {
    if (!drawer) return;
    setEntering(true);
    const timer = setTimeout(() => setEntering(false), 50);
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setDrawer(false);
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => { clearTimeout(timer); window.removeEventListener("keydown", closeOnEscape); };
  }, [drawer]);

  const chips: { key: keyof typeof state; value: string; removeValue?: string }[] = [
    ...state.genres.map((value) => ({ key: "genres" as const, value, removeValue: value })),
    ...(state.format ? [{ key: "format" as const, value: state.format }] : []),
    ...(state.yearMin || state.yearMax ? [{ key: "yearMin" as const, value: `${state.yearMin || "Any"}–${state.yearMax || "Any"}` }] : []),
    ...state.tags.map((value) => ({ key: "tags" as const, value, removeValue: value })),
    ...(state.minScore ? [{ key: "minScore" as const, value: `Score ≥ ${state.minScore}` }] : []),
    ...(state.maxEpisodes ? [{ key: "maxEpisodes" as const, value: `≤ ${state.maxEpisodes} eps` }] : []),
    ...(state.status ? [{ key: "status" as const, value: state.status }] : []),
  ];

  const controls = (
    <>
      <MultiSelectFilter
        label="Genre"
        options={options?.genres ?? []}
        selected={state.genres}
        onChange={(values) => setFilter("genres", values)}
      />
      <label>
        Format
        <select
          aria-label="Format"
          value={state.format}
          onChange={(e) => setFilter("format", e.target.value)}
        >
          <option value="">Any</option>
          {["TV", "MOVIE", "OVA", "ONA", "SPECIAL", "MUSIC"].map((v) => (
            <option key={v}>{v}</option>
          ))}
        </select>
      </label>
      <label>
        Year from
        <input
          aria-label="Year from"
          type="number"
          value={state.yearMin}
          onChange={(e) => setFilter("yearMin", e.target.value)}
          placeholder="Any"
        />
      </label>
      <label>
        Year to
        <input
          aria-label="Year to"
          type="number"
          value={state.yearMax}
          onChange={(e) => setFilter("yearMax", e.target.value)}
          placeholder="Any"
        />
      </label>
      <label>
        Sort
        <select
          aria-label="Sort"
          value={state.sort}
          onChange={(e) => setFilter("sort", e.target.value)}
        >
          <option value="popularity">Popularity</option>
          <option value="score">Score</option>
          <option value="year">Year</option>
          <option value="title">Title</option>
        </select>
      </label>
      <button
        className="more-filters-toggle"
        aria-expanded={more}
        onClick={() => setMore(!more)}
        type="button"
      >
        More filters
      </button>
      {more && (
        <div className="more-filters">
          <MultiSelectFilter
            label="Tags"
            options={options?.tags ?? []}
            selected={state.tags}
            onChange={(values) => setFilter("tags", values)}
          />
          <label>
            Minimum score
            <input
              aria-label="Minimum score"
              type="number"
              min="0"
              max="100"
              value={state.minScore}
              onChange={(e) => setFilter("minScore", e.target.value)}
            />
          </label>
          <label>
            Maximum episodes
            <input
              aria-label="Maximum episodes"
              type="number"
              min="1"
              value={state.maxEpisodes}
              onChange={(e) => setFilter("maxEpisodes", e.target.value)}
            />
          </label>
          <label>
            Status
            <select
              aria-label="Status"
              value={state.status}
              onChange={(e) => setFilter("status", e.target.value)}
            >
              <option value="">Any</option>
              {["FINISHED", "RELEASING", "NOT_YET_RELEASED", "CANCELLED", "HIATUS"].map(
                (v) => (
                  <option key={v}>{v}</option>
                )
              )}
            </select>
          </label>
        </div>
      )}
    </>
  );

  return (
    <section aria-label="Anime filters" className="filter-section">
      <button
        className="mobile-filter-toggle"
        onClick={() => setDrawer(true)}
        type="button"
      >
        Filters
      </button>
      <div className="filter-controls">{controls}</div>
      {!!chips.length && (
        <div className="active-filters">
          {chips.map(({ key, value, removeValue }) => (
            <button
              key={`${key}-${value}`}
              className="filter-chip"
              onClick={() => {
                if (key === "genres" || key === "tags") {
                  setFilter(
                    key,
                    state[key].filter((item) => item !== removeValue)
                  );
                } else if (key === "yearMin") {
                  setFilter("yearMin", "");
                  setFilter("yearMax", "");
                } else {
                  setFilter(key, "");
                }
              }}
              type="button"
            >
              {value} <span aria-hidden="true">×</span>
              <span className="sr-only">Remove {value} filter</span>
            </button>
          ))}
          <button onClick={clearFilters} type="button">
            Clear all
          </button>
        </div>
      )}
      {drawer && (
        <div
          className="drawer-backdrop"
          role="presentation"
          onClick={() => setDrawer(false)}
        >
          <section
            className="filter-drawer"
            role="dialog"
            aria-modal="true"
            aria-label="Filters"
            onClick={(e) => e.stopPropagation()}
            data-entering={entering ? "" : undefined}
          >
            <button onClick={() => setDrawer(false)} type="button">
              Close filters
            </button>
            <div className="filter-controls">{controls}</div>
          </section>
        </div>
      )}
    </section>
  );
}
