import { Link, NavLink } from "react-router-dom";
import { SearchInput } from "./SearchInput";
import { useAuth } from "../auth/useAuth";

export function Navbar() {
  const { user, mature, setMature } = useAuth();
  return (
    <header className="app-header">
      <div className="header-content">
        <Link aria-label="AniMatch home" className="wordmark" to="/">
          AniMatch
        </Link>
        <SearchInput />
        <nav aria-label="Main navigation" className="header-nav">
          <NavLink to="/browse">Browse</NavLink>
          <label className="header-mature"><input aria-label="Include mature anime" type="checkbox" checked={mature} onChange={(e) => void setMature(e.target.checked)} /> Mature</label>
          <NavLink to={user ? "/settings" : "/login"}>{user ? "Settings" : "Sign in"}</NavLink>
        </nav>
      </div>
    </header>
  );
}
