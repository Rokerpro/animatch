import type { Recommendation } from "../api/types";
import { AnimeCard } from "./AnimeCard";
export function RecommendationCard({ recommendation }: { recommendation: Recommendation }) {
  return <div className="recommendation-card"><AnimeCard anime={recommendation} />
    {recommendation.reason?.trim() && <p className="reason-text">{recommendation.reason}</p>}
  </div>;
}
