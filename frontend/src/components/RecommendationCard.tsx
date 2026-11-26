import { useId, useState } from "react";
import type { Recommendation } from "../api/types";
import { AnimeCard } from "./AnimeCard";

const REASON_PREVIEW_LENGTH = 88;

export function RecommendationCard({
  recommendation,
  onDismiss,
}: {
  recommendation: Recommendation;
  onDismiss?: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const reasonId = useId();
  const reason = recommendation.reason ?? "";
  const canExpand = reason.length > REASON_PREVIEW_LENGTH;
  const visibleReason =
    expanded || !canExpand
      ? reason
      : `${reason.slice(0, REASON_PREVIEW_LENGTH).trimEnd()}…`;

  return (
    <div className="recommendation-card">
      <AnimeCard anime={recommendation} />
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
      {onDismiss && (
        <button
          aria-label={`Not interested in ${recommendation.title}`}
          className="rec-dismiss"
          onClick={onDismiss}
          type="button"
        >
          Not interested
        </button>
      )}
    </div>
  );
}
