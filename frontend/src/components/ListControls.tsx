import { useEffect, useRef, useState } from "react";
import {
  Ban,
  Bookmark,
  BookmarkCheck,
  Check,
  Clock,
  Minus,
  Pause,
  Play,
  Plus,
  Trash2,
  X,
  type LucideIcon,
} from "lucide-react";
import { useLocation } from "react-router-dom";
import type { AnimeCardData, ListStatus } from "../api/types";
import { useAuth } from "../auth/useAuth";
import { safeNextPath } from "../auth/nextPath";
import { useListMutation } from "../api/useListMutation";
import { AuthPrompt } from "./AuthPrompt";
import { listStatusLabels, listStatuses } from "./listStatus";

// Exit timing, matching the CSS: buttons leave one by one, then the X flies
// home and becomes the bookmark. "landing" lets the real bookmark fade in
// underneath before the menu unmounts.
const EXIT_MS = 780;
const LANDING_MS = 200;

const statusIcons: Record<ListStatus, LucideIcon> = {
  planning: Clock,
  watching: Play,
  completed: Check,
  dropped: Ban,
  on_hold: Pause,
};

export function ListControl({
  anime,
  status,
  rating,
  statusLoading = false,
  variant = "card",
}: {
  anime: AnimeCardData;
  status: ListStatus | null;
  rating: number | null;
  statusLoading?: boolean;
  variant?: "card" | "detail";
}) {
  const { user } = useAuth();
  const location = useLocation();
  const mutation = useListMutation();
  const [open, setOpen] = useState(false);
  const [exit, setExit] = useState<"none" | "closing" | "landing">("none");
  const wasOpen = useRef(false);
  const [promptOpen, setPromptOpen] = useState(false);
  const [hovered, setHovered] = useState<string | null>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const radial = variant === "card";
  const nextPath = safeNextPath(
    `${location.pathname}${location.search}`,
    "/browse"
  );

  useEffect(() => {
    if (open) {
      wasOpen.current = true;
      setExit("none");
      return;
    }
    if (!wasOpen.current) return;
    wasOpen.current = false;
    const reduced = window.matchMedia?.(
      "(prefers-reduced-motion: reduce)"
    ).matches;
    setExit("closing");
    const land = setTimeout(() => setExit("landing"), reduced ? 0 : EXIT_MS);
    const done = setTimeout(
      () => setExit("none"),
      reduced ? 0 : EXIT_MS + LANDING_MS
    );
    return () => {
      clearTimeout(land);
      clearTimeout(done);
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const menu = menuRef.current;
    (
      menu?.querySelector<HTMLElement>("[aria-checked='true']") ??
      menu?.querySelector<HTMLElement>(
        "[role='menuitemradio'], [role='menuitem']"
      )
    )?.focus();
    function onPointerDown(event: PointerEvent) {
      if (!menuRef.current?.parentElement?.contains(event.target as Node))
        setOpen(false);
    }
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, [open]);

  function closeMenu(restoreFocus = false) {
    setOpen(false);
    setHovered(null);
    if (restoreFocus) buttonRef.current?.focus();
  }

  function onMenuKeyDown(event: React.KeyboardEvent<HTMLDivElement>) {
    const items = Array.from(
      menuRef.current?.querySelectorAll<HTMLElement>(
        "[role='menuitemradio'], [role='menuitem']"
      ) ?? []
    );
    const current = items.indexOf(document.activeElement as HTMLElement);
    if (event.key === "Escape") {
      event.preventDefault();
      closeMenu(true);
      return;
    }
    const forward = event.key === "ArrowDown" || event.key === "ArrowRight";
    const back = event.key === "ArrowUp" || event.key === "ArrowLeft";
    if (forward || back || event.key === "Home" || event.key === "End") {
      event.preventDefault();
      const index =
        event.key === "Home"
          ? 0
          : event.key === "End"
            ? items.length - 1
            : (current + (forward ? 1 : -1) + items.length) % items.length;
      items[index]?.focus();
    }
  }

  function chooseStatus(nextStatus: ListStatus) {
    if (!user) {
      closeMenu();
      setPromptOpen(true);
      return;
    }
    mutation.mutate({
      kind: "put",
      anime,
      body: { status: nextStatus },
      status: nextStatus,
      rating,
    });
    closeMenu(true);
  }

  function remove() {
    if (!user || !status) {
      closeMenu();
      setPromptOpen(true);
      return;
    }
    mutation.mutate({ kind: "delete", anime });
    closeMenu(true);
  }

  const listed = status !== null;
  const BookmarkIcon = listed ? BookmarkCheck : Bookmark;
  const radialLabel = hovered ?? (listed ? listStatusLabels[status] : null);
  return (
    <>
      <div className={`list-control list-control-${variant}`}>
        <button
          aria-label={
            listed
              ? `Change list status for ${anime.title}, ${listStatusLabels[status]}`
              : `Add ${anime.title} to My list`
          }
          aria-expanded={open}
          aria-haspopup="menu"
          className={`list-control-trigger${listed ? " is-listed" : ""}${
            radial && (open || exit === "closing") ? " is-hidden" : ""
          }`}
          disabled={mutation.isPending || (statusLoading && user !== null)}
          onClick={() =>
            user ? setOpen((value) => !value) : setPromptOpen(true)
          }
          ref={buttonRef}
          type="button"
        >
          <BookmarkIcon aria-hidden="true" size={18} strokeWidth={1.8} />
          {variant === "detail" && (
            <span>{listed ? listStatusLabels[status] : "Add to My list"}</span>
          )}
        </button>
        {open && !radial && (
          <div
            aria-label={`List status for ${anime.title}`}
            className="list-status-menu"
            onKeyDown={onMenuKeyDown}
            ref={menuRef}
            role="menu"
          >
            {listStatuses.map((item) => (
              <button
                aria-checked={status === item}
                key={item}
                onClick={() => chooseStatus(item)}
                role="menuitemradio"
                type="button"
              >
                {listStatusLabels[item]}
                {status === item && <span aria-hidden="true">✓</span>}
              </button>
            ))}
            {listed && (
              <button
                className="list-remove-action"
                onClick={remove}
                role="menuitem"
                type="button"
              >
                <X aria-hidden="true" size={15} />
                Remove
              </button>
            )}
          </div>
        )}
        {(open || exit !== "none") && radial && (
          <div
            className={`list-radial${open ? "" : " is-closing"}`}
            style={{ "--n": listed ? 6 : 5 } as React.CSSProperties}
          >
            <div
              aria-hidden="true"
              className="list-radial-scrim"
              onClick={() => closeMenu(true)}
            />
            <span aria-hidden="true" className="list-radial-ring" />
            <div
              aria-label={`List status for ${anime.title}`}
              onKeyDown={onMenuKeyDown}
              ref={menuRef}
              role="menu"
            >
              {[...listStatuses, ...(listed ? ["remove" as const] : [])].map(
                (item, index, items) => {
                  const Icon = item === "remove" ? Trash2 : statusIcons[item];
                  const label =
                    item === "remove" ? "Remove" : listStatusLabels[item];
                  return (
                    <button
                      aria-checked={
                        item === "remove" ? undefined : status === item
                      }
                      aria-label={label}
                      className="list-radial-item"
                      key={item}
                      onBlur={() => setHovered(null)}
                      onClick={() =>
                        item === "remove" ? remove() : chooseStatus(item)
                      }
                      onFocus={() => setHovered(label)}
                      onMouseEnter={() => setHovered(label)}
                      onMouseLeave={() => setHovered(null)}
                      role={item === "remove" ? "menuitem" : "menuitemradio"}
                      style={
                        {
                          "--angle": `${(360 / items.length) * index}deg`,
                          "--i": index,
                        } as React.CSSProperties
                      }
                      type="button"
                    >
                      <Icon aria-hidden="true" size={20} strokeWidth={1.5} />
                    </button>
                  );
                }
              )}
            </div>
            <button
              aria-label="Close list menu"
              className={`list-radial-close${listed ? " is-listed" : ""}`}
              onClick={() => closeMenu(true)}
              type="button"
            >
              <X aria-hidden="true" size={22} strokeWidth={1.5} />
              {/* Drawn at 24/2.4 so it matches the 18px trigger icon at 0.75 scale. */}
              <BookmarkIcon
                aria-hidden="true"
                className="list-radial-home-icon"
                size={24}
                strokeWidth={2.4}
              />
            </button>
            {/* The slot delays the label on open; the keyed label animates
                each time its text changes. */}
            <span aria-hidden="true" className="list-radial-label-slot">
              {radialLabel && (
                <span className="list-radial-label" key={radialLabel}>
                  {radialLabel}
                </span>
              )}
            </span>
          </div>
        )}
      </div>
      {promptOpen && (
        <AuthPrompt nextPath={nextPath} onClose={() => setPromptOpen(false)} />
      )}
    </>
  );
}

export function ListRatingControl({
  anime,
  status,
  rating,
  statusLoading = false,
}: {
  anime: AnimeCardData;
  status: ListStatus | null;
  rating: number | null;
  statusLoading?: boolean;
}) {
  const { user } = useAuth();
  const location = useLocation();
  const mutation = useListMutation();
  const [promptOpen, setPromptOpen] = useState(false);
  const nextPath = safeNextPath(
    `${location.pathname}${location.search}`,
    "/browse"
  );
  function rate(value: string) {
    if (!user) {
      setPromptOpen(true);
      return;
    }
    if (statusLoading) return;
    if (!value && status === null) return;
    const nextRating = value ? Number(value) : null;
    const nextStatus = status ?? "completed";
    mutation.mutate({
      kind: "put",
      anime,
      body:
        nextRating === null
          ? { rating: null }
          : {
              ...(status === null ? { status: "completed" as const } : {}),
              rating: nextRating,
            },
      status: nextStatus,
      rating: nextRating,
    });
  }
  return (
    <>
      <label className="list-rating-control">
        <span>Your rating</span>
        <select
          aria-label={`Your rating for ${anime.title}`}
          disabled={(statusLoading && user !== null) || mutation.isPending}
          onChange={(event) => rate(event.target.value)}
          value={rating ?? ""}
        >
          <option value="">Not rated</option>
          {Array.from({ length: 10 }, (_, index) => index + 1).map((value) => (
            <option key={value} value={value}>
              {value} / 10
            </option>
          ))}
        </select>
      </label>
      {promptOpen && (
        <AuthPrompt nextPath={nextPath} onClose={() => setPromptOpen(false)} />
      )}
    </>
  );
}

export function ListProgressControl({
  anime,
  status,
  rating,
  progress,
}: {
  anime: AnimeCardData;
  status: ListStatus;
  rating: number | null;
  progress: number;
}) {
  const mutation = useListMutation();
  const total = anime.episodes ?? null;
  function step(delta: number) {
    const next = progress + delta;
    mutation.mutate({
      kind: "put",
      anime,
      body: { progress: next },
      status,
      rating,
      progress: next,
    });
  }
  return (
    <div className="list-progress-control">
      <span>Episodes</span>
      <button
        aria-label={`One fewer episode watched of ${anime.title}`}
        disabled={mutation.isPending || progress <= 0}
        onClick={() => step(-1)}
        type="button"
      >
        <Minus aria-hidden="true" size={14} />
      </button>
      <output aria-label={`Episodes watched of ${anime.title}`}>
        {progress} / {total ?? "?"}
      </output>
      <button
        aria-label={`One more episode watched of ${anime.title}`}
        disabled={mutation.isPending || (total !== null && progress >= total)}
        onClick={() => step(1)}
        type="button"
      >
        <Plus aria-hidden="true" size={14} />
      </button>
    </div>
  );
}
