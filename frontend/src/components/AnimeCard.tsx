import { Link } from "react-router-dom";
import type { AnimeCardData, Recommendation } from "../api/types";
import { PosterImage } from "./PosterImage";
import { ScoreBadge } from "./ScoreBadge";
export function AnimeCard({ anime }: { anime: AnimeCardData & Pick<Recommendation, "similarity"> }) {
  const metadata = [anime.format, anime.year, anime.episodes ? `${anime.episodes} eps` : null].filter(Boolean).join(" · ");
  return <article className="anime-card">
    <div className="anime-poster">
      <Link to={`/anime/${anime.id}`} aria-label={anime.title}>
        <PosterImage src={anime.coverImage} alt={anime.title} />
      </Link>
      <div className="poster-badges">
        {anime.similarity !== undefined && anime.similarity !== null && (
          <span aria-label={`Similarity: ${Math.round(anime.similarity * 100)}%`} className="similarity-badge">
            {Math.round(anime.similarity * 100)}% match
          </span>
        )}
        <ScoreBadge score={anime.score ?? null} />
      </div>
    </div>
    <div className="anime-card-copy"><div className="anime-card-top"><Link to={`/anime/${anime.id}`}><h2>{anime.title}</h2></Link></div>
    {metadata && <p className="anime-meta">{metadata}</p>}</div>
  </article>;
}
