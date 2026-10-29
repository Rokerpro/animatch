type ScoreBadgeProps = { score: number | null };

export function ScoreBadge({ score }: ScoreBadgeProps) {
  const label = score === null ? "Score unavailable" : `Score: ${score}%`;

  return (
    <span aria-label={label} className="score-text">
      {score === null ? "—" : `${Math.round(score)}%`}
    </span>
  );
}
