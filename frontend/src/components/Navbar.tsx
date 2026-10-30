import { Link, NavLink } from "react-router-dom";
import { useAuth } from "../auth/useAuth";

export function Navbar() {
  const { user, mature, setMature } = useAuth();
  return (
    <header className="app-header">
      <div className="header-content">
        <Link aria-label="AniMatch home" className="wordmark" to="/">
          <span aria-hidden="true" className="wordmark-mark">
            <svg viewBox="0 0 24 24" fill="none">
              <path d="M12 2.75 14.2 9.8 21.25 12l-7.05 2.2L12 21.25 9.8 14.2 2.75 12 9.8 9.8 12 2.75Z" />
              <path d="m19 2 .85 2.15L22 5l-2.15.85L19 8l-.85-2.15L16 5l2.15-.85L19 2Z" />
            </svg>
          </span>
          <span>Ani<span className="wordmark-accent">Match</span></span>
        </Link>
        <nav aria-label="Main navigation" className="header-nav">
          <NavLink to="/browse">Browse</NavLink>
          <button
            aria-label="Include mature anime"
            aria-pressed={mature}
            className={`mature-toggle${mature ? " is-active" : ""}`}
            onClick={() => void setMature(!mature)}
            title={mature ? "Mature content enabled" : "Mature content disabled"}
            type="button"
          >
            18+
          </button>
          <NavLink to={user ? "/settings" : "/login"}>{user ? "Settings" : "Sign in"}</NavLink>
        </nav>
      </div>
    </header>
  );
}
