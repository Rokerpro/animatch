# AniMatch – Phase 5 Approved Design

> **Status**: Approved. Build begins after Phase 4 is complete.  
> **Reference tone**: AniList / Letterboxd — content first, chrome minimal.

---

## Phase 5 initial design rules (superseded where Visual direction v2 differs)

1. **Superseded by Visual direction v2 below:** the earlier bans on gradient text, glow, icon-in-rounded-square tiles, and pill badges no longer apply. Glassmorphism and marketing taglines remain disallowed.
2. Cover art remains a strong visual element. Browse and recommendation results use dense poster grids; the v2 landing hero is an explicit exception.
3. Follow the slightly raised surfaces, soft borders, rounded corners, and restrained shadows in Visual direction v2.
4. Use the shared accent and content tokens defined in `frontend/tailwind.config.js`.
5. Keep card titles compact and show real data (score, year, format, episodes) where available.
6. The plain-text gradient wordmark with a sparkle tile is specified in Visual direction v2 and supersedes the earlier plain single-color wordmark.
7. Use the shared muted content token for secondary metadata.

---

## Visual direction v2 (supersedes earlier flat/minimal corrections)

This section supersedes earlier flat/minimal corrections, including the bans on gradient text, icon tiles, pill badges, and glow. The v2 direction applies consistently to Landing, Browse, Quiz, Results, Similar rows, Detail, Login, Register, and Settings. It changes styling only; it does not authorize layout, route, API, or behavior changes.

- Use a near-black page surface with a large violet radial glow near the top (17% opacity at its center); keep the rest of the background quiet. The `accent.glow` value lives in `frontend/tailwind.config.js`.
- Use violet for fills, borders, and focus rings, and lighter violet text for small text on dark surfaces.
- Render the wordmark as near-white “Ani” and gradient “Match” beside a small bordered rounded-square sparkle tile.
- Keep the header to the wordmark, Browse, Quiz, the existing 18+ toggle, and Sign in. Do not add a search box.
- Center the landing hero with an outlined pill badge, a large two-tone AniMatch heading, truthful functional subtitle, filled Start quiz button, and ghost Skip to Browse button.
- Use slightly raised dark cards and panels with soft borders, rounded corners, and optional rounded icon tiles. Use violet focus rings.
- Keep quiz questions in a centered rounded card with a progress pill and large rounded answer controls. Preserve the existing API-driven single/multi selection behavior.
- Keep poster art dominant, sharp at 2:3, with softly rounded corners, a rounded score pill, title, muted metadata, and real API reason text in lighter violet, 12 px, clamped to three lines.
- Use tinted rounded status boxes, red for errors and green for success, with icons.
- Use 150–200 ms transitions, preserve visible keyboard focus, and respect `prefers-reduced-motion`. Do not use backdrop blur on poster grids or long lists.
- The hero subtitle must say recommendations come from quiz answers and that the quiz takes about a minute. Do not claim features that do not exist.

### Canonical theme tokens

All color tokens are defined once in `frontend/tailwind.config.js`; CSS consumes those values through Tailwind's `theme()` function. Do not duplicate token values in CSS or this document. The config includes page, raised, overlay, and border surfaces; UI, hover, text, gradient-start/end and subtle accents; primary, secondary and muted content; high/mid/low score colors; and error/success status colors. Keep the existing semantic names in sync with their documented uses above.

## Colour Tokens (Tailwind)

See `frontend/tailwind.config.js` for the canonical token values. CSS and utility classes must reference the same token definitions rather than maintaining a second palette.

---

## Global Layout

### Header (v2)
- Use the shared header described in Visual direction v2: sparkle tile and two-tone wordmark, Browse, Quiz, existing 18+ toggle, and Sign in/Settings. No search box.

### Filter Bar (sticky below header, 44 px, desktop)
Supported filters match the Phase 2 API exactly:

| Filter | Control | API param |
|--------|---------|-----------|
| Search | Text input in Browse filters (not the header) | `q` |
| Genre | Multi-select dropdown | `genres[]` |
| Tags | Multi-select dropdown | `tags[]` |
| Format | Segmented toggle: All / TV / Movie / OVA / ONA / Special | `format` |
| Year | Dual-number range inputs | `yearMin`, `yearMax` |
| Min Score | Numeric input (0–100) | `minScore` |
| Max Episodes | Numeric input | `maxEpisodes` |
| Status | Dropdown: All / Finished / Releasing / Upcoming | `status` |
| Sort | Dropdown: Popularity / Score / Newest / Title | `sort` |

**No** season selector. **No** "Recently Added" option.

Active filter has `accent.ui` border and `accent.text` label.

**Mobile**: All filters collapsed behind a **Filters** button that opens a full-width drawer from the bottom. Active filter count shown as a plain number badge on the button.

---

## Browse Page

### Poster Grid
- **Columns**: 7 (≥ 1400 px), 6 (≥ 1200 px), 5 (≥ 960 px), 4 (≥ 768 px), 3 (≥ 480 px), 2 (< 480 px).
- **Gap**: 12 px everywhere.
- Poster image: softly rounded corners, 1 px `surface.border`, exact 2:3 `aspect-ratio`.

### Poster Card
```
┌────────────────────┐
│                    │  ← cover image (2:3, object-fit: cover)
│            [ 84% ] │  ← score badge: top-right overlay, 11px, score.high colour
│                    │
└────────────────────┘
  Frieren: Beyond...   ← 14px, content.primary, 2-line max, hover → accent.text
  TV · 2023 · 28 eps  ← 12px, content.secondary
```

Score is displayed as a percentage (integer). Missing score → dash.

### Pagination
- Numbered page links: `← Prev  1 2 3 … 42  Next →`.
- Page number synced to URL query param `?page=N`.
- Current page number styled with `accent.ui` border.

---

## Detail Page

### Banner
- Max-height 240 px wide image (`bannerImage`); linear-gradient overlay to `surface.base` at the bottom so text is readable.
- **Fallback**: If `bannerImage` is null → solid `surface.raised` strip of the same height with no error state.

### Layout (desktop: two-column)

```
[ Banner (full width, 240px, gradient overlay) ]

[ Cover poster 220px ] │ [ Content column, flex-1 ]
                       │
                       │  Romanized title (20px, semibold)
                       │  Native title (13px, content.secondary)
                       │  Format · Episodes · Status · Year (12px, muted)
                       │
                       │  Average score: [  84%  ] (score.high colour, 18px)
                       │  Your rating:   [ ★ 8 ] (accent.text, distinct style)
                       │                           ← reserved, wired Phase 6
                       │
                       │  [ + Add to List ]   (btn-primary, reserved Phase 6)
                       │  [ 1-10 rating control ] (reserved, wired Phase 6)
                       │
                       │  ── Synopsis ──────────────────────────────────
                       │  14px body text, content.primary, natural line-height
                       │
                       │  ── Info Table ─────────────────────────────────
                       │  Studio | Source | Duration | Popularity
                       │  (12px dense key/value rows)
                       │
                       │  Genres: Action, Fantasy, …   (plain text links)
                       │  Tags:   Isekai, Time Skip, … (plain text)
```

**Removed from v1 detail page**: Staff credits, Aired dates, Related anime.

**Mobile**: Sidebar (cover poster + score + action buttons) stacks **above** the content column.

### Score Display Rules
- Average community score: integer percentage (e.g. "84%"), coloured by `score.high / mid / low`.
- User's own rating (1–10 scale, Phase 6): shown separately with a `★` prefix and `accent.text` colour so it is visually distinct from the community score.

---

## Recommendation Cards
Used on the similar-anime row (detail page) and on the personalised homepage (Phase 9).

```
┌──────────────┐
│  poster 2:3  │  ← same spec as browse card
│      [ 79% ] │
└──────────────┘
  Title here
  TV · 2022 · 12 eps
  ╰─ "Because you liked Frieren and rated
      slice-of-life highly"               ← accent.text, 12px, 3-line max, always visible
```

- `reason` field is **mandatory and always visible** — never hidden behind a hover or tooltip.
- `similarity` score (0–1) is not displayed to the user in v1.

---

## Component Inventory (to be built in Phase 5)

| Component | Path |
|-----------|------|
| `<PosterCard>` | `src/components/PosterCard.tsx` |
| `<PosterGrid>` | `src/components/PosterGrid.tsx` |
| `<FilterBar>` | `src/components/FilterBar.tsx` |
| `<FilterDrawer>` | `src/components/FilterDrawer.tsx` (mobile) |
| `<Pagination>` | `src/components/Pagination.tsx` |
| `<RecommendationCard>` | `src/components/RecommendationCard.tsx` |
| `<ScoreBadge>` | `src/components/ScoreBadge.tsx` |
| `<AnimeDetailLayout>` | `src/pages/AnimePage.tsx` |
| `<BrowsePage>` | `src/pages/BrowsePage.tsx` |

---

## API Contract (shapes to implement in Phase 2, consumed in Phase 5)

### Browse endpoint
```
GET /api/anime?page=1&perPage=24&genres=Action&format=TV&sort=score
```
Response:
```json
{
  "items": [ { AnimeCard } ],
  "pageInfo": {
    "total": 1200,
    "currentPage": 1,
    "lastPage": 50,
    "perPage": 24,
    "hasNextPage": true
  }
}
```

### AnimeCard (slim, for grid)
```json
{
  "id": 1,
  "title": "Frieren: Beyond Journey's End",
  "titleNative": "葬送のフリーレン",
  "coverImage": "https://…",
  "bannerImage": "https://…",
  "format": "TV",
  "status": "FINISHED",
  "episodes": 28,
  "year": 2023,
  "score": 84,
  "genres": ["Fantasy", "Adventure"]
}
```

### AnimeDetail (full, for detail page)
Extends `AnimeCard` with:
```json
{
  "synopsis": "…",
  "duration": 23,
  "season": "FALL",
  "seasonYear": 2023,
  "studio": "Madhouse",
  "source": "MANGA",
  "tags": ["Isekai", "Time Skip"],
  "popularity": 312400
}
```

### Filter metadata endpoint
```
GET /api/anime/filters
```
Response:
```json
{
  "genres": ["Action", "Adventure", …],
  "tags":   ["Isekai", "Time Skip", …]
}
```

### Recommendation shape
Extends `AnimeCard` with:
```json
{
  "reason": "Because you liked Frieren and rated slice-of-life highly",
  "similarity": 0.87
}
```

---

## Accessibility Notes
- All interactive elements keyboard-navigable; use the shared `accent.ui` focus ring token.
- Poster `<img>` always has `alt` = romanized title.
- Filter controls have associated `<label>`.
- Score badge has `aria-label` (e.g. `"Score: 84%"`).
- Mobile drawer traps focus; closes on Escape.

---

*Document saved: 2026-10-23. Awaiting Phase 2.*
