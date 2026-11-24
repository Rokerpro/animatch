import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { formatLabel, statusLabel } from "../components/formatMeta";
import { ApiError } from "../api/client";
import { useAnimeDetail, useListStatuses, useSimilar } from "../api/hooks";
import { useAuth } from "../auth/useAuth";
import { PosterGrid } from "../components/PosterGrid";
import { PosterImage } from "../components/PosterImage";
import { RecommendationCard } from "../components/RecommendationCard";
import { ErrorState, PosterSkeleton } from "../components/RequestStates";
import { ScoreBadge } from "../components/ScoreBadge";
import { ListControl, ListRatingControl } from "../components/ListControls";
export function AnimeDetailPage() {
  const id = Number(useParams().id);
  const { mature, user } = useAuth();
  const detail = useAnimeDetail(id, mature);
  const similar = useSimilar(id, mature);
  const listStatusQuery = useListStatuses([id], mature, Boolean(user));
  if (detail.isLoading)
    return (
      <section className="detail-page detail-state">
        <PosterSkeleton count={3} />
      </section>
    );
  if (detail.error instanceof ApiError && detail.error.status === 404)
    return (
      <section className="detail-page detail-state">
        <p role="status">Not found, or hidden by your content settings</p>
      </section>
    );
  if (detail.isError || !detail.data)
    return (
      <section className="detail-page detail-state">
        <ErrorState message="Could not load this anime." />
      </section>
    );
  const anime = detail.data;
  const tags = [...(anime.tagDetails ?? [])]
    .filter((tag) => !tag.isSpoiler)
    .sort((a, b) => (b.rank ?? 0) - (a.rank ?? 0));
  const listEntry = listStatusQuery.data?.items.find(
    (entry) => entry.animeId === anime.id
  );
  const listStatus = listEntry?.status ?? null;
  const listRating = listEntry?.rating ?? null;
  const subtitle = [anime.titleRomaji, anime.titleEnglish].find(
    (value) => value && value !== anime.title
  );
  const statusText = statusLabel(anime.status);
  const kind = [formatLabel(anime.format), statusText].filter(Boolean);
  const details: [string, string | number | null | undefined][] = [
    [
      "Popularity",
      anime.popularity ? `${anime.popularity.toLocaleString()} users` : null,
    ],
    ["Studio", anime.studio],
    [
      "Season",
      [titleCase(anime.season), anime.seasonYear].filter(Boolean).join(" "),
    ],
    ["Source", titleCase(anime.source)],
    ["Episodes", anime.episodes],
    ["Duration", anime.duration ? `${anime.duration} min` : null],
  ];
  return (
    <article className="detail-page">
      <div
        aria-hidden="true"
        className={`detail-banner${anime.bannerImage ? " has-image" : ""}`}
        style={
          anime.bannerImage
            ? { backgroundImage: `url(${JSON.stringify(anime.bannerImage)})` }
            : anime.coverColor
              ? { backgroundColor: anime.coverColor }
              : undefined
        }
      />
      <div className="detail-layout">
        <aside aria-label="Anime controls" className="detail-sidebar">
          <div className="detail-cover">
            <PosterImage
              src={anime.coverImage}
              alt={anime.title}
              color={anime.coverColor}
            />
          </div>
          <div className="detail-action-stack">
            <div className="detail-anilist-score">
              <span>AniList score</span>
              <ScoreBadge
                className="detail-score"
                score={anime.score ?? null}
              />
              {anime.score == null && (
                <span className="detail-score">None</span>
              )}
            </div>
            <ListControl
              anime={anime}
              status={listStatus}
              rating={listRating}
              statusLoading={Boolean(user) && listStatusQuery.isLoading}
              variant="detail"
            />
          </div>
          <section aria-label="List actions" className="detail-list-actions">
            <ListRatingControl
              anime={anime}
              status={listStatus}
              rating={listRating}
              statusLoading={Boolean(user) && listStatusQuery.isLoading}
            />
          </section>
        </aside>
        <div className="detail-main">
          <header className="detail-heading">
            {kind.length > 0 && (
              <p className="detail-kind">{kind.join(", ")}</p>
            )}
            <h1 className="detail-title">
              {anime.title}
              {anime.titleNative && anime.titleNative !== anime.title && (
                <>
                  {" "}
                  <span className="accent detail-native" lang="ja">
                    {anime.titleNative}
                  </span>
                </>
              )}
            </h1>
            {subtitle && <p className="detail-subtitle">{subtitle}</p>}
            <p className="anime-meta">
              {[
                anime.year,
                anime.episodes ? `${anime.episodes} episodes` : null,
              ]
                .filter(Boolean)
                .join(", ")}
            </p>
          </header>
          <div className="detail-content">
            <div className="detail-overview">
              <section className="detail-synopsis">
                <h2 className="subheading">Synopsis</h2>
                <p>{anime.synopsis || "No synopsis available."}</p>
              </section>
              <section className="detail-facts panel">
                <h2 className="subheading">Details</h2>
                <dl className="detail-list">
                  {details
                    .filter(([, value]) => value != null && value !== "")
                    .map(([key, value]) => (
                      <div key={key}>
                        <dt>{key}</dt>
                        <dd>{value}</dd>
                      </div>
                    ))}
                </dl>
              </section>
            </div>
            {!!anime.genres?.length && (
              <section>
                <h2 className="subheading">Genres</h2>
                <div className="tag-list">
                  {anime.genres.map((genre) => (
                    <Link
                      className="tag-pill"
                      key={genre}
                      to={`/browse?genres=${encodeURIComponent(genre)}`}
                    >
                      {genre}
                    </Link>
                  ))}
                </div>
              </section>
            )}
            {!!tags.length && <TagList tags={tags.map((tag) => tag.name)} />}
            <section className="detail-similar">
              <h2 className="section-title">
                Similar <span className="accent">Anime</span>
              </h2>
              {similar.isLoading ? (
                <PosterSkeleton count={4} wide />
              ) : similar.isError ? (
                <ErrorState message="Could not load recommendations." />
              ) : !similar.data?.length ? (
                <p className="muted">No similar anime found.</p>
              ) : (
                <PosterGrid
                  animeIds={similar.data.map((rec) => rec.id)}
                  label="Similar anime"
                  wide
                >
                  {similar.data.map((rec) => (
                    <RecommendationCard key={rec.id} recommendation={rec} />
                  ))}
                </PosterGrid>
              )}
            </section>
          </div>
        </div>
      </div>
    </article>
  );
}

function titleCase(value?: string | null): string | null {
  if (!value) return null;
  const words = value.toLowerCase().replace(/_/g, " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}

function TagList({ tags }: { tags: string[] }) {
  const [showAll, setShowAll] = useState(false);
  const shown = showAll ? tags : tags.slice(0, 8);
  return (
    <section>
      <h2 className="subheading">Tags</h2>
      <div className="tag-list">
        {shown.map((tag) => (
          <Link
            className="tag-pill"
            key={tag}
            to={`/browse?tags=${encodeURIComponent(tag)}`}
          >
            {tag}
          </Link>
        ))}
        {tags.length > 8 && (
          <button
            className="clear-filters"
            onClick={() => setShowAll(!showAll)}
            type="button"
          >
            {showAll ? "Show fewer" : "Show more"}
          </button>
        )}
      </div>
    </section>
  );
}
