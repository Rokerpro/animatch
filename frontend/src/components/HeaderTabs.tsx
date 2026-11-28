import { useEffect, useRef, useState, type ComponentType } from "react";
import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import { X, type LucideProps } from "lucide-react";
import { useAnimeDetail } from "../api/hooks";
import { useAuth } from "../auth/useAuth";
import { onMenuKeyDown } from "./menuKeys";

export type PageLink = {
  to: string;
  label: string;
  className: string;
  Icon: ComponentType<LucideProps>;
};

type OpenTab = {
  path: string;
  kind: "anime" | "similar" | "matches";
  title: string;
  coverImage?: string | null;
  coverColor?: string | null;
  isAdult?: boolean;
};

const STORAGE_KEY = "animatch.openTabs";
const MAX_TABS = 8;

function tabForPath(path: string): Pick<OpenTab, "path" | "kind"> | null {
  if (/^\/anime\/\d+$/.test(path)) return { path, kind: "anime" };
  if (/^\/similar\/\d+$/.test(path)) return { path, kind: "similar" };
  if (path === "/results") return { path, kind: "matches" };
  return null;
}

const placeholderTitles: Record<OpenTab["kind"], string> = {
  anime: "Anime",
  similar: "Similar anime",
  matches: "Your matches",
};

function readTabs(): OpenTab[] {
  try {
    const saved: unknown = JSON.parse(
      localStorage.getItem(STORAGE_KEY) ?? "[]"
    );
    if (!Array.isArray(saved)) return [];
    // Saved data is untrusted: keep only entries whose path is a tab route.
    return saved.filter(
      (tab): tab is OpenTab =>
        typeof tab?.path === "string" &&
        tabForPath(tab.path)?.kind === tab.kind &&
        typeof tab.title === "string"
    );
  } catch {
    return [];
  }
}

function OverlapIcon({ size = 24, strokeWidth = 1.5, ...props }: LucideProps) {
  return (
    <svg
      fill="none"
      height={size}
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={strokeWidth}
      viewBox="0 0 24 24"
      width={size}
      {...props}
    >
      <circle cx="9" cy="12" r="6" />
      <circle cx="15" cy="12" r="6" />
    </svg>
  );
}

function TabsIcon({ size = 24, strokeWidth = 1.5, ...props }: LucideProps) {
  return (
    <svg
      fill="none"
      height={size}
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={strokeWidth}
      viewBox="0 0 24 24"
      width={size}
      {...props}
    >
      <path d="M7.5 3h9" />
      <rect height="13.5" rx="3" width="18" x="3" y="7.5" />
    </svg>
  );
}

function TabThumb({ tab }: { tab: OpenTab }) {
  return tab.kind === "matches" ? (
    <OverlapIcon aria-hidden="true" size={18} />
  ) : (
    <span
      aria-hidden="true"
      className="header-tab-thumb"
      style={{
        backgroundColor: tab.coverColor ?? undefined,
        backgroundImage: tab.coverImage
          ? `url("${encodeURI(tab.coverImage)}")`
          : undefined,
      }}
    />
  );
}

/** Home page header: the open tabs fold into one "Your tabs" menu. */
function TabsMenu({
  pageLinks,
  tabs,
}: {
  pageLinks: PageLink[];
  tabs: OpenTab[];
}) {
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    wrapRef.current?.querySelector<HTMLElement>("[role=menuitem]")?.focus();
    function onPointerDown(event: PointerEvent) {
      if (!wrapRef.current?.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, [open]);

  function close(restoreFocus: boolean) {
    setOpen(false);
    if (restoreFocus) buttonRef.current?.focus();
  }

  return (
    <div className="tabs-menu-wrap" ref={wrapRef}>
      <button
        aria-controls="tabs-menu"
        aria-expanded={open}
        aria-haspopup="menu"
        className="tabs-menu-button"
        onClick={() => setOpen((value) => !value)}
        ref={buttonRef}
        type="button"
      >
        <TabsIcon aria-hidden="true" size={16} />
        Your tabs
        <span className="tabs-menu-count">
          {pageLinks.length + tabs.length}
        </span>
      </button>
      {open && (
        <div
          aria-label="Your tabs"
          className="account-menu tabs-menu"
          id="tabs-menu"
          onKeyDown={(event) => onMenuKeyDown(event, close)}
          role="menu"
        >
          {pageLinks.map((link) => (
            <Link
              key={link.to}
              onClick={() => close(false)}
              role="menuitem"
              to={link.to}
            >
              <link.Icon aria-hidden="true" size={18} strokeWidth={1.5} />
              {link.label}
            </Link>
          ))}
          {tabs.length > 0 && (
            <span aria-hidden="true" className="tabs-menu-divider" />
          )}
          {tabs.map((tab) => (
            <Link
              key={tab.path}
              onClick={() => close(false)}
              role="menuitem"
              to={tab.path}
            >
              <TabThumb tab={tab} />
              <span className="header-tab-title">{tab.title}</span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

export function HeaderTabs({
  pageLinks,
  quiet = false,
}: {
  pageLinks: PageLink[];
  quiet?: boolean;
}) {
  const { mature } = useAuth();
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const [tabs, setTabs] = useState<OpenTab[]>(readTabs);
  const current = tabForPath(pathname);
  const animeId =
    current && current.kind !== "matches" ? Number(pathname.split("/")[2]) : 0;
  const detail = useAnimeDetail(animeId, mature, animeId > 0);
  const visitedPath = useRef<string | null>(null);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(tabs));
    } catch {
      /* Tabs still work for this visit without storage. */
    }
  }, [tabs]);

  // Open a tab for the current page, and fill in its title once known.
  const anime = detail.data;
  useEffect(() => {
    // Only arriving at a page opens its tab, so a tab closed while the
    // navigation away is still pending is not added straight back.
    const arrived = visitedPath.current !== pathname;
    visitedPath.current = pathname;
    if (!current) return;
    const known =
      current.kind === "matches"
        ? { title: placeholderTitles.matches }
        : anime && {
            title:
              current.kind === "similar" ? `Like ${anime.title}` : anime.title,
            coverImage: anime.coverImage,
            coverColor: anime.coverColor,
            isAdult: anime.isAdult,
          };
    setTabs((open) => {
      const existing = open.find((tab) => tab.path === current.path);
      if (existing) {
        if (!known || existing.title === known.title) return open;
        return open.map((tab) =>
          tab.path === current.path ? { ...tab, ...known } : tab
        );
      }
      if (!arrived) return open;
      const added: OpenTab = {
        ...current,
        title: placeholderTitles[current.kind],
        ...known,
      };
      // shortcut: drop the oldest tabs past MAX_TABS; raise it if people ask.
      return [...open, added].slice(-MAX_TABS);
    });
    // `current` is derived from pathname, which the dependency covers.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname, anime]);

  // Adult titles stay out of the header unless mature content is on.
  const visible = tabs.filter((tab) => mature || !tab.isAdult);

  function closeTab(path: string) {
    const index = visible.findIndex((tab) => tab.path === path);
    setTabs((open) => open.filter((tab) => tab.path !== path));
    if (path !== pathname) return;
    const next = visible[index + 1] ?? visible[index - 1];
    navigate(next ? next.path : "/browse");
  }

  if (quiet) return <TabsMenu pageLinks={pageLinks} tabs={visible} />;
  return (
    <nav aria-label="Main navigation" className="header-tabs">
      {pageLinks.map((link) => (
        <NavLink
          className={`header-tab ${link.className}`}
          key={link.to}
          to={link.to}
        >
          <link.Icon aria-hidden="true" size={18} strokeWidth={1.5} />
          {link.label}
        </NavLink>
      ))}
      {visible.length > 0 && (
        <span aria-hidden="true" className="header-tabs-divider" />
      )}
      {visible.map((tab) => {
        const active = tab.path === pathname;
        return (
          <div
            className={`header-tab header-open-tab${active ? " active" : ""}`}
            key={tab.path}
          >
            <Link
              aria-current={active ? "page" : undefined}
              className="header-open-tab-link"
              title={tab.title}
              to={tab.path}
            >
              <TabThumb tab={tab} />
              <span className="header-tab-title">{tab.title}</span>
            </Link>
            <button
              aria-label={`Close ${tab.title}`}
              className="header-tab-close"
              onClick={() => closeTab(tab.path)}
              type="button"
            >
              <X aria-hidden="true" size={16} strokeWidth={1.5} />
            </button>
          </div>
        );
      })}
    </nav>
  );
}
