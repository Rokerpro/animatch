"""Text cleaning and sanitization utilities."""

import html
import re

_APOSTROPHE_TRANSLATION = str.maketrans(
    {"\u2018": "'", "\u2019": "'", "\u02bc": "'", "`": "'"}
)


def normalize_title_search(value: str | None) -> str:
    """Normalize title punctuation for FTS queries and fuzzy title matching."""
    if not value:
        return ""
    normalized = value.translate(_APOSTROPHE_TRANSLATION).replace("'", "")
    return re.sub(r"[^\w]+", " ", normalized, flags=re.UNICODE).strip().lower()


def strip_html_tags(raw: str | None) -> str | None:
    """Strips HTML tags from text, converts <br> tags to newlines, and unescapes entities."""
    if not raw:
        return None
    # Convert <br>, <br/>, <p> endings to newlines
    text = re.sub(r"<br\s*/?>", "\n", raw, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "\n\n", text, flags=re.IGNORECASE)
    # Strip remaining HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # Unescape HTML entities (&quot;, &#039;, &amp;, etc.)
    text = html.unescape(text)
    # Normalize excessive newlines
    text = re.sub(r"\n{3,}", "\n\n", text)
    cleaned = text.strip()
    return cleaned if cleaned else None


def sanitize_fts_query(q: str | None) -> str:
    """Sanitizes user search query for SQLite FTS5 MATCH clause.

    - Strips SQLite FTS syntax and operators (AND, OR, NOT, NEAR, quotes, colons, parens, etc.)
    - Extracts alphanumeric words (including non-ASCII unicode for Japanese/kanji/kana)
    - Appends '*' to the last token for prefix matching
    - Returns a safe MATCH expression or empty string if no valid tokens
    """
    if not q:
        return ""

    # Reserved words to strip
    reserved = {"AND", "OR", "NOT", "NEAR"}

    # Extract alphanumeric words (supports all Unicode word characters)
    tokens = re.findall(r"[\w]+", q, flags=re.UNICODE)
    cleaned_tokens = [t for t in tokens if t.upper() not in reserved]

    if not cleaned_tokens:
        return ""

    # Quote each token; append '*' to the last token for prefix matching
    fts_parts = [f'"{t}"' for t in cleaned_tokens[:-1]]
    fts_parts.append(f'"{cleaned_tokens[-1]}"*')

    return " ".join(fts_parts)
