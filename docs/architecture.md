# AniMatch Architecture Documentation

This directory contains architecture decisions, database schema design, and API documentation for AniMatch.

- **Phase 1**: Scaffold, directory structure, tooling, and health checks.
- **Phase 2**: Database schema, catalog synchronization CLI, and repository pattern.
- **Phase 3**: User authentication (Email/Password + Google OAuth).
- **Phase 4**: Hybrid recommendation engine.
- **Phase 5**: Frontend catalog browse and search.
- **Phase 6**: User profiles, watchlists, and rating systems.
- **Phase 7**: MyAnimeList import workflows (Jikan API & XML upload).
- **Phase 8**: Find something new recommendations based on a short quiz and the user's list and taste profile.
- **Phase 9**: Gemini LLM natural language parsing.
- **Phase 10**: Returning-user homepage and UX polish.
- **Phase 11**: Hardening, security auditing, and deployment ([Phase 11 Notes](phase11_notes.md)).

## Natural-language recommendations (Phase 9)

`GET /api/features` reports whether the natural-language request box can be
shown. Authenticated requests to `POST /api/recs/ask` are translated by Gemini
into existing quiz answers and up to five catalog title seeds. Only validated
inputs reach the existing recommendation engine; Gemini does not rank or choose
recommendations. Usage is counted per user and UTC day in
`natural_language_usage`, with the limit configurable through
`NL_DAILY_LIMIT`. Provider failures return a generic service error without
provider response details.

## Mature-content visibility

The server hides a title when AniList marks the title `isAdult`, when it has the
Hentai or Ecchi genre, or when it has an adult-flagged tag whose per-title
`anime_tags.rank` is at least `MATURE_TAG_MIN_RANK` (default `60`, an integer
percentage). The first two title/genre rules are unconditional. This setting
changes visibility everywhere that applies the mature-content toggle, including
browse, filters, detail, lists, and recommendation seeds/results. Adult-flagged
tag names remain excluded from the tag vocabulary while mature content is off.

