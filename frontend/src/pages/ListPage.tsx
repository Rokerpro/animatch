import { useEffect, useRef } from "react";
import { Link, Navigate, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { ApiError } from "../api/client";
import { useList } from "../api/hooks";
import type { ListSort, ListStatus } from "../api/types";
import { useAuth } from "../auth/useAuth";
import { safeNextPath } from "../auth/nextPath";
import { ListControl, ListRatingControl } from "../components/ListControls";
import { listStatusLabels, listStatuses } from "../components/listStatus";
import { Pagination } from "../components/Pagination";
import { PosterImage } from "../components/PosterImage";
import { ErrorState, PosterSkeleton } from "../components/RequestStates";

const tabs: { value: ListStatus | "all"; label: string }[] = [
  { value: "all", label: "All" },
  ...listStatuses.map((status) => ({ value: status, label: listStatusLabels[status] })),
];

export function ListPage() {
  const { user, authLoading, mature } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const tabRefs = useRef<Array<HTMLButtonElement | null>>([]);
  const requestedStatus = params.get("status") as ListStatus | null;
  const selectedStatus = listStatuses.includes(requestedStatus as ListStatus) ? requestedStatus! : "all";
  const sortValue = params.get("sort") as ListSort | null;
  const sort: ListSort = sortValue === "rating" || sortValue === "title" ? sortValue : "updated";
  const page = Math.max(1, Number(params.get("page") ?? 1) || 1);
  const list = useList({ status: selectedStatus === "all" ? undefined : selectedStatus, sort, page, pageSize: 24, includeMature: mature }, Boolean(user) && !authLoading);
  const nextPath = safeNextPath(`${location.pathname}${location.search}`, "/list");

  useEffect(() => {
    if (list.error instanceof ApiError && list.error.status === 401) {
      navigate(`/login?next=${encodeURIComponent(nextPath)}`, { replace: true });
    }
  }, [list.error, navigate, nextPath]);

  function setParam(name: string, value: string | null) {
    const next = new URLSearchParams(params);
    if (value) next.set(name, value); else next.delete(name);
    next.delete("page");
    setParams(next);
  }

  function selectTab(index: number) {
    const tab = tabs[index];
    tabRefs.current[index]?.focus();
    setParam("status", tab.value === "all" ? null : tab.value);
  }

  if (authLoading) return <section className="browse-page"><p>Checking your account…</p></section>;
  if (!user) return <Navigate replace to={`/login?next=${encodeURIComponent("/list")}`} />;
  if (list.error instanceof ApiError && list.error.status === 401) return <section className="browse-page"><p>Redirecting to sign in…</p></section>;
  if (list.isLoading && !list.data) return <section className="browse-page"><h1 className="page-title">My list</h1><PosterSkeleton count={8} /></section>;
  if (list.isError || !list.data) return <section className="browse-page"><h1 className="page-title">My list</h1><ErrorState message={list.error instanceof Error ? list.error.message : "Could not load your list."} onRetry={() => void list.refetch()} /></section>;

  return <section className="browse-page my-list-page">
    <div className="list-page-heading"><div><p className="eyebrow">Your anime</p><h1 className="page-title">My list</h1></div><span className="list-total">{list.data.page_info.total} titles</span></div>
    <div className="list-controls-row">
      <div className="list-tabs-shell">
        <div aria-label="Filter list by status" className="list-status-tabs" onKeyDown={(event) => {
          const current = tabs.findIndex((tab) => tab.value === selectedStatus);
          if (event.key === "ArrowRight") { event.preventDefault(); selectTab((current + 1) % tabs.length); }
          if (event.key === "ArrowLeft") { event.preventDefault(); selectTab((current - 1 + tabs.length) % tabs.length); }
          if (event.key === "Home") { event.preventDefault(); selectTab(0); }
          if (event.key === "End") { event.preventDefault(); selectTab(tabs.length - 1); }
        }} role="tablist" tabIndex={0}>
          {tabs.map((tab, index) => <button aria-selected={selectedStatus === tab.value} className="list-status-tab" id={`list-tab-${tab.value}`} key={tab.value} onClick={() => setParam("status", tab.value === "all" ? null : tab.value)} ref={(node) => { tabRefs.current[index] = node; }} role="tab" tabIndex={selectedStatus === tab.value ? 0 : -1} type="button">{tab.label}</button>)}
        </div>
      </div>
      <label className="list-sort-control"><span>Sort by</span><select aria-label="Sort list" onChange={(event) => setParam("sort", event.target.value)} value={sort}><option value="updated">Recently updated</option><option value="rating">Rating</option><option value="title">Title</option></select></label>
    </div>
    <section aria-labelledby={`list-tab-${selectedStatus}`} className="list-tabpanel" id="my-list-panel" role="tabpanel">
      {list.data.items.length ? <>
        <p className="result-count">Showing {list.data.items.length} of {list.data.page_info.total} titles</p>
        <div className="my-list-grid">
          {list.data.items.map((entry) => <article className="my-list-card" key={entry.id}>
            <div className="my-list-card-poster"><Link aria-label={entry.anime.title} to={`/anime/${entry.anime_id}`}><PosterImage alt={entry.anime.title} src={entry.anime.coverImage} /></Link><ListControl anime={entry.anime} status={entry.status} rating={entry.rating} variant="card" /></div>
            <div className="my-list-card-content"><Link className="my-list-card-title" to={`/anime/${entry.anime_id}`}>{entry.anime.title}</Link><p className="my-list-status-label">{listStatusLabels[entry.status]}</p><ListRatingControl anime={entry.anime} status={entry.status} rating={entry.rating} /></div>
          </article>)}
        </div>
        <Pagination page={page} lastPage={Math.max(1, Math.ceil(list.data.page_info.total / list.data.page_info.per_page))} />
      </> : <div className="empty-recommendations"><p>{selectedStatus === "all" ? "Your list is empty. Take the quiz to find anime to add." : `No titles in ${listStatusLabels[selectedStatus]} yet.`}</p><Link className="primary-action" to="/quiz">Take the quiz</Link></div>}
    </section>
  </section>;
}
