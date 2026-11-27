import type { AnimeCardData, ExtraItem } from "../api/types";

const FORMAT_LABELS: Record<string, string> = {
  TV: "TV",
  TV_SHORT: "TV short",
  MOVIE: "Movie",
  SPECIAL: "Special",
  OVA: "OVA",
  ONA: "ONA",
  MUSIC: "Music",
};

export function formatLabel(format?: string | null): string | null {
  if (!format) return null;
  return FORMAT_LABELS[format] ?? format;
}

const STATUS_LABELS: Record<string, string> = {
  FINISHED: "finished airing",
  RELEASING: "currently airing",
  NOT_YET_RELEASED: "not yet aired",
  CANCELLED: "cancelled",
  HIATUS: "on hiatus",
};

export function statusLabel(status?: string | null): string | null {
  if (!status) return null;
  return STATUS_LABELS[status] ?? status.toLowerCase().replace(/_/g, " ");
}

/** "TV, 2020, 24 eps", or "TV, 2020, 24 episodes" when `long`. */
export function cardMeta(
  anime: Pick<AnimeCardData, "format" | "year" | "episodes">,
  long = false
): string {
  return [
    formatLabel(anime.format),
    anime.year,
    long
      ? episodesText(anime.episodes)
      : anime.episodes
        ? `${anime.episodes} eps`
        : null,
  ]
    .filter((part) => part !== null && part !== undefined && part !== "")
    .join(", ");
}

/** AniList's 0-100 average score as "4.3" out of 5. */
export function scoreOutOfFive(score?: number | null): string | null {
  return score == null ? null : (score / 20).toFixed(1);
}

/** A stored 1-10 rating shown on the 5-point scale, in half steps: 9 -> "4.5". */
export function ratingOutOfFive(rating?: number | null): string | null {
  return rating == null ? null : (rating / 2).toFixed(1);
}

/** 1084000 -> "1.08M" */
export function compactCount(value: number): string {
  return new Intl.NumberFormat("en", {
    notation: "compact",
    maximumFractionDigits: 2,
  }).format(value);
}

/**
 * The cover colour's hue, softened for text and outlines on the dark page:
 * #f1a143 -> hsl(32 40% 72%), close to the design's #d3ba9c.
 */
export function coverTone(hex?: string | null): string | null {
  const match = /^#([0-9a-f]{6})$/i.exec(hex ?? "");
  if (!match) return null;
  const value = parseInt(match[1], 16);
  const [r, g, b] = [value >> 16, (value >> 8) & 255, value & 255].map(
    (channel) => channel / 255
  );
  const max = Math.max(r, g, b);
  const delta = max - Math.min(r, g, b);
  if (delta === 0) return null;
  const hue =
    max === r
      ? ((g - b) / delta + 6) % 6
      : max === g
        ? (b - r) / delta + 2
        : (r - g) / delta + 4;
  return `hsl(${Math.round(hue * 60)} 40% 72%)`;
}

export function episodesText(episodes?: number | null) {
  return episodes
    ? `${episodes} ${episodes === 1 ? "episode" : "episodes"}`
    : null;
}

/** "OVA, 2 episodes, 2014", "Spin-off, 12 episodes, 2015", "Recap film, 2020" */
export function extraMeta(extra: ExtraItem): string {
  const isMovie = extra.format === "MOVIE";
  const kind =
    extra.relation === "SPIN_OFF"
      ? "Spin-off"
      : extra.relation === "SUMMARY"
        ? isMovie
          ? "Recap film"
          : "Recap"
        : extra.relation === "ALTERNATIVE"
          ? `Alternative ${isMovie ? "film" : "version"}`
          : formatLabel(extra.format);
  return [kind, isMovie ? null : episodesText(extra.episodes), extra.year]
    .filter(Boolean)
    .join(", ");
}
