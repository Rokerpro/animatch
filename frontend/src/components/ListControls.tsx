import { useEffect, useRef, useState } from "react";
import { Bookmark, BookmarkCheck, X } from "lucide-react";
import { useLocation } from "react-router-dom";
import type { AnimeCardData, ListStatus } from "../api/types";
import { useAuth } from "../auth/useAuth";
import { safeNextPath } from "../auth/nextPath";
import { useListMutation } from "../api/useListMutation";
import { AuthPrompt } from "./AuthPrompt";
import { listStatusLabels, listStatuses } from "./listStatus";

export function ListControl({ anime, status, rating, statusLoading = false, variant = "card" }: {
  anime: AnimeCardData; status: ListStatus | null; rating: number | null; statusLoading?: boolean; variant?: "card" | "detail";
}) {
  const { user } = useAuth();
  const location = useLocation();
  const mutation = useListMutation();
  const [open, setOpen] = useState(false);
  const [promptOpen, setPromptOpen] = useState(false);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const nextPath = safeNextPath(`${location.pathname}${location.search}`, "/browse");

  useEffect(() => {
    if (open) menuRef.current?.querySelector<HTMLElement>("[role='menuitemradio'], [role='menuitem']")?.focus();
  }, [open]);

  function closeMenu(restoreFocus = false) {
    setOpen(false);
    if (restoreFocus) buttonRef.current?.focus();
  }

  function onMenuKeyDown(event: React.KeyboardEvent<HTMLDivElement>) {
    const items = Array.from(menuRef.current?.querySelectorAll<HTMLElement>("[role='menuitemradio'], [role='menuitem']") ?? []);
    const current = items.indexOf(document.activeElement as HTMLElement);
    if (event.key === "Escape") { event.preventDefault(); closeMenu(true); return; }
    if (["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) {
      event.preventDefault();
      const index = event.key === "Home" ? 0 : event.key === "End" ? items.length - 1 : (current + (event.key === "ArrowDown" ? 1 : -1) + items.length) % items.length;
      items[index]?.focus();
    }
  }

  function chooseStatus(nextStatus: ListStatus) {
    if (!user) { closeMenu(); setPromptOpen(true); return; }
    mutation.mutate({ kind: "put", anime, body: { status: nextStatus }, status: nextStatus, rating });
    closeMenu(true);
  }

  function remove() {
    if (!user || !status) { closeMenu(); setPromptOpen(true); return; }
    mutation.mutate({ kind: "delete", anime });
    closeMenu(true);
  }

  const listed = status !== null;
  return <>
    <div className={`list-control list-control-${variant}`}>
      <button
        aria-label={listed ? `Change list status for ${anime.title}, ${listStatusLabels[status]}` : `Add ${anime.title} to My list`}
        aria-expanded={open}
        aria-haspopup="menu"
        className={`list-control-trigger${listed ? " is-listed" : ""}`}
        disabled={mutation.isPending || (statusLoading && user !== null)}
        onClick={() => user ? setOpen((value) => !value) : setPromptOpen(true)}
        ref={buttonRef}
        type="button"
      >
        {listed ? <BookmarkCheck aria-hidden="true" fill="currentColor" size={17} /> : <Bookmark aria-hidden="true" size={17} />}
        {variant === "card" && listed && <span>{listStatusLabels[status]}</span>}
        {variant === "detail" && <span>{listed ? listStatusLabels[status] : "Add to My list"}</span>}
      </button>
      {open && <div aria-label={`List status for ${anime.title}`} className="list-status-menu" onKeyDown={onMenuKeyDown} ref={menuRef} role="menu">
        {listStatuses.map((item) => <button aria-checked={status === item} key={item} onClick={() => chooseStatus(item)} role="menuitemradio" type="button">{listStatusLabels[item]}{status === item && <span aria-hidden="true">✓</span>}</button>)}
        {listed && <button className="list-remove-action" onClick={remove} role="menuitem" type="button"><X aria-hidden="true" size={15} />Remove</button>}
      </div>}
    </div>
    {promptOpen && <AuthPrompt nextPath={nextPath} onClose={() => setPromptOpen(false)} />}
  </>;
}

export function ListRatingControl({ anime, status, rating, statusLoading = false }: { anime: AnimeCardData; status: ListStatus | null; rating: number | null; statusLoading?: boolean }) {
  const { user } = useAuth();
  const location = useLocation();
  const mutation = useListMutation();
  const [promptOpen, setPromptOpen] = useState(false);
  const nextPath = safeNextPath(`${location.pathname}${location.search}`, "/browse");
  function rate(value: string) {
    if (!user) { setPromptOpen(true); return; }
    if (statusLoading) return;
    if (!value && status === null) return;
    const nextRating = value ? Number(value) : null;
    const nextStatus = status ?? "completed";
    mutation.mutate({
      kind: "put",
      anime,
      body: nextRating === null ? { rating: null } : { ...(status === null ? { status: "completed" as const } : {}), rating: nextRating },
      status: nextStatus,
      rating: nextRating,
    });
  }
  return <>
    <label className="list-rating-control">
      <span>Your rating</span>
      <select aria-label={`Your rating for ${anime.title}`} disabled={statusLoading && user !== null || mutation.isPending} onChange={(event) => rate(event.target.value)} value={rating ?? ""}>
        <option value="">Not rated</option>
        {Array.from({ length: 10 }, (_, index) => index + 1).map((value) => <option key={value} value={value}>{value} / 10</option>)}
      </select>
    </label>
    {promptOpen && <AuthPrompt nextPath={nextPath} onClose={() => setPromptOpen(false)} />}
  </>;
}

