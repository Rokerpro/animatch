import { useState } from "react";
import type { CSSProperties } from "react";
import { Link, useParams } from "react-router-dom";
import {
  compactCount,
  coverTone,
  formatLabel,
  scoreOutOfFive,
  statusLabel,
} from "../components/formatMeta";
import { ApiError } from "../api/client";
import { useAnimeDetail, useListStatuses, useSimilar } from "../api/hooks";
import { useAuth } from "../auth/useAuth";
import { PosterGrid } from "../components/PosterGrid";
import { PosterImage } from "../components/PosterImage";
import { RecommendationCard } from "../components/RecommendationCard";
import { ErrorState, PosterSkeleton } from "../components/RequestStates";
import { ListControl, ListRatingControl } from "../components/ListControls";
import { SeasonsSection } from "../components/SeasonsSection";
import "../styles/detail.css";

const TAG_PREVIEW = 9;

export function AnimeDetailPage() {
  const id = Number(useParams().id);
  const { mature, user } = useAuth();
  const detail = useAnimeDetail(id, mature);
  const similar = useSimilar(id, mature);
  const listStatusQuery = useListStatuses([id], mature, Boolean(user));
  if (detail.isLoading)
    return (
      <section className="title-page title-state">
        <PosterSkeleton count={3} />
      </section>
    );
  if (detail.error instanceof ApiError && detail.error.status === 404)
    return (
      <section className="title-page title-state">
        <p role="status">Not found, or hidden by your content settings</p>
      </section>
    );
  if (detail.isError || !detail.data)
    return (
      <section className="title-page title-state">
        <ErrorState message="Could not load this anime." />
      </section>
    );
  const anime = detail.data;
  const tags = [...(anime.tagDetails ?? [])]
    .filter((tag) => !tag.isSpoiler)
    .sort((a, b) => (b.rank ?? 0) - (a.rank ?? 0))
    .map((tag) => tag.name);
  const listEntry = listStatusQuery.data?.items.find(
    (entry) => entry.animeId === anime.id
  );
  const listStatus = listEntry?.status ?? null;
  const listRating = listEntry?.rating ?? null;
  const statusLoading = Boolean(user) && listStatusQuery.isLoading;
  const romaji =
    anime.titleRomaji && anime.titleRomaji !== anime.title
      ? anime.titleRomaji
      : null;
  const native =
    anime.titleNative && anime.titleNative !== anime.title
      ? anime.titleNative
      : null;
  const status = statusLabel(anime.status);
  const pills = [
    formatLabel(anime.format),
    anime.year,
    anime.episodes
      ? `${anime.episodes} ${anime.episodes === 1 ? "episode" : "episodes"}`
      : null,
    status && status.charAt(0).toUpperCase() + status.slice(1),
  ].filter(Boolean);
  const season = [titleCase(anime.season), anime.seasonYear]
    .filter(Boolean)
    .join(" ");
  const stats: {
    label: string;
    value: string;
    unit?: string;
    score?: boolean;
  }[] = [
    ...(anime.score != null
      ? [
          {
            label: "AniList score",
            value: scoreOutOfFive(anime.score)!,
            unit: " / 5",
            score: true,
          },
        ]
      : []),
    ...(anime.popularity
      ? [
          {
            label: "Popularity",
            value: compactCount(anime.popularity),
            unit: " members",
          },
        ]
      : []),
    ...(season ? [{ label: "Season", value: season }] : []),
    ...(anime.studio ? [{ label: "Studio", value: anime.studio }] : []),
    ...(anime.episodes
      ? [
          {
            label: "Episodes",
            value: String(anime.episodes),
            unit: anime.duration ? ` x ${anime.duration} min` : undefined,
          },
        ]
      : []),
  ];
  const tone = coverTone(anime.coverColor);
  const style = {
    ...(anime.coverColor ? { "--cover": anime.coverColor } : {}),
    ...(tone ? { "--accent": tone } : {}),
  } as CSSProperties;

  return (
    <article className="title-page" style={style}>
      <header className="title-hero">
        <div className="title-cover">
          <PosterImage
            alt={anime.title}
            color={anime.coverColor}
            src={anime.coverImage}
          />
        </div>
        <div className="title-heading">
          {pills.length > 0 && (
            <ul aria-label="Overview" className="title-pills">
              {pills.map((pill) => (
                <li key={String(pill)}>{pill}</li>
              ))}
            </ul>
          )}
          <h1 className="title-name">{anime.title}</h1>
          {(native || romaji) && (
            <p className="title-alt">
              {native && (
                <span className="title-native" lang="ja">
                  {native}
                </span>
              )}
              {romaji && <span className="title-romaji">{romaji}</span>}
            </p>
          )}
          <div className="title-actions">
            <ListControl
              anime={anime}
              rating={listRating}
              status={listStatus}
              statusLoading={statusLoading}
              variant="detail"
            />
            <ListRatingControl
              anime={anime}
              rating={listRating}
              status={listStatus}
              statusLoading={statusLoading}
            />
          </div>
        </div>
      </header>
      {stats.length > 0 && (
        <dl className="title-stats">
          {stats.map((stat) => (
            <div key={stat.label}>
              <dt>{stat.label}</dt>
              <dd>
                <span className={stat.score ? "title-score" : undefined}>
                  {stat.value}
                </span>
                {stat.unit && <span className="title-unit">{stat.unit}</span>}
              </dd>
            </div>
          ))}
        </dl>
      )}
      <div className="title-overview">
        <section aria-labelledby="synopsis-title" className="title-synopsis">
          <h2 className="title-label" id="synopsis-title">
            Synopsis
          </h2>
          {(anime.synopsis || "No synopsis available.")
            .split(/\n+/)
            .filter((paragraph) => paragraph.trim())
            .map((paragraph, index) => (
              <p key={index}>{paragraph}</p>
            ))}
        </section>
        <div className="title-facets">
          {!!anime.genres?.length && (
            <section aria-labelledby="genres-title">
              <h2 className="title-label" id="genres-title">
                Genres
              </h2>
              <div className="title-chips">
                {anime.genres.map((genre) => (
                  <Link
                    key={genre}
                    to={`/browse?genres=${encodeURIComponent(genre)}`}
                  >
                    {genre}
                  </Link>
                ))}
              </div>
            </section>
          )}
          {!!tags.length && <TagList tags={tags} />}
        </div>
      </div>
      <SeasonsSection animeId={anime.id} mature={mature} />
      <section aria-labelledby="similar-title" className="title-section">
        <h2 className="title-section-heading" id="similar-title">
          Similar Anime
        </h2>
        <p className="title-section-sub">
          Matched on what makes {anime.title} work
        </p>
        {similar.isLoading ? (
          <PosterSkeleton count={5} wide />
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
  const shown = showAll ? tags : tags.slice(0, TAG_PREVIEW);
  return (
    <section aria-labelledby="tags-title">
      <h2 className="title-label" id="tags-title">
        Tags
      </h2>
      <div className="title-chips">
        {shown.map((tag) => (
          <Link key={tag} to={`/browse?tags=${encodeURIComponent(tag)}`}>
            {tag}
          </Link>
        ))}
      </div>
      {tags.length > TAG_PREVIEW && (
        <button
          aria-expanded={showAll}
          className="title-more"
          onClick={() => setShowAll(!showAll)}
          type="button"
        >
          {showAll ? "Show fewer tags" : "Show all tags"}
        </button>
      )}
    </section>
  );
}
