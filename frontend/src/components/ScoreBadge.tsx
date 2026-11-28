type ScoreBadgeProps = { score: number | null; className?: string };

export function ScoreBadge({
  score,
  className = "card-score",
}: ScoreBadgeProps) {
  const rating = score === null ? null : (score / 20).toFixed(1);
  const label =
    rating === null ? "Rating unavailable" : `Rating: ${rating} out of 5`;

  if (rating === null) return null;
  return (
    <span aria-label={label} className={className}>
      {rating}
    </span>
  );
}
