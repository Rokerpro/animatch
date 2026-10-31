import type { ReactNode } from "react";
import { CircleAlert } from "lucide-react";

export function PosterSkeleton({ count = 12 }: { count?: number }) {
  return (
    <div aria-busy="true" aria-label="Loading anime" className="poster-grid">
      {Array.from({ length: count }, (_, index) => (
        <div aria-hidden="true" className="poster-skeleton" key={index}>
          <div className="poster-skeleton-image" />
          <div className="poster-skeleton-title" />
          <div className="poster-skeleton-meta" />
        </div>
      ))}
    </div>
  );
}

export function EmptyState({
  title,
  children,
}: {
  title: string;
  children?: ReactNode;
}) {
  return (
    <section className="request-state" aria-labelledby="empty-state-title">
      <h2 id="empty-state-title">{title}</h2>
      {children && <div className="request-state-body">{children}</div>}
    </section>
  );
}

export function ErrorState({
  title = "Something went wrong",
  message,
  onRetry,
}: {
  title?: string;
  message: string;
  onRetry?: () => void;
}) {
  return (
    <section className="request-state" aria-labelledby="error-state-title" role="alert">
      <CircleAlert aria-hidden="true" className="request-state-icon" size={20} />
      <h2 id="error-state-title">{title}</h2>
      <p className="request-state-body">{message}</p>
      {onRetry && (
        <button className="text-button" onClick={onRetry} type="button">
          Try again
        </button>
      )}
    </section>
  );
}
