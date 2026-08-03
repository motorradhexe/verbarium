"""Text normalisation for search. → D16"""

import unicodedata


def normalise(value: str) -> str:
    """Lowercase and strip diacritics.

    Applied to both the stored search text and the query, so `Grosse` finds
    `Große` and `cafe` finds `café`. Done in Python rather than by the
    database, because SQLite and PostgreSQL offer nothing comparable that
    behaves the same way on both.
    """
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    return "".join(character for character in decomposed if not unicodedata.combining(character))


def build_search_text(*parts: str | list[str] | None) -> str:
    """The haystack for one term entry.

    Covers term, definition, synonyms, and NoGo alternatives, as
    `REQUIREMENTS.md` requires. Maintained on write: searching inside a JSON
    column is not portable between the two backends, and normalising at query
    time would rule out using an index later.
    """
    pieces: list[str] = []

    for part in parts:
        if part is None:
            continue
        if isinstance(part, list):
            pieces.extend(str(item) for item in part)
        else:
            pieces.append(str(part))

    return normalise(" ".join(piece for piece in pieces if piece))
