import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import type { FiltersResponse } from "../api/types";
import { MultiSelectFilter } from "./MultiSelectFilter";
type FilterState = { genres: string[]; format: string; yearMin: string; yearMax: string; sort: string; tags: string[]; minScore: string; maxEpisodes: string; status: string };
const defaults: FilterState = { genres: [], format: "", yearMin: "", yearMax: "", sort: "popularity", tags: [], minScore: "", maxEpisodes: "", status: "" };
export function FilterBar({ options }: { options?: FiltersResponse }) {
  const [params, setParams] = useSearchParams(); const [more, setMore] = useState(false); const [drawer, setDrawer] = useState(false);
  useEffect(() => {
    if (!drawer) return;
    const closeOnEscape = (event: KeyboardEvent) => { if (event.key === "Escape") setDrawer(false); };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [drawer]);
  const state: FilterState = { ...defaults, genres: params.getAll("genres"), format: params.get("format") ?? "", yearMin: params.get("yearMin") ?? "", yearMax: params.get("yearMax") ?? "", sort: params.get("sort") ?? "popularity", tags: params.getAll("tags"), minScore: params.get("minScore") ?? "", maxEpisodes: params.get("maxEpisodes") ?? "", status: params.get("status") ?? "" };
  const set = (key: keyof FilterState, value: string | string[]) => { const next = new URLSearchParams(params); const name: Partial<Record<keyof FilterState, string>> = { format: "format", yearMin: "yearMin", yearMax: "yearMax", sort: "sort", minScore: "minScore", maxEpisodes: "maxEpisodes", status: "status" }; const param = name[key];
    if (key === "genres" || key === "tags") { next.delete(key); (value as string[]).forEach((item) => next.append(key, item)); }
    else if (param) { const scalar = value as string; if (scalar && !(key === "sort" && scalar === "popularity")) next.set(param, scalar); else next.delete(param); }
    next.delete("page"); setParams(next); };
  const clear = () => { const next = new URLSearchParams(); const q = params.get("q"); if (q) next.set("q", q); setParams(next); };
  const chips: { key: keyof FilterState; value: string; removeValue?: string }[] = [
    ...state.genres.map((value) => ({ key: "genres" as const, value, removeValue: value })),
    ...(state.format ? [{ key: "format" as const, value: state.format }] : []),
    ...(state.yearMin || state.yearMax ? [{ key: "yearMin" as const, value: `${state.yearMin || "Any"}–${state.yearMax || "Any"}` }] : []),
    ...state.tags.map((value) => ({ key: "tags" as const, value, removeValue: value })),
    ...(state.minScore ? [{ key: "minScore" as const, value: `Score ≥ ${state.minScore}` }] : []),
    ...(state.maxEpisodes ? [{ key: "maxEpisodes" as const, value: `≤ ${state.maxEpisodes} eps` }] : []),
    ...(state.status ? [{ key: "status" as const, value: state.status }] : []),
  ];
  const controls = <>
    <MultiSelectFilter label="Genre" options={options?.genres ?? []} selected={state.genres} onChange={(values) => set("genres", values)} />
    <label>Format<select aria-label="Format" value={state.format} onChange={(e) => set("format", e.target.value)}><option value="">Any</option>{["TV", "MOVIE", "OVA", "ONA", "SPECIAL", "MUSIC"].map((v) => <option key={v}>{v}</option>)}</select></label>
    <label>Year from<input aria-label="Year from" type="number" value={state.yearMin} onChange={(e) => set("yearMin", e.target.value)} placeholder="Any" /></label>
    <label>Year to<input aria-label="Year to" type="number" value={state.yearMax} onChange={(e) => set("yearMax", e.target.value)} placeholder="Any" /></label>
    <label>Sort<select aria-label="Sort" value={state.sort} onChange={(e) => set("sort", e.target.value)}><option value="popularity">Popularity</option><option value="score">Score</option><option value="year">Year</option><option value="title">Title</option></select></label>
    <button className="more-filters-toggle" aria-expanded={more} onClick={() => setMore(!more)}>More filters</button>
    {more && <div className="more-filters"><MultiSelectFilter label="Tags" options={options?.tags ?? []} selected={state.tags} onChange={(values) => set("tags", values)} /><label>Minimum score<input aria-label="Minimum score" type="number" min="0" max="100" value={state.minScore} onChange={(e) => set("minScore", e.target.value)} /></label><label>Maximum episodes<input aria-label="Maximum episodes" type="number" min="1" value={state.maxEpisodes} onChange={(e) => set("maxEpisodes", e.target.value)} /></label><label>Status<select aria-label="Status" value={state.status} onChange={(e) => set("status", e.target.value)}><option value="">Any</option>{["FINISHED", "RELEASING", "NOT_YET_RELEASED", "CANCELLED", "HIATUS"].map((v) => <option key={v}>{v}</option>)}</select></label></div>}
  </>;
  return <section aria-label="Anime filters" className="filter-section"><button className="mobile-filter-toggle" onClick={() => setDrawer(true)}>Filters</button>
    <div className="filter-controls">{controls}</div>
    {!!chips.length && <div className="active-filters">{chips.map(({ key, value, removeValue }) => <button key={`${key}-${value}`} className="filter-chip" onClick={() => {
      if (key === "genres" || key === "tags") set(key, state[key].filter((item) => item !== removeValue));
      else if (key === "yearMin") { set("yearMin", ""); set("yearMax", ""); }
      else set(key, "");
    }}>{value} <span aria-hidden="true">×</span><span className="sr-only">Remove {value} filter</span></button>)}<button onClick={clear}>Clear all</button></div>}
    {drawer && <div className="drawer-backdrop" role="presentation" onClick={() => setDrawer(false)}><section className="filter-drawer" role="dialog" aria-modal="true" aria-label="Filters" onClick={(e) => e.stopPropagation()}><button onClick={() => setDrawer(false)}>Close filters</button><div className="filter-controls">{controls}</div></section></div>}
  </section>;
}
