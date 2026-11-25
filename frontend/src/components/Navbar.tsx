import { useEffect, useRef, useState } from "react";
import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import { CircleUserRound, Menu, Search } from "lucide-react";
import { useAuth } from "../auth/useAuth";
import { useOptionalToast } from "./useToast";
import { TitleAutocomplete } from "./TitleAutocomplete";
import { AuthPrompt } from "./AuthPrompt";

export function Navbar() {
  const { user, mature, setMature, signOut } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const { showToast } = useOptionalToast();
  const [menuOpen, setMenuOpen] = useState(false);
  const [pageMenuOpen, setPageMenuOpen] = useState(false);
  const [authPromptOpen, setAuthPromptOpen] = useState(false);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const pageButtonRef = useRef<HTMLButtonElement>(null);
  const pageMenuRef = useRef<HTMLDivElement>(null);
  const pageLinks = user
    ? [
        { to: "/browse", label: "Browse", className: "browse-link" },
        { to: "/for-you", label: "For you", className: "for-you-link" },
        { to: "/list", label: "My list", className: "my-list-link" },
      ]
    : [
        { to: "/browse", label: "Browse", className: "browse-link" },
        { to: "/quiz", label: "Take the quiz", className: "quiz-link" },
      ];
  const showSimilarSearch =
    location.pathname === "/browse" ||
    location.pathname === "/for-you" ||
    location.pathname === "/results" ||
    location.pathname.startsWith("/similar/") ||
    location.pathname.startsWith("/anime/");
  useEffect(() => {
    (menuOpen ? menuRef : pageMenuRef).current
      ?.querySelector<HTMLElement>("[role=menuitem]")
      ?.focus();
  }, [menuOpen, pageMenuOpen]);
  useEffect(() => {
    if (!menuOpen && !pageMenuOpen) return;
    function onPointerDown(event: PointerEvent) {
      if (
        !(event.target as Element).closest(
          ".page-menu-wrap, .account-menu-wrap"
        )
      ) {
        setMenuOpen(false);
        setPageMenuOpen(false);
      }
    }
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, [menuOpen, pageMenuOpen]);
  function closeMenu(restoreFocus = false) {
    setMenuOpen(false);
    if (restoreFocus) buttonRef.current?.focus();
  }
  function closePageMenu(restoreFocus = false) {
    setPageMenuOpen(false);
    if (restoreFocus) pageButtonRef.current?.focus();
  }
  function onMenuKeyDown(
    event: React.KeyboardEvent<HTMLDivElement>,
    close: (restoreFocus: boolean) => void
  ) {
    const items = Array.from(
      event.currentTarget.querySelectorAll<HTMLElement>("[role=menuitem]")
    );
    const current = items.indexOf(document.activeElement as HTMLElement);
    if (event.key === "Escape") {
      event.preventDefault();
      close(true);
    }
    if (
      event.key === "ArrowDown" ||
      event.key === "ArrowUp" ||
      event.key === "Home" ||
      event.key === "End"
    ) {
      event.preventDefault();
      const next =
        event.key === "Home"
          ? 0
          : event.key === "End"
            ? items.length - 1
            : (current + (event.key === "ArrowDown" ? 1 : -1) + items.length) %
              items.length;
      items[next]?.focus();
    }
  }
  async function handleSignOut() {
    try {
      await signOut();
    } catch {
      /* Local state is cleared even if the server session expired. */
    }
    closeMenu();
    navigate("/", { replace: true, state: { showHome: true } });
    showToast("You’re signed out", "success");
  }
  return (
    <header
      className={`app-header${showSimilarSearch ? " has-similar-search" : ""}`}
    >
      <div
        className={`header-content${showSimilarSearch ? " has-similar-search" : ""}`}
      >
        <div className="page-menu-wrap">
          <button
            aria-label="Pages"
            aria-controls="page-menu"
            aria-expanded={pageMenuOpen}
            aria-haspopup="menu"
            className="page-menu-button"
            onClick={() => {
              setMenuOpen(false);
              setPageMenuOpen((open) => !open);
            }}
            ref={pageButtonRef}
            type="button"
          >
            <Menu aria-hidden="true" size={20} />
          </button>
          {pageMenuOpen && (
            <div
              aria-label="Pages"
              className="account-menu page-menu"
              id="page-menu"
              onKeyDown={(event) => onMenuKeyDown(event, closePageMenu)}
              ref={pageMenuRef}
              role="menu"
            >
              {pageLinks.map((link) => (
                <NavLink
                  key={link.to}
                  onClick={() => closePageMenu()}
                  role="menuitem"
                  to={link.to}
                >
                  {link.label}
                </NavLink>
              ))}
            </div>
          )}
        </div>
        <Link
          aria-label="AniMatch home"
          className="wordmark"
          state={{ showHome: true }}
          to="/"
        >
          <span>Ani</span>
          <span className="wordmark-accent">Match</span>
        </Link>
        {showSimilarSearch && (
          <div className="header-similar-search">
            <Search
              aria-hidden="true"
              className="header-similar-search-icon"
              size={16}
            />
            <TitleAutocomplete
              includeMature={mature}
              inputLabel="Search anime similar to"
              onSelect={(anime) => navigate(`/similar/${anime.id}`)}
              placeholder="Find anime similar to…"
              selected={[]}
            />
          </div>
        )}
        <nav aria-label="Main navigation" className="header-nav">
          {pageLinks.map((link) => (
            <NavLink className={link.className} key={link.to} to={link.to}>
              {link.label}
            </NavLink>
          ))}
          {user ? (
            <>
              <button
                aria-label="Include mature anime"
                aria-pressed={mature}
                className={`mature-toggle${mature ? " is-active" : ""}`}
                onClick={() => void setMature(!mature)}
                title="Show mature content"
                type="button"
              >
                {mature ? "18+ on" : "18+ off"}
              </button>
              <div className="account-menu-wrap">
                <button
                  aria-label="Account menu"
                  aria-controls="account-menu"
                  aria-expanded={menuOpen}
                  aria-haspopup="menu"
                  className="account-menu-button"
                  onClick={() => {
                    setPageMenuOpen(false);
                    setMenuOpen((open) => !open);
                  }}
                  ref={buttonRef}
                  type="button"
                >
                  <CircleUserRound aria-hidden="true" size={22} />
                </button>
                {menuOpen && (
                  <div
                    className="account-menu"
                    id="account-menu"
                    onKeyDown={(event) => onMenuKeyDown(event, closeMenu)}
                    ref={menuRef}
                    role="menu"
                    aria-label="Account"
                  >
                    <NavLink
                      onClick={() => closeMenu()}
                      role="menuitem"
                      to="/settings"
                    >
                      Settings
                    </NavLink>
                    <button
                      onClick={() => void handleSignOut()}
                      role="menuitem"
                      type="button"
                    >
                      Sign out
                    </button>
                  </div>
                )}
              </div>
            </>
          ) : (
            <>
              <button
                aria-label="Include mature anime"
                aria-pressed={mature}
                className={`mature-toggle${mature ? " is-active" : ""}`}
                onClick={() => setAuthPromptOpen(true)}
                title="Show mature content"
                type="button"
              >
                {mature ? "18+ on" : "18+ off"}
              </button>
              <NavLink
                className="header-signin"
                to={`/login?next=${encodeURIComponent(`${location.pathname}${location.search}`)}`}
              >
                Sign in
              </NavLink>
            </>
          )}
        </nav>
      </div>
      {authPromptOpen && (
        <AuthPrompt
          message="Sign in or create an account to view mature anime."
          nextPath={`${location.pathname}${location.search}`}
          onClose={() => setAuthPromptOpen(false)}
          title="Sign in to view 18+ content"
        />
      )}
    </header>
  );
}
