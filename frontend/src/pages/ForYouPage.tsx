import { useEffect } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError, api, getErrorMessage } from "../api/client";
import type { Recommendation } from "../api/types";
import { useOptionalToast } from "../components/useToast";
import { safeNextPath } from "../auth/nextPath";
import { useAuth } from "../auth/useAuth";
import { RecommendationCard } from "../components/RecommendationCard";
import { PosterGrid } from "../components/PosterGrid";
import { useFeatures } from "../api/useFeatures";
import { useListStats } from "../api/hooks";
import { PageTitle } from "../components/PageTitle";
import { PosterSkeleton } from "../components/RequestStates";

export function ForYouPage() {
  const { user, authLoading, mature } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const next = safeNextPath(
    `${location.pathname}${location.search}`,
    "/for-you"
  );
  const recs = useQuery({
    queryKey: ["my-recommendations", mature],
    queryFn: () => api.myRecommendations(mature),
    enabled: Boolean(user),
    retry: false,
  });
  const queryClient = useQueryClient();
  const { showToast } = useOptionalToast();
  const recsKey = ["my-recommendations", mature];
  const dismiss = useMutation({
    mutationFn: (animeId: number) => api.hideRecommendation(animeId),
    onMutate: async (animeId) => {
      await queryClient.cancelQueries({ queryKey: recsKey });
      const previous = queryClient.getQueryData<Recommendation[]>(recsKey);
      queryClient.setQueryData<Recommendation[]>(recsKey, (old) =>
        old?.filter((item) => item.id !== animeId)
      );
      return previous;
    },
    onError: (error, _animeId, previous) => {
      queryClient.setQueryData(recsKey, previous);
      showToast(getErrorMessage(error, "Could not hide this title."), "error");
    },
    onSuccess: () => showToast("We will stop suggesting this one", "success"),
    onSettled: () =>
      queryClient.invalidateQueries({ queryKey: ["my-recommendations"] }),
  });
  const features = useFeatures();
  const stats = useListStats(mature, Boolean(user));
  const total = stats.data?.total ?? 0;
  const heading = (
    <header className="page-header for-you-heading">
      <div>
        <PageTitle lead="For" accent="You" />
        <p className="page-subtitle">
          {total > 0
            ? `Picked from your quiz answers and the ${total} ${total === 1 ? "title" : "titles"} on your list.`
            : "Picked from your quiz answers and your list."}
        </p>
      </div>
      <div className="page-header-aside for-you-heading-actions">
        {features.data?.natural_language && (
          <Link className="secondary-action" to="/ask">
            Describe what you want
          </Link>
        )}
        <Link className="primary-action" to="/new">
          Find something new
        </Link>
      </div>
    </header>
  );
  useEffect(() => {
    if (recs.error instanceof ApiError && recs.error.status === 401)
      navigate(`/login?next=${encodeURIComponent(next)}`, { replace: true });
  }, [navigate, next, recs.error]);
  if (authLoading)
    return (
      <section className="browse-page">
        <p>Checking your account…</p>
      </section>
    );
  if (!user)
    return (
      <Navigate replace to={`/login?next=${encodeURIComponent("/for-you")}`} />
    );
  if (recs.isPending)
    return (
      <section className="browse-page for-you-page">
        {heading}
        <PosterSkeleton count={5} wide />
      </section>
    );
  if (recs.error instanceof ApiError && recs.error.status === 401)
    return (
      <section className="browse-page">
        <p>Redirecting to sign in…</p>
      </section>
    );
  if (recs.error)
    return (
      <section className="browse-page for-you-page">
        {heading}
        <p role="alert">{recs.error.message}</p>
        <button
          className="text-button"
          onClick={() => void recs.refetch()}
          type="button"
        >
          Retry
        </button>
      </section>
    );
  const results = recs.data ?? [];
  return (
    <section className="browse-page for-you-page">
      {heading}
      {results.length ? (
        <PosterGrid
          animeIds={results.map((result) => result.id)}
          label="Recommendations for you"
          wide
        >
          {results.map((result) => (
            <RecommendationCard
              key={result.id}
              onDismiss={() => dismiss.mutate(result.id)}
              recommendation={result}
            />
          ))}
        </PosterGrid>
      ) : (
        <div className="empty-recommendations">
          <p>
            No recommendations yet. Take the quiz or rate anime to build your
            profile.
          </p>
          <div className="for-you-empty-actions">
            <Link className="primary-action" to="/quiz">
              Take the quiz
            </Link>
            <Link className="secondary-action" to="/new">
              Find something new
            </Link>
            {features.data?.natural_language && (
              <Link className="secondary-action" to="/ask">
                Describe what you want
              </Link>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
