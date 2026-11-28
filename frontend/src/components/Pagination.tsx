import { useSearchParams } from "react-router-dom";

/** Page numbers with gaps: 1 … 4 5 6 … 51 */
function pageItems(page: number, lastPage: number): (number | "gap")[] {
  if (lastPage <= 7)
    return Array.from({ length: lastPage }, (_, index) => index + 1);
  const pages = new Set([1, lastPage, page - 1, page, page + 1]);
  if (page <= 3) [2, 3, 4].forEach((n) => pages.add(n));
  if (page >= lastPage - 2)
    [lastPage - 3, lastPage - 2, lastPage - 1].forEach((n) => pages.add(n));
  const sorted = [...pages]
    .filter((n) => n >= 1 && n <= lastPage)
    .sort((a, b) => a - b);
  const items: (number | "gap")[] = [];
  sorted.forEach((n, index) => {
    if (index > 0 && n - sorted[index - 1] > 1) items.push("gap");
    items.push(n);
  });
  return items;
}

export function Pagination({
  page,
  lastPage,
}: {
  page: number;
  lastPage: number;
}) {
  const [params, setParams] = useSearchParams();
  if (lastPage <= 1) return null;
  const go = (n: number) => {
    const next = new URLSearchParams(params);
    next.set("page", String(n));
    setParams(next);
    if (typeof window.scrollTo === "function") window.scrollTo(0, 0);
  };
  return (
    <nav className="pagination" aria-label="Pagination">
      <button disabled={page <= 1} onClick={() => go(page - 1)} type="button">
        Previous
      </button>
      {pageItems(page, lastPage).map((item, index) =>
        item === "gap" ? (
          <span
            aria-hidden="true"
            className="pagination-gap"
            key={`gap-${index}`}
          >
            …
          </span>
        ) : (
          <button
            aria-current={item === page ? "page" : undefined}
            key={item}
            onClick={() => go(item)}
            type="button"
          >
            {item}
          </button>
        )
      )}
      <button
        disabled={page >= lastPage}
        onClick={() => go(page + 1)}
        type="button"
      >
        Next
      </button>
    </nav>
  );
}
