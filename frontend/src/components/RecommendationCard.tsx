import { useId, useState } from "react";
import { EyeOff } from "lucide-react";
import type { Recommendation } from "../api/types";
import { AnimeCard } from "./AnimeCard";

const REASON_PREVIEW_LENGTH = 88;
const SHARED_CHIPS = 3;

export function RecommendationCard({
  recommendation,
  onDismiss,
}: {
  recommendation: Recommendation;
  onDismiss?: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const reasonId = useId();
  const shared = [
    ...(recommendation.explanation?.sharedTags ?? []),
    ...(recommendation.explanation?.sharedGenres ?? []),
  ].slice(0, SHARED_CHIPS);
  const reason = recommendation.reason ?? "";
  const canExpand = reason.length > REASON_PREVIEW_LENGTH;
  const visibleReason =
    expanded || !canExpand
      ? reason
      : `${reason.slice(0, REASON_PREVIEW_LENGTH).trimEnd()}…`;

  return (
    <div className="recommendation-card">
      <AnimeCard anime={recommendation} />
      {shared.length > 0 ? (
        <div className="rec-shares">
          <span className="rec-shares-label">Shares</span>
          <ul aria-label="Shared genres and tags" className="rec-chips">
            {shared.map((name) => (
              <li key={name}>{name}</li>
            ))}
          </ul>
        </div>
      ) : (
        // Free-text picks (Ask) have no structured explanation.
        reason && (
          <p className="reason-text" id={reasonId}>
            {visibleReason}
            {canExpand && (
              <button
                aria-controls={reasonId}
                aria-expanded={expanded}
                className="reason-more"
                onClick={() => setExpanded((value) => !value)}
                type="button"
              >
                {expanded ? "Less" : "More"}
              </button>
            )}
          </p>
        )
      )}
      {onDismiss && (
        <button
          aria-label={`Not interested in ${recommendation.title}`}
          className="rec-dismiss"
          onClick={onDismiss}
          type="button"
        >
          <EyeOff aria-hidden="true" size={16} strokeWidth={1.5} />
          Not interested
        </button>
      )}
    </div>
  );
}
