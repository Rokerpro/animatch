import { Link, useParams } from "react-router-dom";
import { useAnimeDetail, useSimilar } from "../api/hooks";
import { useAuth } from "../auth/useAuth";
import { PageTitle } from "../components/PageTitle";
import { PosterGrid } from "../components/PosterGrid";
import { RecommendationCard } from "../components/RecommendationCard";
import {
  EmptyState,
  ErrorState,
  PosterSkeleton,
} from "../components/RequestStates";
import { PosterImage } from "../components/PosterImage";
import { formatLabel } from "../components/formatMeta";

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
  return (
    <section className="browse-page similar-results-page">
      <header className="page-header">
        <PageTitle lead="Anime Similar to" accent={seed.title} />
      </header>
      <div className="similar-seed panel">
        <div className="similar-seed-cover">
          <PosterImage
            alt={seed.title}
            color={seed.coverColor}
            src={seed.coverImage}
          />
        </div>
        <div className="similar-seed-copy">
          <p className="similar-seed-label">Based on your pick</p>
          <Link className="similar-seed-title" to={`/anime/${seed.id}`}>
            {seed.title}
          </Link>
          <p className="muted">
            {[formatLabel(seed.format), seed.year].filter(Boolean).join(", ")}
          </p>
        </div>
        {count > 0 && (
          <p className="similar-seed-count">
            {count} {count === 1 ? "match" : "matches"}
          </p>
        )}
      </div>
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
