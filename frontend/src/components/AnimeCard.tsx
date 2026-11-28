import { Link } from "react-router-dom";
import type { AnimeCardData, Recommendation } from "../api/types";
import { PosterImage } from "./PosterImage";
import { ScoreBadge } from "./ScoreBadge";
import { useAnimeDetail } from "../api/hooks";
import { useAuth } from "../auth/useAuth";
import { ListControl } from "./ListControls";
import { useCardListStatus } from "./listStatus";
import { cardMeta } from "./formatMeta";
export function AnimeCard({
  anime,
}: {
  anime: AnimeCardData & Pick<Recommendation, "similarity">;
}) {
  const { mature } = useAuth();
  const listEntry = useCardListStatus(anime.id);
  // Recommendation vectors can lag behind catalog metadata. Recover a missing
  // poster from the canonical anime detail response, which is query-cached.
  const detail = useAnimeDetail(anime.id, mature, !anime.coverImage);
  const coverImage = anime.coverImage || detail.data?.coverImage;
  const metadata = cardMeta(anime);
  return (
    <article className="anime-card">
      <div className="anime-poster">
        <Link to={`/anime/${anime.id}`} aria-label={anime.title}>
          <PosterImage
            src={coverImage}
            alt={anime.title}
            color={anime.coverColor ?? detail.data?.coverColor}
          />
        </Link>
        <div className="poster-badges">
          {anime.similarity !== undefined && anime.similarity !== null && (
            <span
              aria-label={`Similarity: ${Math.round(anime.similarity * 100)}%`}
              className="similarity-badge"
            >
              {Math.round(anime.similarity * 100)}% match
            </span>
          )}
          <ScoreBadge score={anime.score ?? null} />
        </div>
        <div className="anime-save-control">
          <ListControl
            anime={anime}
            status={listEntry.status}
            rating={listEntry.rating}
            statusLoading={listEntry.loading}
          />
        </div>
      </div>
      <div className="anime-card-copy">
        <Link to={`/anime/${anime.id}`}>
          <h2>{anime.title}</h2>
        </Link>
        {metadata && <p className="anime-meta">{metadata}</p>}
      </div>
    </article>
  );
}
