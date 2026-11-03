import { useState } from "react";
import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import { Search, Sparkles } from "lucide-react";
import { useAuth } from "../auth/useAuth";
import { TitleAutocomplete } from "./TitleAutocomplete";
import { AuthPrompt } from "./AuthPrompt";

export function Navbar() {
  const { user, mature, setMature } = useAuth();
  const location = useLocation(); const [authPromptOpen, setAuthPromptOpen] = useState(false);
  const navigate = useNavigate();
  const showSimilarSearch =
    location.pathname === "/results" ||
    location.pathname.startsWith("/similar/") ||
    location.pathname.startsWith("/anime/");
  return (
    <header className={`app-header${showSimilarSearch ? " has-similar-search" : ""}`}>
      <div className={`header-content${showSimilarSearch ? " has-similar-search" : ""}`}>
        <Link aria-label="AniMatch home" className="wordmark" state={{ showHome: true }} to="/">
          <span aria-hidden="true" className="wordmark-mark"><Sparkles size={17} strokeWidth={1.8} /></span>
          <span className="wordmark-copy"><span>Ani</span><span className="wordmark-accent">Match</span></span>
        </Link>
        {showSimilarSearch && (
          <div className="header-similar-search">
            <Search aria-hidden="true" className="header-similar-search-icon" size={16} />
            <TitleAutocomplete
              includeMature={mature}
              inputLabel="Search anime similar to"
              onSelect={(anime) => navigate(`/similar/${anime.id}`)}
              placeholder="Search anime similar to…"
              selected={[]}
            />
          </div>
        )}
        <nav aria-label="Main navigation" className="header-nav">
          <NavLink end to="/quiz">Retake the quiz</NavLink>
          <button
            aria-label="Include mature anime"
            aria-pressed={mature}
            className={`mature-toggle${mature ? " is-active" : ""}`}
            onClick={() => { if (!user) setAuthPromptOpen(true); else void setMature(!mature); }}
            title="Show mature content"
            type="button"
          >
            {mature ? "18+ on" : "18+"}
          </button>
          <NavLink to={user ? "/settings" : "/login"}>{user ? "Settings" : "Sign in"}</NavLink>
        </nav>
      </div>
      {authPromptOpen && <AuthPrompt nextPath={`${location.pathname}${location.search}`} onClose={() => setAuthPromptOpen(false)} />}
    </header>
  );
}
