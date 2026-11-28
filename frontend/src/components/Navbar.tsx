import { useEffect, useRef, useState } from "react";
import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import {
  Bookmark,
  CircleUserRound,
  Eye,
  EyeOff,
  LayoutGrid,
  LogIn,
  LogOut,
  Menu,
  Search,
  Settings,
  X,
  type LucideProps,
} from "lucide-react";
import { useAuth } from "../auth/useAuth";
import { useOptionalToast } from "./useToast";
import { TitleAutocomplete } from "./TitleAutocomplete";
import { AuthPrompt } from "./AuthPrompt";
import { HeaderTabs } from "./HeaderTabs";
import { onMenuKeyDown } from "./menuKeys";

// Custom glyphs from the Penpot design: a TV with a heart, and a choice ballot.
function ForYouIcon({ size = 24, strokeWidth = 1.5, ...props }: LucideProps) {
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
      <rect height="14" rx="2" width="20" x="2" y="7" />
      <path d="M17 2l-5 5-5-5" />
      <path
        d="M14.28 14.68c.48-.47.96-1.03.96-1.76a1.76 1.76 0 0 0-1.76-1.76c-.56 0-.96.16-1.44.64-.48-.48-.88-.64-1.44-.64a1.76 1.76 0 0 0-1.76 1.76c0 .74.48 1.3.96 1.76l2.24 2.24z"
        strokeWidth={4.7}
      />
    </svg>
  );
}

function QuizIcon({ size = 24, strokeWidth = 1.5, ...props }: LucideProps) {
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
      <circle cx="6" cy="7" r="2.5" />
      <circle cx="6" cy="17" r="2.5" />
      <circle cx="6" cy="7" fill="currentColor" r="0.6" />
      <path d="M12 7h9M12 17h9" />
    </svg>
  );
}

export function Navbar() {
  const { user, mature, setMature, signOut } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const { showToast } = useOptionalToast();
  const [menuOpen, setMenuOpen] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [authPromptOpen, setAuthPromptOpen] = useState(false);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const drawerButtonRef = useRef<HTMLButtonElement>(null);
  const drawerRef = useRef<HTMLDivElement>(null);
  const browseLink = {
    to: "/browse",
    label: "Browse",
    className: "browse-link",
    Icon: LayoutGrid,
  };
  const pageLinks = user
    ? [
        browseLink,
        {
          to: "/for-you",
          label: "For you",
          className: "for-you-link",
          Icon: ForYouIcon,
        },
        {
          to: "/list",
          label: "My list",
          className: "my-list-link",
          Icon: Bookmark,
        },
      ]
    : [
        browseLink,
        {
          to: "/quiz",
          label: "Take the quiz",
          className: "quiz-link",
          Icon: QuizIcon,
        },
      ];
  const signInPath = `/login?next=${encodeURIComponent(`${location.pathname}${location.search}`)}`;
  const showSimilarSearch =
    location.pathname === "/browse" ||
    location.pathname === "/for-you" ||
    location.pathname === "/results" ||
    location.pathname.startsWith("/similar/") ||
    location.pathname.startsWith("/anime/");
  useEffect(() => {
    (menuOpen ? menuRef : drawerRef).current
      ?.querySelector<HTMLElement>("[role=menuitem], nav a")
      ?.focus();
  }, [menuOpen, drawerOpen]);
  useEffect(() => {
    if (!menuOpen && !drawerOpen) return;
    function onPointerDown(event: PointerEvent) {
      if (
        !(event.target as Element).closest(".nav-drawer, .account-menu-wrap")
      ) {
        setMenuOpen(false);
        setDrawerOpen(false);
      }
    }
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, [menuOpen, drawerOpen]);
  function closeMenu(restoreFocus = false) {
    setMenuOpen(false);
    if (restoreFocus) buttonRef.current?.focus();
  }
  function closeDrawer(restoreFocus = true) {
    setDrawerOpen(false);
    if (restoreFocus) drawerButtonRef.current?.focus();
  }
  function onDrawerKeyDown(event: React.KeyboardEvent<HTMLDivElement>) {
    if (event.key === "Escape") {
      event.preventDefault();
      closeDrawer();
    }
    if (event.key !== "Tab") return;
    // Keep keyboard focus inside the open drawer.
    const items = Array.from(
      event.currentTarget.querySelectorAll<HTMLElement>(
        "a[href], button, input"
      )
    );
    const first = items[0];
    const last = items[items.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last?.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first?.focus();
    }
  }
  async function handleSignOut() {
    try {
      await signOut();
    } catch {
      /* Local state is cleared even if the server session expired. */
    }
    closeMenu();
    setDrawerOpen(false);
    navigate("/", { replace: true, state: { showHome: true } });
    showToast("You’re signed out", "success");
  }
  return (
    <header className="app-header">
      <div
        className={`header-bar${location.pathname === "/" ? " is-quiet" : ""}`}
      >
        <div className="header-content">
          <button
            aria-controls="nav-drawer"
            aria-expanded={drawerOpen}
            aria-haspopup="dialog"
            aria-label="Menu"
            className="page-menu-button"
            onClick={() => {
              setMenuOpen(false);
              setDrawerOpen(true);
            }}
            ref={drawerButtonRef}
            type="button"
          >
            <Menu aria-hidden="true" size={20} strokeWidth={1.5} />
          </button>
          <Link
            aria-label="AniMatch home"
            className="wordmark"
            state={{ showHome: true }}
            to="/"
          >
            <span>Ani</span>
            <span className="wordmark-accent">Match</span>
          </Link>
          <HeaderTabs pageLinks={pageLinks} quiet={location.pathname === "/"} />
          <nav aria-label="Account" className="header-nav">
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
                      setDrawerOpen(false);
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
                        <Settings
                          aria-hidden="true"
                          size={18}
                          strokeWidth={1.5}
                        />
                        Settings
                      </NavLink>
                      <button
                        onClick={() => void handleSignOut()}
                        role="menuitem"
                        type="button"
                      >
                        <LogOut
                          aria-hidden="true"
                          size={18}
                          strokeWidth={1.5}
                        />
                        Sign out
                      </button>
                    </div>
                  )}
                </div>
                <Link
                  aria-label="Account settings"
                  className="account-menu-button account-settings-link"
                  to="/settings"
                >
                  <CircleUserRound aria-hidden="true" size={22} />
                </Link>
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
                <NavLink className="header-signin" to={signInPath}>
                  Sign in
                </NavLink>
              </>
            )}
          </nav>
        </div>
      </div>
      {showSimilarSearch && (
        <div className="similar-search-bar">
          <div className="similar-search-inner">
            <Search
              aria-hidden="true"
              className="similar-search-icon"
              size={18}
              strokeWidth={1.5}
            />
            <TitleAutocomplete
              includeMature={mature}
              inputLabel="Search anime similar to"
              onSelect={(anime) => navigate(`/similar/${anime.id}`)}
              placeholder="Find anime similar to…"
              selected={[]}
            />
          </div>
        </div>
      )}
      {drawerOpen && (
        <>
          <div aria-hidden="true" className="nav-drawer-scrim" />
          <div
            aria-label="Menu"
            aria-modal="true"
            className="nav-drawer"
            id="nav-drawer"
            onKeyDown={onDrawerKeyDown}
            ref={drawerRef}
            role="dialog"
          >
            <div className="nav-drawer-top">
              <button
                aria-label="Close menu"
                className="page-menu-button"
                onClick={() => closeDrawer()}
                type="button"
              >
                <X aria-hidden="true" size={20} strokeWidth={1.5} />
              </button>
              <Link
                aria-label="AniMatch home"
                className="wordmark"
                onClick={() => closeDrawer(false)}
                state={{ showHome: true }}
                to="/"
              >
                <span>Ani</span>
                <span className="wordmark-accent">Match</span>
              </Link>
            </div>
            <nav aria-label="Pages" className="nav-drawer-links">
              {pageLinks.map((link) => (
                <NavLink
                  className="nav-drawer-row"
                  key={link.to}
                  onClick={() => closeDrawer(false)}
                  to={link.to}
                >
                  <link.Icon aria-hidden="true" size={24} strokeWidth={1.5} />
                  {link.label}
                </NavLink>
              ))}
            </nav>
            <div className="nav-drawer-bottom">
              <hr className="nav-drawer-rule" />
              <div className="nav-drawer-row">
                {mature ? (
                  <Eye aria-hidden="true" size={24} strokeWidth={1.5} />
                ) : (
                  <EyeOff aria-hidden="true" size={24} strokeWidth={1.5} />
                )}
                <label htmlFor="drawer-mature">Mature (18+)</label>
                <input
                  checked={mature}
                  className="switch"
                  id="drawer-mature"
                  onChange={(event) => {
                    if (user) {
                      void setMature(event.target.checked);
                    } else {
                      closeDrawer(false);
                      setAuthPromptOpen(true);
                    }
                  }}
                  role="switch"
                  type="checkbox"
                />
              </div>
              {user ? (
                <>
                  <button
                    className="nav-drawer-row"
                    onClick={() => void handleSignOut()}
                    type="button"
                  >
                    <LogOut
                      aria-hidden="true"
                      className="nav-drawer-icon-sm"
                      size={20}
                      strokeWidth={1.5}
                    />
                    Sign out
                  </button>
                  <hr className="nav-drawer-rule" />
                  <Link
                    className="nav-drawer-profile"
                    onClick={() => closeDrawer(false)}
                    to="/settings"
                  >
                    <span aria-hidden="true" className="nav-drawer-avatar">
                      {user.display_name.trim().charAt(0).toUpperCase()}
                    </span>
                    <span className="nav-drawer-profile-copy">
                      <strong>{user.display_name}</strong>
                      <span>Account settings</span>
                    </span>
                  </Link>
                </>
              ) : (
                <>
                  <hr className="nav-drawer-rule" />
                  <NavLink
                    className="nav-drawer-row"
                    onClick={() => closeDrawer(false)}
                    to={signInPath}
                  >
                    <LogIn
                      aria-hidden="true"
                      className="nav-drawer-icon-sm"
                      size={20}
                      strokeWidth={1.5}
                    />
                    Sign in
                  </NavLink>
                </>
              )}
            </div>
          </div>
        </>
      )}
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
