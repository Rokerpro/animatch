import { useEffect, useState } from "react";
import type { FiltersResponse } from "../api/types";
import { MultiSelectFilter } from "./MultiSelectFilter";
import { useFilterParams } from "../hooks/useFilterParams";
import { SearchInput } from "./SearchInput";
import { ListFilter, SlidersHorizontal, X } from "lucide-react";
import { formatLabel } from "./formatMeta";

const FORMATS = ["TV", "MOVIE", "OVA", "ONA", "SPECIAL", "MUSIC"];
const STATUSES: [string, string][] = [
  ["FINISHED", "Finished"],
  ["RELEASING", "Airing"],
  ["NOT_YET_RELEASED", "Not yet aired"],
  ["CANCELLED", "Cancelled"],
  ["HIATUS", "Hiatus"],
];

export function FilterBar({ options }: { options?: FiltersResponse }) {
  const [more, setMore] = useState(false);
  const [drawer, setDrawer] = useState(false);
  const [entering, setEntering] = useState(false);
  const { state, setFilter, clearFilters } = useFilterParams();
  const activeMoreFilterCount =
    state.genres.length +
    state.tags.length +
    Number(Boolean(state.yearMin || state.yearMax)) +
    Number(Boolean(state.maxEpisodes)) +
    Number(Boolean(state.status));

  useEffect(() => {
    if (!drawer) return;
    setEntering(true);
    const timer = setTimeout(() => setEntering(false), 50);
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setDrawer(false);
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => {
      clearTimeout(timer);
      window.removeEventListener("keydown", closeOnEscape);
    };
  }, [drawer]);

  const chips: {
    key: keyof typeof state;
    value: string;
    removeValue?: string;
  }[] = [
    ...state.genres.map((value) => ({
      key: "genres" as const,
      value,
      removeValue: value,
    })),
    ...(state.format
      ? [
          {
            key: "format" as const,
            value: formatLabel(state.format) ?? state.format,
          },
        ]
      : []),
    ...(state.yearMin || state.yearMax
      ? [
          {
            key: "yearMin" as const,
            value: `${state.yearMin || "Any"}–${state.yearMax || "Any"}`,
          },
        ]
      : []),
    ...state.tags.map((value) => ({
      key: "tags" as const,
      value,
      removeValue: value,
    })),
    ...(state.minScore
      ? [{ key: "minScore" as const, value: `Score ${state.minScore}+` }]
      : []),
    ...(state.maxEpisodes
      ? [
          {
            key: "maxEpisodes" as const,
            value: `Up to ${state.maxEpisodes} eps`,
          },
        ]
      : []),
    ...(state.status
      ? [
          {
            key: "status" as const,
            value:
              STATUSES.find(([value]) => value === state.status)?.[1] ??
              state.status,
          },
        ]
      : []),
  ];

  const controls = (
    <>
      <div className="filter-primary-controls">
        <div className="filter-field filter-search">
          <span className="sr-only">Search</span>
          <SearchInput />
        </div>
        <label className="filter-field">
          <span className="filter-label">Format</span>
          <select
            aria-label="Format"
            value={state.format}
            onChange={(e) => setFilter("format", e.target.value)}
          >
            <option value="">Any format</option>
            {FORMATS.map((v) => (
              <option key={v} value={v}>
                {formatLabel(v)}
              </option>
            ))}
          </select>
        </label>
        <label className="filter-field">
          <span className="filter-label">Min score</span>
          <input
            aria-label="Minimum score"
            type="number"
            min="0"
            max="100"
            value={state.minScore}
            onChange={(e) => setFilter("minScore", e.target.value)}
            placeholder="Any"
          />
        </label>
        <label className="filter-field">
          <span className="filter-label">Sort</span>
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
          aria-controls="more-filter-options"
          aria-expanded={more}
          onClick={() => setMore(!more)}
          type="button"
        >
          <ListFilter aria-hidden="true" size={18} strokeWidth={1.5} />
          More filters
          {activeMoreFilterCount > 0 && (
            <span className="filter-count"> {activeMoreFilterCount}</span>
          )}
        </button>
      </div>
      {more && (
        <div className="more-filters panel" id="more-filter-options">
          <MultiSelectFilter
            label="Genre"
            options={options?.genres ?? []}
            selected={state.genres}
            onChange={(values) => setFilter("genres", values)}
          />
          <MultiSelectFilter
            label="Tags"
            options={options?.tags ?? []}
            selected={state.tags}
            onChange={(values) => setFilter("tags", values)}
          />
          <label className="filter-field">
            <span className="filter-label">Year from</span>
            <input
              aria-label="Year from"
              type="number"
              value={state.yearMin}
              onChange={(e) => setFilter("yearMin", e.target.value)}
              placeholder="Any"
            />
          </label>
          <label className="filter-field">
            <span className="filter-label">Year to</span>
            <input
              aria-label="Year to"
              type="number"
              value={state.yearMax}
              onChange={(e) => setFilter("yearMax", e.target.value)}
              placeholder="Any"
            />
          </label>
          <label className="filter-field">
            <span className="filter-label">Maximum episodes</span>
            <input
              aria-label="Maximum episodes"
              type="number"
              min="1"
              value={state.maxEpisodes}
              onChange={(e) => setFilter("maxEpisodes", e.target.value)}
            />
          </label>
          <label className="filter-field">
            <span className="filter-label">Status</span>
            <select
              aria-label="Status"
              value={state.status}
              onChange={(e) => setFilter("status", e.target.value)}
            >
              <option value="">Any</option>
              {STATUSES.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
        </div>
      )}
    </>
  );

  return (
    <section aria-label="Anime filters" className="filter-section">
      <button
        className="secondary-action mobile-filter-toggle"
        onClick={() => setDrawer(true)}
        type="button"
      >
        <SlidersHorizontal aria-hidden="true" size={18} />
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
              {value} <X aria-hidden="true" size={18} strokeWidth={1.8} />
              <span className="sr-only">Remove {value} filter</span>
            </button>
          ))}
          <button
            className="clear-filters"
            onClick={clearFilters}
            type="button"
          >
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
            <div className="filter-drawer-header">
              <h2>Filters</h2>
              <button
                aria-label="Close filters"
                className="icon-button"
                onClick={() => setDrawer(false)}
                type="button"
              >
                <X aria-hidden="true" size={18} />
              </button>
            </div>
            <div className="filter-controls">{controls}</div>
          </section>
        </div>
      )}
    </section>
  );
}
