import type { ReactNode } from "react";
export function PosterGrid({ children, label = "Anime results" }: { children: ReactNode; label?: string }) {
  return <div className="poster-grid" aria-label={label}>{children}</div>;
}
