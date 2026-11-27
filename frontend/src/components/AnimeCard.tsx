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
  const match =
    anime.similarity == null ? null : Math.round(anime.similarity * 100);
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
        {match !== null && (
          <>
            <div className="card-match-row">
              <span aria-label={`Similarity: ${match}%`}>{match}% match</span>
              <ScoreBadge score={anime.score ?? null} />
            </div>
            <span aria-hidden="true" className="card-match-track">
              <span
                style={{ width: `${Math.min(100, Math.max(0, match))}%` }}
              />
            </span>
          </>
        )}
        <div className="card-title-row">
          <Link to={`/anime/${anime.id}`}>
            <h2>{anime.title}</h2>
          </Link>
          {match === null && <ScoreBadge score={anime.score ?? null} />}
        </div>
        {metadata && <p className="anime-meta">{metadata}</p>}
      </div>
    </article>
  );
}
