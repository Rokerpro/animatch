import { Link, NavLink } from "react-router-dom";
import { Sparkles } from "lucide-react";
import { useAuth } from "../auth/useAuth";

export function Navbar() {
  const { user, mature, setMature } = useAuth();
  return (
    <header className="app-header">
      <div className="header-content">
        <Link aria-label="AniMatch home" className="wordmark" to="/">
          <span aria-hidden="true" className="wordmark-mark"><Sparkles size={17} strokeWidth={1.8} /></span>
          <span className="wordmark-copy"><span>Ani</span><span className="wordmark-accent">Match</span></span>
        </Link>
        <nav aria-label="Main navigation" className="header-nav">
          <NavLink to="/browse">Browse</NavLink>
          <NavLink to="/quiz">Quiz</NavLink>
          <button
            aria-label="Include mature anime"
            aria-pressed={mature}
            className={`mature-toggle${mature ? " is-active" : ""}`}
            onClick={() => void setMature(!mature)}
            title="Show mature content"
            type="button"
          >
            {mature ? "18+ on" : "18+"}
          </button>
          <NavLink to={user ? "/settings" : "/login"}>{user ? "Settings" : "Sign in"}</NavLink>
        </nav>
      </div>
    </header>
  );
}
