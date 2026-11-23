import { useEffect } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ApiError, api } from "../api/client";
import { safeNextPath } from "../auth/nextPath";
import { useAuth } from "../auth/useAuth";
import { RecommendationCard } from "../components/RecommendationCard";
import { PosterGrid } from "../components/PosterGrid";
import { useFeatures } from "../api/useFeatures";

export function ForYouPage() {
  const { user, authLoading, mature } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const next = safeNextPath(`${location.pathname}${location.search}`, "/for-you");
  const recs = useQuery({ queryKey: ["my-recommendations", mature], queryFn: () => api.myRecommendations(mature), enabled: Boolean(user), retry: false });
  const features = useFeatures();
  const heading = <header className="for-you-heading"><h1 className="page-title">For you</h1><div className="for-you-heading-actions"><Link className="primary-action" to="/new">Find something new</Link>{features.data?.natural_language && <Link className="secondary-action" to="/ask">Describe what you want</Link>}</div></header>;
  useEffect(() => { if (recs.error instanceof ApiError && recs.error.status === 401) navigate(`/login?next=${encodeURIComponent(next)}`, { replace: true }); }, [navigate, next, recs.error]);
  if (authLoading) return <section className="browse-page"><p>Checking your account…</p></section>;
  if (!user) return <Navigate replace to={`/login?next=${encodeURIComponent("/for-you")}`} />;
  if (recs.isPending) return <section className="browse-page for-you-page">{heading}<p>Finding recommendations…</p></section>;
  if (recs.error instanceof ApiError && recs.error.status === 401) return <section className="browse-page"><p>Redirecting to sign in…</p></section>;
  if (recs.error) return <section className="browse-page for-you-page">{heading}<p role="alert">{recs.error.message}</p><button className="text-button" onClick={() => void recs.refetch()} type="button">Retry</button></section>;
  const results = recs.data ?? [];
  return <section className="browse-page for-you-page">{heading}{results.length ? <PosterGrid animeIds={results.map((result) => result.id)} label="Recommendations for you">{results.map((result) => <RecommendationCard key={result.id} recommendation={result} />)}</PosterGrid> : <div className="empty-recommendations"><p>No recommendations yet. Take the quiz or rate anime to build your profile.</p><div className="for-you-empty-actions"><Link className="primary-action" to="/quiz">Take the quiz</Link><Link className="secondary-action" to="/new">Find something new</Link>{features.data?.natural_language && <Link className="secondary-action" to="/ask">Describe what you want</Link>}</div></div>}</section>;
}
