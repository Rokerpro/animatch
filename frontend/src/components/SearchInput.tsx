import { useEffect, useState, type FormEvent } from "react";
import { Search } from "lucide-react";
import { useLocation, useNavigate } from "react-router-dom";

const DEBOUNCE_MS = 300;

export function SearchInput() {
  const location = useLocation();
  const navigate = useNavigate();
  const currentQuery = new URLSearchParams(location.search).get("q") ?? "";
  const [value, setValue] = useState(currentQuery);

  useEffect(() => {
    setValue(currentQuery);
  }, [currentQuery]);

  useEffect(() => {
    const query = value.trim();
    if (query === currentQuery.trim()) return;

    const timer = window.setTimeout(() => {
      const params =
        location.pathname === "/browse"
          ? new URLSearchParams(location.search)
          : new URLSearchParams();

      if (query) params.set("q", query);
      else params.delete("q");

      const search = params.toString();
      navigate(`/browse${search ? `?${search}` : ""}`, { replace: true });
    }, DEBOUNCE_MS);

    return () => window.clearTimeout(timer);
  }, [currentQuery, location.pathname, location.search, navigate, value]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const query = value.trim();
    const params =
      location.pathname === "/browse"
        ? new URLSearchParams(location.search)
        : new URLSearchParams();

    if (query) params.set("q", query);
    else params.delete("q");

    const search = params.toString();
    navigate(`/browse${search ? `?${search}` : ""}`);
  }

  return (
    <form
      className="header-search"
      role="search"
      onSubmit={handleSubmit}
      aria-label="Search anime"
    >
      <Search aria-hidden="true" size={16} />
      <input
        aria-label="Search titles"
        autoComplete="off"
        name="q"
        onChange={(event) => setValue(event.currentTarget.value)}
        placeholder="Search anime"
        type="search"
        value={value}
      />
    </form>
  );
}
