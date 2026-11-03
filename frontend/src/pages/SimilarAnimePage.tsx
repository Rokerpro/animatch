import { Link, useParams } from "react-router-dom";
import { useAnimeDetail, useSimilar } from "../api/hooks";
import { useAuth } from "../auth/useAuth";
import { PosterGrid } from "../components/PosterGrid";
import { RecommendationCard } from "../components/RecommendationCard";
import { EmptyState, ErrorState, PosterSkeleton } from "../components/RequestStates";
import { PosterImage } from "../components/PosterImage";

export function SimilarAnimePage() {
  const id = Number(useParams().id);
  const { mature } = useAuth();
  const anime = useAnimeDetail(id, mature);
  const similar = useSimilar(id, mature);

  if (anime.isLoading) {
    return <section className="browse-page"><PosterSkeleton count={4} /></section>;
  }
  if (anime.isError || !anime.data) {
    return <section className="browse-page"><ErrorState message="Could not load the selected anime." /></section>;
  }

  const seed = anime.data;
  return (
    <section className="browse-page similar-results-page">
      <h1 className="page-title">Anime similar to {seed.title}</h1>
      <div className="similar-seed">
        <PosterImage alt={seed.title} src={seed.coverImage} />
        <div>
          <p className="similar-seed-label">Based on your pick</p>
          <Link to={`/anime/${seed.id}`}>{seed.title}</Link>
          <p>{[seed.format, seed.year].filter(Boolean).join(" · ")}</p>
        </div>
      </div>
      {similar.isLoading ? <PosterSkeleton count={4} /> : similar.isError ? (
        <ErrorState message="Could not load similar anime. Please try again." />
      ) : !similar.data?.length ? (
        <EmptyState title={`No similar anime found for ${seed.title}.`} />
      ) : (
        <PosterGrid label={`Anime similar to ${seed.title}`}>
          {similar.data.map((recommendation) => (
            <RecommendationCard key={recommendation.id} recommendation={recommendation} />
          ))}
        </PosterGrid>
      )}
    </section>
  );
}
