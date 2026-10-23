# AniMatch – Phase 5 Approved Design

> **Status**: Approved. Build begins after Phase 4 is complete.  
> **Reference tone**: AniList / Letterboxd — content first, chrome minimal.

---

## Design Rules (override all earlier styling)

1. **No** gradient text, glow/blur effects, glassmorphism, icon-in-rounded-square tiles, pill badges, or marketing taglines in the UI.
2. Cover art is the visual identity. Pages are dominated by a dense grid of anime posters (2:3 ratio) with tight, consistent gaps — not by hero text or decorative cards.
3. Flat near-black surfaces separated by 1 px borders only. No drop shadows.
4. **One accent, two values**:
   - `#7c65c1` → borders, buttons, focus rings (UI chrome)
   - `#9d8bdc` → accent text only (meets WCAG AA contrast on `#0d0d11`)
5. Small, information-dense type: card titles at 14–15 px, real data (score %, year, format, episodes) on every card.
6. Wordmark is plain text in the normal font weight — no gradient, no icon tile.
7. Muted gray (`#9494a0`) for all secondary metadata.

---

## Colour Tokens (Tailwind)

| Token | Value | Use |
|-------|-------|-----|
| `surface.base` | `#0d0d11` | Page background |
| `surface.raised` | `#141419` | Cards, sidebars, panels |
| `surface.overlay` | `#1a1a22` | Dropdowns, modals |
| `surface.border` | `#202028` | 1 px dividers |
| `accent.ui` | `#7c65c1` | Borders, buttons, focus rings |
| `accent.hover` | `#6a56aa` | Hover state of accent buttons |
| `accent.text` | `#9d8bdc` | Accent-coloured text (WCAG AA) |
| `accent.subtle` | `rgba(124,101,193,0.12)` | Hover fill on filter rows |
| `content.primary` | `#eeeeee` | Titles, body text |
| `content.secondary` | `#9494a0` | Metadata, labels |
| `content.muted` | `#5e5e6e` | Placeholders, disabled |
| `score.high` | `#4ade80` | ≥ 75 % |
| `score.mid` | `#facc15` | 50–74 % |
| `score.low` | `#f87171` | < 50 % |

---

## Global Layout

### Header (48 px fixed top bar)
- 1 px bottom border (`surface.border`), `surface.base` fill.
- Left: plain-text wordmark **AniMatch** (normal weight, `content.primary`).
- Centre: compact search input (expand on focus, no separate search page for v1).
- Right: `Browse` nav link only — **no Recommendations link in v1**.
- Auth state: `Sign in` ghost button → `Avatar + username` dropdown after login (wired Phase 3+).

### Filter Bar (sticky below header, 44 px, desktop)
Supported filters match the Phase 2 API exactly:

| Filter | Control | API param |
|--------|---------|-----------|
| Search | Text input (in header) | `search` |
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
- Poster image: sharp corners, 1 px `surface.border`, exact 2:3 `aspect-ratio`.

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
      slice-of-life highly"               ← accent.text, 12px, 2-line max, always visible
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
- All interactive elements keyboard-navigable; focus ring `2px solid #7c65c1`.
- Poster `<img>` always has `alt` = romanized title.
- Filter controls have associated `<label>`.
- Score badge has `aria-label` (e.g. `"Score: 84%"`).
- Mobile drawer traps focus; closes on Escape.

---

*Document saved: 2026-10-23. Awaiting Phase 2.*
