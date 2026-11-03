import { useState } from "react";
import { useLocation, useParams } from "react-router-dom";
import { ApiError } from "../api/client";
import { useAnimeDetail, useSimilar } from "../api/hooks";
import { useAuth } from "../auth/useAuth";
import { PosterGrid } from "../components/PosterGrid";
import { PosterImage } from "../components/PosterImage";
import { RecommendationCard } from "../components/RecommendationCard";
import { ErrorState, PosterSkeleton } from "../components/RequestStates";
import { ScoreBadge } from "../components/ScoreBadge";
import { AuthPrompt } from "../components/AuthPrompt";
export function AnimeDetailPage() {
  const id = Number(useParams().id); const { mature, user } = useAuth(); const detail = useAnimeDetail(id, mature); const similar = useSimilar(id, mature);
  const location = useLocation(); const [authPromptOpen, setAuthPromptOpen] = useState(false); const [rating, setRating] = useState("");
  if (detail.isLoading) return <main className="detail-page"><PosterSkeleton count={3} /></main>;
  if (detail.error instanceof ApiError && detail.error.status === 404) return <main className="detail-page"><p role="status">Not found, or hidden by your content settings</p></main>;
  if (detail.isError || !detail.data) return <main className="detail-page"><ErrorState message="Could not load this anime." /></main>;
  const anime = detail.data; const tags = [...(anime.tagDetails ?? [])].filter((tag) => !tag.isSpoiler).sort((a, b) => (b.rank ?? 0) - (a.rank ?? 0));
  return <article className="detail-page">
    <div className="detail-banner" style={anime.bannerImage ? { backgroundImage: `url(${JSON.stringify(anime.bannerImage)})` } : undefined} aria-hidden="true" />
    <div className="detail-intro"><div className="detail-cover"><PosterImage src={anime.coverImage} alt={anime.title} /></div><div className="detail-heading"><p className="eyebrow">{[anime.format, anime.status].filter(Boolean).join(" · ")}</p><h1>{anime.title}</h1>{anime.titleEnglish && anime.titleEnglish !== anime.title && <p>{anime.titleEnglish}</p>}<ScoreBadge score={anime.score ?? null} /><p className="anime-meta">{[anime.year, anime.episodes ? `${anime.episodes} episodes` : null].filter(Boolean).join(" · ")}</p></div></div>
    <div className="detail-content"><section><h2>Synopsis</h2><p>{anime.synopsis || "No synopsis available."}</p></section>
      <section><h2>Details</h2><dl className="detail-list">{[["Popularity", `${(anime.popularity ?? 0).toLocaleString()} users`], ["Studio", anime.studio], ["Season", [anime.season, anime.seasonYear].filter(Boolean).join(" ")], ["Source", anime.source], ["Episodes", anime.episodes], ["Duration", anime.duration ? `${anime.duration} min` : null]].filter(([, value]) => value != null).map(([key, value]) => <div key={String(key)}><dt>{key}</dt><dd>{value}</dd></div>)}</dl></section>
      {!!anime.genres?.length && <section><h2>Genres</h2><div className="tag-list">{anime.genres.map((genre) => <span className="tag-pill" key={genre}>{genre}</span>)}</div></section>}
      {!!tags.length && <TagList tags={tags.map((tag) => tag.name)} />}
      <section aria-label="List actions" className="reserved-actions">
        <button disabled={Boolean(user)} onClick={() => setAuthPromptOpen(true)} type="button">Add to list</button>
        <label>Your rating <span className="rating-control"><select aria-label="Your rating out of 10" onChange={(event) => {
          if (!user) { setAuthPromptOpen(true); return; }
          setRating(event.target.value);
        }} value={rating}><option value="">_</option>{Array.from({ length: 10 }, (_, i) => <option value={i + 1} key={i}>{i + 1}</option>)}</select><span aria-hidden="true">/10</span></span></label>
      </section>
      {authPromptOpen && <AuthPrompt nextPath={`${location.pathname}${location.search}`} onClose={() => setAuthPromptOpen(false)} />}
      <section><h2>Similar anime</h2>{similar.isLoading ? <PosterSkeleton count={4} /> : similar.isError ? <ErrorState message="Could not load recommendations." /> : !similar.data?.length ? <p>No similar anime found.</p> : <PosterGrid label="Similar anime">{similar.data.map((rec) => <RecommendationCard key={rec.id} recommendation={rec} />)}</PosterGrid>}</section>
    </div>
  </article>;
}
function TagList({ tags }: { tags: string[] }) {
  const [showAll, setShowAll] = useState(false); const shown = showAll ? tags : tags.slice(0, 8);
  return <section><h2>Tags</h2><div className="tag-list">{shown.map((tag) => <span className="tag-pill" key={tag}>{tag}</span>)}</div>{tags.length > 8 && <button className="tag-toggle" onClick={() => setShowAll(!showAll)}>{showAll ? "Show fewer" : "Show more"}</button>}</section>;
}
