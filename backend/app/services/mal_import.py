"""Safe parsing helpers for MyAnimeList XML exports."""

from __future__ import annotations

import gzip
import xml.etree.ElementTree as ET
import zlib
from dataclasses import dataclass
from io import BytesIO

from fastapi import HTTPException, status

MAX_COMPRESSED_BYTES = 5 * 1024 * 1024
MAX_XML_BYTES = 25 * 1024 * 1024
MAX_ANIME_ENTRIES = 5000

STATUS_MAP = {
    "1": "watching",
    "watching": "watching",
    "2": "completed",
    "completed": "completed",
    "3": "on_hold",
    "on-hold": "on_hold",
    "on_hold": "on_hold",
    "4": "dropped",
    "dropped": "dropped",
    "6": "planning",
    "plan to watch": "planning",
    "plan_to_watch": "planning",
}


@dataclass(frozen=True)
class MALAnime:
    mal_id: int
    title: str
    status: str
    rating: int | None


def _bad_request(message: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)


def _decompress_gzip(body: bytes) -> bytes:
    try:
        with gzip.GzipFile(fileobj=BytesIO(body)) as stream:
            parts: list[bytes] = []
            total = 0
            while chunk := stream.read(min(64 * 1024, MAX_XML_BYTES - total + 1)):
                total += len(chunk)
                if total > MAX_XML_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="Decompressed XML exceeds the 25 MB limit.",
                    )
                parts.append(chunk)
            return b"".join(parts)
    except HTTPException:
        raise
    except (OSError, EOFError, zlib.error) as exc:
        raise _bad_request("Invalid or corrupt gzip XML export.") from exc


def parse_mal_xml(body: bytes) -> tuple[int, list[MALAnime]]:
    """Validate and parse anime entries, retaining the last duplicate MAL ID."""
    is_gzip = body.startswith(b"\x1f\x8b")
    if is_gzip:
        if len(body) > MAX_COMPRESSED_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Compressed XML exceeds the 5 MB limit.",
            )
        xml_data = _decompress_gzip(body)
    else:
        if len(body) > MAX_XML_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="XML exceeds the 25 MB limit.",
            )
        xml_data = body

    if b"\x00" in xml_data:
        raise _bad_request("XML must use an ASCII-compatible encoding.")
    upper_xml = xml_data.upper()
    if b"<!DOCTYPE" in upper_xml or b"<!ENTITY" in upper_xml:
        raise _bad_request("DOCTYPE and ENTITY declarations are not allowed.")

    entries: dict[int, MALAnime] = {}
    total_entries = 0
    root: ET.Element | None = None
    depth = 0
    try:
        for event, element in ET.iterparse(BytesIO(xml_data), events=("start", "end")):
            if event == "start":
                depth += 1
                if root is None:
                    root = element
                    if root.tag != "myanimelist":
                        raise _bad_request("XML root must be <myanimelist>.")
                continue

            if depth == 2 and element.tag == "anime":
                total_entries += 1
                if total_entries > MAX_ANIME_ENTRIES:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="XML contains more than 5000 anime entries.",
                    )
                fields = {
                    name: (element.findtext(name) or "").strip()
                    for name in (
                        "series_animedb_id",
                        "series_title",
                        "my_score",
                        "my_status",
                    )
                }
                try:
                    mal_id = int(fields.get("series_animedb_id", ""))
                except ValueError as exc:
                    raise _bad_request(
                        "Each <anime> entry must have a numeric series_animedb_id."
                    ) from exc
                if mal_id <= 0:
                    raise _bad_request(
                        "Each <anime> entry must have a positive series_animedb_id."
                    )
                title = fields.get("series_title", "")
                raw_status = fields.get("my_status", "").strip().lower()
                mapped_status = STATUS_MAP.get(raw_status)
                if mapped_status is None:
                    raise _bad_request(
                        f"Unsupported MyAnimeList status: {raw_status or '(empty)'}."
                    )
                try:
                    score = int(fields.get("my_score", "0"))
                except ValueError:
                    score = 0
                rating = score if 1 <= score <= 10 else None
                entries[mal_id] = MALAnime(mal_id, title, mapped_status, rating)
                element.clear()
            depth -= 1
    except HTTPException:
        raise
    except (ET.ParseError, LookupError, UnicodeError) as exc:
        raise _bad_request("Invalid XML document.") from exc

    if root is None:
        raise _bad_request("XML document is empty; expected a <myanimelist> root.")
    if total_entries == 0:
        raise _bad_request("XML export contains no <anime> entries.")
    return total_entries, list(entries.values())
