import { useSearchParams } from "react-router-dom";
export function Pagination({ page, lastPage }: { page: number; lastPage: number }) {
  const [params, setParams] = useSearchParams();
  if (lastPage <= 1) return null;
  const go = (n: number) => { const next = new URLSearchParams(params); next.set("page", String(n)); setParams(next); };
  const pages = Array.from({ length: Math.min(lastPage, 7) }, (_, i) => Math.max(1, Math.min(lastPage - 6, page - 3)) + i);
  return <nav className="pagination" aria-label="Pagination">
    <button disabled={page <= 1} onClick={() => go(page - 1)}>Previous</button>
    {pages.map((n) => <button aria-current={n === page ? "page" : undefined} key={n} onClick={() => go(n)}>{n}</button>)}
    <button disabled={page >= lastPage} onClick={() => go(page + 1)}>Next</button>
  </nav>;
}
