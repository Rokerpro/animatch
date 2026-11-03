type ScoreBadgeProps = { score: number | null };

export function ScoreBadge({ score }: ScoreBadgeProps) {
  const rating = score === null ? null : (score / 20).toFixed(1);
  const label = rating === null ? "Rating unavailable" : `Rating: ${rating} out of 5`;

  return (
    <span aria-label={label} className="score-text">
      {rating === null ? "—" : <><a
        aria-label="AniList, Public domain, via Wikimedia Commons"
        className="anilist-source"
        href="https://commons.wikimedia.org/wiki/File:AniList_logo.svg"
        rel="noreferrer"
        target="_blank"
      ><img alt="AniList" src="https://upload.wikimedia.org/wikipedia/commons/6/61/AniList_logo.svg" /></a> {rating}/5</>}
    </span>
  );
}
