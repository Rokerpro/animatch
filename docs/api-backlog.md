# API Backlog

## Future MAL username import

The XML upload imports a user's own MAL export. Consider a separate future
flow that accepts a public MAL username and fetches the list through Jikan,
with rate limiting and clear handling for private or unavailable profiles.

## Normalize list response casing before public API

The watchlist API currently preserves its established mixed casing: entry fields
such as `anime_id`, `added_at`, and `page_info` are snake_case, while the nested
anime card uses camelCase fields such as `coverImage`. Keep this contract stable
for current clients. Before declaring the API public, plan a versioned migration
that normalizes casing across the list response and its nested objects.
