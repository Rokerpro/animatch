import { useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { ApiError, api } from "../api/client";
import { RecommendationCard } from "../components/RecommendationCard";
import { PosterGrid } from "../components/PosterGrid";
import { PosterSkeleton } from "../components/RequestStates";
import { useAuth } from "../auth/useAuth";
import { readSavedStart, saveStart } from "../startStorage";

export function StartResultsPage() {
  const [saved, setSaved] = useState(readSavedStart);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [retryCount, setRetryCount] = useState(0);
  const { mature } = useAuth();

  useEffect(() => {
    if (!saved || saved.include_mature === mature) return;
    let active = true;
    setError("");
    setRefreshing(true);
    void api
      .startRecommendations(saved.liked_ids, mature)
      .then((results) => {
        if (!active) return;
        const updated = { ...saved, results, include_mature: mature };
        saveStart(updated);
        setSaved(updated);
      })
      .catch((reason: unknown) => {
        if (!active) return;
        setError(
          reason instanceof ApiError
            ? reason.message
            : "Could not update recommendations. Try again.",
        );
      })
      .finally(() => {
        if (active) setRefreshing(false);
      });
    return () => {
      active = false;
    };
  }, [mature, retryCount, saved]);

  if (!saved) return <Navigate to="/" replace />;

  return (
    <section className="browse-page results-page">
      <h1 className="page-title">Recommendations based on your picks</h1>
      <div className="results-actions">
        <Link className="text-button" to="/quiz">Take the quiz</Link>
      </div>
      {error && (
        <div className="status-box status-error" role="alert">
          <p>{error}</p>
          <button
            className="text-button"
            onClick={() => setRetryCount((count) => count + 1)}
            type="button"
          >
            Retry
          </button>
        </div>
      )}
      {refreshing ? (
        <>
          <p aria-live="polite">Updating recommendations…</p>
          <PosterSkeleton count={4} />
        </>
      ) : saved.results.length ? (
        <PosterGrid animeIds={saved.results.map((result) => result.id)} label="Recommendations based on your picks">
          {saved.results.map((result) => (
            <RecommendationCard key={result.id} recommendation={result} />
          ))}
        </PosterGrid>
      ) : (
        !error && <p>No recommendations were found for these titles.</p>
      )}
    </section>
  );
}
