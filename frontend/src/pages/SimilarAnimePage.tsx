import type { CSSProperties } from "react";
import { Link, useParams } from "react-router-dom";
import { useAnimeDetail, useSimilar } from "../api/hooks";
import { useAuth } from "../auth/useAuth";
import { PosterGrid } from "../components/PosterGrid";
import { RecommendationCard } from "../components/RecommendationCard";
import {
  EmptyState,
  ErrorState,
  PosterSkeleton,
} from "../components/RequestStates";
import { PosterImage } from "../components/PosterImage";
import { coverTone } from "../components/formatMeta";
import "../styles/similar.css";

export function SimilarAnimePage() {
  const id = Number(useParams().id);
  const { mature } = useAuth();
  const anime = useAnimeDetail(id, mature);
  const similar = useSimilar(id, mature);

  if (anime.isLoading) {
    return (
      <section className="browse-page page-top">
        <PosterSkeleton count={5} wide />
      </section>
    );
  }
  if (anime.isError || !anime.data) {
    return (
      <section className="browse-page page-top">
        <ErrorState message="Could not load the selected anime." />
      </section>
    );
  }

  const seed = anime.data;
  const count = similar.data?.length ?? 0;
  const tone = coverTone(seed.coverColor);
  const style = {
    ...(seed.coverColor ? { "--cover": seed.coverColor } : {}),
    ...(tone ? { "--accent": tone } : {}),
  } as CSSProperties;
  return (
    <section className="browse-page similar-page" style={style}>
      <header className="similar-hero">
        <div className="similar-cover">
          <PosterImage
            alt={seed.title}
            color={seed.coverColor}
            src={seed.coverImage}
          />
        </div>
        <div className="similar-heading">
          <h1 className="similar-title">
            <span className="similar-lead">Anime like</span> {seed.title}
          </h1>
          {count > 0 && (
            <p className="similar-count">
              {count} {count === 1 ? "match" : "matches"}, ranked by shared
              genres and themes
            </p>
          )}
        </div>
        <Link
          className="secondary-action similar-open"
          to={`/anime/${seed.id}`}
        >
          Open {seed.title}
        </Link>
      </header>
      {similar.isLoading ? (
        <PosterSkeleton count={5} wide />
      ) : similar.isError ? (
        <ErrorState message="Could not load similar anime. Please try again." />
      ) : !similar.data?.length ? (
        <EmptyState title={`No similar anime found for ${seed.title}.`} />
      ) : (
        <PosterGrid
          animeIds={similar.data.map((recommendation) => recommendation.id)}
          label={`Anime similar to ${seed.title}`}
          wide
        >
          {similar.data.map((recommendation) => (
            <RecommendationCard
              key={recommendation.id}
              recommendation={recommendation}
            />
          ))}
        </PosterGrid>
      )}
    </section>
  );
}
