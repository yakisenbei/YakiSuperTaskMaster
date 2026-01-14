from __future__ import annotations

import re

from taskmaster.repository import normalize_tag


def parse_search_query(query: str) -> tuple[str, list[str]]:
    """Return (text_query, tags).

    - Extracts #tag tokens as tags (AND semantics).
    - Remaining text becomes title/note LIKE query.
    """

    raw = (query or "").strip()
    if not raw:
        return "", []

    tokens = re.split(r"\s+", raw)
    tags: list[str] = []
    text_parts: list[str] = []

    for t in tokens:
        if t.startswith("#") and len(t) > 1:
            tags.append(normalize_tag(t[1:]))
        else:
            text_parts.append(t)

    text = " ".join(text_parts).strip()
    # de-dup tags while preserving order
    seen: set[str] = set()
    uniq_tags: list[str] = []
    for tag in tags:
        if tag and tag not in seen:
            seen.add(tag)
            uniq_tags.append(tag)

    return text, uniq_tags
