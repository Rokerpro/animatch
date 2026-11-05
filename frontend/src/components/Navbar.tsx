import { useEffect, useRef, useState } from "react";
import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import { CircleUserRound, Search, Sparkles } from "lucide-react";
import { useAuth } from "../auth/useAuth";
import { useOptionalToast } from "./useToast";
import { TitleAutocomplete } from "./TitleAutocomplete";
import { AuthPrompt } from "./AuthPrompt";

export function Navbar() {
  const { user, mature, setMature, signOut } = useAuth();
  const location = useLocation(); const navigate = useNavigate(); const { showToast } = useOptionalToast();
  const [menuOpen, setMenuOpen] = useState(false);
  const [authPromptOpen, setAuthPromptOpen] = useState(false);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const showSimilarSearch = location.pathname === "/results" || location.pathname.startsWith("/similar/") || location.pathname.startsWith("/anime/");
  useEffect(() => {
    if (menuOpen) menuRef.current?.querySelector<HTMLElement>("a:not(.account-mobile-link)[role=menuitem]")?.focus();
  }, [menuOpen]);
  function closeMenu(restoreFocus = false) {
    setMenuOpen(false);
    if (restoreFocus) buttonRef.current?.focus();
  }
  function onMenuKeyDown(event: React.KeyboardEvent<HTMLDivElement>) {
    const items = Array.from(menuRef.current?.querySelectorAll<HTMLElement>("[role=menuitem]") ?? []).filter((item) => window.getComputedStyle(item).display !== "none");
    const current = items.indexOf(document.activeElement as HTMLElement);
    if (event.key === "Escape") { event.preventDefault(); closeMenu(true); }
    if (event.key === "ArrowDown" || event.key === "ArrowUp" || event.key === "Home" || event.key === "End") {
      event.preventDefault();
      const next = event.key === "Home" ? 0 : event.key === "End" ? items.length - 1 : (current + (event.key === "ArrowDown" ? 1 : -1) + items.length) % items.length;
      items[next]?.focus();
    }
  }
  async function handleSignOut() {
    try { await signOut(); } catch { /* Local state is cleared even if the server session expired. */ }
    closeMenu(); navigate("/", { replace: true, state: { showHome: true } }); showToast("You’re signed out", "success");
  }
  return <header className={`app-header${showSimilarSearch ? " has-similar-search" : ""}`}>
    <div className={`header-content${showSimilarSearch ? " has-similar-search" : ""}`}>
      <Link aria-label="AniMatch home" className="wordmark" state={{ showHome: true }} to="/">
        <span aria-hidden="true" className="wordmark-mark"><Sparkles size={17} strokeWidth={1.8} /></span>
        <span className="wordmark-copy"><span>Ani</span><span className="wordmark-accent">Match</span></span>
      </Link>
      {showSimilarSearch && <div className="header-similar-search"><Search aria-hidden="true" className="header-similar-search-icon" size={16} /><TitleAutocomplete includeMature={mature} inputLabel="Search anime similar to" onSelect={(anime) => navigate(`/similar/${anime.id}`)} placeholder="Search anime similar to…" selected={[]} /></div>}
      <nav aria-label="Main navigation" className="header-nav">
        {user ? <>
          <NavLink className="browse-anime-link" to="/browse">Browse</NavLink>
          <NavLink className="for-you-link" to="/for-you">For you</NavLink>
          <button aria-label="Include mature anime" aria-pressed={mature} className={`mature-toggle${mature ? " is-active" : ""}`} onClick={() => void setMature(!mature)} title="Show mature content" type="button">{mature ? "18+ on" : "18+"}</button>
          <div className="account-menu-wrap">
            <button aria-label="Account menu" aria-controls="account-menu" aria-expanded={menuOpen} aria-haspopup="menu" className="account-menu-button" onClick={() => setMenuOpen((open) => !open)} ref={buttonRef} type="button"><CircleUserRound aria-hidden="true" size={22} /></button>
            {menuOpen && <div className="account-menu" id="account-menu" onKeyDown={onMenuKeyDown} ref={menuRef} role="menu" aria-label="Account">
              <NavLink className="account-mobile-link browse-mobile-link" onClick={() => closeMenu()} role="menuitem" to="/browse">Browse</NavLink>
              <NavLink className="account-mobile-link" onClick={() => closeMenu()} role="menuitem" to="/for-you">For you</NavLink>
              <NavLink onClick={() => closeMenu()} role="menuitem" to="/settings">Settings</NavLink>
              <button onClick={() => void handleSignOut()} role="menuitem" type="button">Sign out</button>
            </div>}
          </div>
        </> : <>
          <Link to="/quiz">Get started</Link>
          <button aria-label="Include mature anime" aria-pressed={mature} className={`mature-toggle${mature ? " is-active" : ""}`} onClick={() => setAuthPromptOpen(true)} title="Show mature content" type="button">{mature ? "18+ on" : "18+"}</button>
          <NavLink to={`/login?next=${encodeURIComponent(`${location.pathname}${location.search}`)}`}>Sign in</NavLink>
        </>}
      </nav>
    </div>
    {authPromptOpen && <AuthPrompt nextPath={`${location.pathname}${location.search}`} onClose={() => setAuthPromptOpen(false)} />}
  </header>;
}
