import { useEffect, useId, useRef, useState, type KeyboardEvent } from "react";
import { api } from "../api/client";
import type { AnimeCardData } from "../api/types";

interface TitleAutocompleteProps {
  includeMature: boolean;
  selected: AnimeCardData[];
  inputLabel?: string;
  placeholder?: string;
  disabled?: boolean;
  onSelect: (anime: AnimeCardData) => void;
}

export function TitleAutocomplete({
  includeMature,
  selected,
  inputLabel = "Search anime titles",
  placeholder = "Search anime titles",
  disabled = false,
  onSelect,
}: TitleAutocompleteProps) {
  const listId = useId();
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [results, setResults] = useState<AnimeCardData[]>([]);
  const [loading, setLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [error, setError] = useState(false);
  const [focused, setFocused] = useState(false);
  const [dismissed, setDismissed] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [retryCount, setRetryCount] = useState(0);
  const requestRef = useRef<AbortController | null>(null);
  const selectedIds = new Set(selected.map((anime) => anime.id));
  const atMaximum = selected.length >= 5;
  const inputDisabled = disabled || atMaximum;
  const open =
    focused &&
    Boolean(query.trim()) &&
    !dismissed &&
    (loading || error || hasSearched || results.length > 0);

  useEffect(() => {
    const timeout = window.setTimeout(() => setDebouncedQuery(query.trim()), 300);
    return () => window.clearTimeout(timeout);
  }, [query]);

  useEffect(() => {
    const search = debouncedQuery.trim();
    if (!search || inputDisabled) {
      setResults([]);
      setLoading(false);
      setError(false);
      setHasSearched(false);
      return;
    }

    const controller = new AbortController();
    requestRef.current = controller;
    setLoading(true);
    setError(false);
    setResults([]);
    setActiveIndex(-1);
    void api
      .anime(
        { q: search, page: 1, pageSize: 6, includeMature },
        controller.signal,
      )
      .then((response) => {
        if (!controller.signal.aborted) {
          setResults(response.items);
          setHasSearched(true);
        }
      })
      .catch(() => {
        if (!controller.signal.aborted) setError(true);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => controller.abort();
  }, [debouncedQuery, includeMature, inputDisabled, retryCount]);

  function choose(anime: AnimeCardData) {
    if (inputDisabled || selectedIds.has(anime.id)) return;
    onSelect(anime);
    setQuery("");
    setDebouncedQuery("");
    setResults([]);
    setActiveIndex(-1);
    setDismissed(false);
  }

  function handleChange(value: string) {
    requestRef.current?.abort();
    setLoading(false);
    setHasSearched(false);
    setResults([]);
    setQuery(value);
    setDismissed(false);
    setActiveIndex(-1);
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Enter") {
      event.preventDefault();
      if (open && activeIndex >= 0) choose(results[activeIndex]);
      return;
    }
    if (event.key === "Escape") {
      if (open) {
        event.preventDefault();
        setDismissed(true);
        setActiveIndex(-1);
      }
      return;
    }
    if (!open || results.length === 0) return;
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveIndex((current) => (current + 1) % results.length);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((current) =>
        current <= 0 ? results.length - 1 : current - 1,
      );
    }
  }

  return (
    <div className="title-autocomplete">
      <label className="sr-only" htmlFor={`${listId}-input`}>
        {inputLabel}
      </label>
      <input
        id={`${listId}-input`}
        role="combobox"
        aria-autocomplete="list"
        aria-expanded={open}
        aria-controls={`${listId}-listbox`}
        aria-activedescendant={
          activeIndex >= 0 ? `${listId}-option-${activeIndex}` : undefined
        }
        autoComplete="off"
        disabled={inputDisabled}
        onBlur={() => setFocused(false)}
        onChange={(event) => handleChange(event.target.value)}
        onFocus={() => setFocused(true)}
        onKeyDown={handleKeyDown}
        placeholder={atMaximum ? "Maximum of 5 titles selected" : placeholder}
        type="search"
        value={query}
      />
      {atMaximum && <p className="autocomplete-limit-note">Maximum of 5 titles selected.</p>}
      {open && (
        <div className="autocomplete-popover">
          <ul
            className="autocomplete-options"
            id={`${listId}-listbox`}
            role="listbox"
            aria-label="Anime search results"
          >
            {results.map((anime, index) => {
              const alreadySelected = selectedIds.has(anime.id);
              const metadata = [anime.format, anime.year]
                .filter((value) => value !== null && value !== undefined)
                .join(" · ");
              return (
                <li
                  aria-disabled={alreadySelected}
                  aria-selected={activeIndex === index}
                  className={`autocomplete-option${activeIndex === index ? " is-active" : ""}${alreadySelected ? " is-selected" : ""}`}
                  id={`${listId}-option-${index}`}
                  key={anime.id}
                  onMouseDown={(event) => event.preventDefault()}
                  onClick={() => choose(anime)}
                  role="option"
                >
                  <img alt="" src={anime.coverImage ?? ""} />
                  <span className="autocomplete-option-copy">
                    <span className="autocomplete-option-title">{anime.title}</span>
                    {metadata && <span className="autocomplete-option-meta">{metadata}</span>}
                  </span>
                  {alreadySelected && <span className="autocomplete-added">Added</span>}
                </li>
              );
            })}
          </ul>
          {loading && <p className="autocomplete-status" role="status">Searching…</p>}
          {!loading && !error && results.length === 0 && (
            <p className="autocomplete-status" role="status">No anime found</p>
          )}
          {error && (
            <div className="autocomplete-error" role="alert">
              <span>Could not load anime. Try again.</span>
              <button
                className="text-button"
                onClick={() => {
                  setDismissed(false);
                  setRetryCount((count) => count + 1);
                }}
                type="button"
              >
                Retry
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
