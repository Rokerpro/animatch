import { useSearchParams } from "react-router-dom";
import { useAnime, useFilters } from "../api/hooks";
import { AnimeCard } from "../components/AnimeCard";
import { FilterBar } from "../components/FilterBar";
import { Pagination } from "../components/Pagination";
import { PosterGrid } from "../components/PosterGrid";
import { EmptyState, ErrorState, PosterSkeleton } from "../components/RequestStates";
import { useAuth } from "../auth/useAuth";
export function BrowsePage() {
  const [params] = useSearchParams(); const { mature } = useAuth(); const page = Math.max(1, Number(params.get("page") ?? 1) || 1);
  const query = { q: params.get("q") ?? undefined, genres: params.getAll("genres"), tags: params.getAll("tags"), format: params.get("format") ?? undefined, yearMin: Number(params.get("yearMin")) || undefined, yearMax: Number(params.get("yearMax")) || undefined, minScore: Number(params.get("minScore")) || undefined, maxEpisodes: Number(params.get("maxEpisodes")) || undefined, status: params.get("status") ?? undefined, sort: params.get("sort") ?? "popularity", page, pageSize: 24, includeMature: mature };
  const results = useAnime(query); const filters = useFilters(mature);
  return <section className="browse-page"><h1 className="page-title">{query.q ? `Results for “${query.q}”` : "Browse anime"}</h1><FilterBar options={filters.data} />
    {results.isLoading ? <PosterSkeleton /> : results.isError ? <ErrorState message="Could not load anime. Please try again." /> : !results.data?.items.length ? <EmptyState title="No anime match these filters." /> : <>
      <p className="result-count">{results.data.pageInfo.total.toLocaleString()} anime</p><PosterGrid>{results.data.items.map((anime) => <AnimeCard anime={anime} key={anime.id} />)}</PosterGrid><Pagination page={page} lastPage={results.data.pageInfo.lastPage} />
    </>}
  </section>;
}
