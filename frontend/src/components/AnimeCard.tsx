import { Link } from "react-router-dom";
import type { AnimeCardData } from "../api/types";
import { PosterImage } from "./PosterImage";
import { ScoreBadge } from "./ScoreBadge";
export function AnimeCard({ anime }: { anime: AnimeCardData }) {
  const metadata = [anime.format, anime.year, anime.episodes ? `${anime.episodes} eps` : null].filter(Boolean).join(" · ");
  return <article className="anime-card"><Link to={`/anime/${anime.id}`} aria-label={anime.title}>
    <div className="anime-poster"><PosterImage src={anime.coverImage} alt={anime.title} /><ScoreBadge score={anime.score ?? null} /></div>
    <div className="anime-card-copy"><div className="anime-card-top"><h2>{anime.title}</h2></div>
    {metadata && <p className="anime-meta">{metadata}</p>}</div>
  </Link></article>;
}
