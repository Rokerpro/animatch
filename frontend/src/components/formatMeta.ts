import type { AnimeCardData } from "../api/types";

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

/** "TV, 2020, 24 eps" */
export function cardMeta(
  anime: Pick<AnimeCardData, "format" | "year" | "episodes">
): string {
  return [
    formatLabel(anime.format),
    anime.year,
    anime.episodes ? `${anime.episodes} eps` : null,
  ]
    .filter((part) => part !== null && part !== undefined && part !== "")
    .join(", ");
}
