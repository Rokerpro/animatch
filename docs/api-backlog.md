# API Backlog

## Future MAL username import (blocked upstream)

The XML upload imports a user's own MAL export. A public-username flow via Jikan
is not possible: Jikan's OpenAPI spec marks `GET /users/{username}/animelist` as
deprecated and says user anime lists were discontinued on May 1st, 2022. The
remaining options are MAL's official API (requires registering a MAL client ID and
per-user OAuth) or scraping an undocumented MAL endpoint (fragile and against
MAL's terms), so this stays on the XML export until a decision is made.
