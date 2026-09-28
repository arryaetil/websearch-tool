"""Deterministic identity rules. A model may extract facts; only these rules decide the tier."""

from __future__ import annotations

import re
import unicodedata

# Dutch surname prefixes (tussenvoegsels) that are not part of the sortable surname.
PREFIXES = {"van", "de", "der", "den", "het", "ten", "ter", "te", "op", "in", "aan", "bij", "uit", "la", "le", "du", "d", "t", "s"}

PROFESSION_TERMS = {
    "healthcare": (
        "arts", "huisarts", "specialist", "chirurg", "tandarts", "apotheker", "verpleegkundige",
        "verloskundige", "fysiotherapeut", "psycholoog", "psychiater", "doctor", "physician",
        "surgeon", "nurse", "dentist", "pharmacist", "midwife", "physiotherapist",
    ),
    "lawyer": ("advocaat", "advocate", "lawyer", "attorney", "solicitor", "barrister"),
}

STRONG_ANCHORS = ("employer", "age", "profession")


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).casefold()
    text = re.sub(r"[^\w\s.,'-]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def split_name(full_name: str) -> tuple[list[str], str, str]:
    """Return first names, prefix and surname: 'Jan de Vries' -> (['jan'], 'de', 'vries')."""
    words = [w.strip(".,") for w in normalize(full_name).split()]
    words = [w for w in words if w]
    if len(words) < 2:
        return words, "", words[0] if words else ""
    first = [words[0]]
    rest = words[1:]
    while len(rest) > 1 and rest[0] not in PREFIXES:
        first.append(rest.pop(0))
    prefix = []
    while len(rest) > 1 and rest[0] in PREFIXES:
        prefix.append(rest.pop(0))
    return first, " ".join(prefix), " ".join(rest)


def _contains(haystack: str, needle: str) -> bool:
    return bool(needle) and re.search(rf"(?<!\w){re.escape(needle)}(?!\w)", haystack) is not None


def name_variants(full_name: str) -> tuple[list[str], list[str]]:
    """Written forms that count as the full name, and as a partial (pseudonymised) name."""
    first, prefix, surname = split_name(full_name)
    if not first or not surname:
        return [], []
    given = first[0]
    tail = f"{prefix} {surname}".strip()
    initial = given[0]
    full = [
        " ".join(first + [tail]), f"{given} {tail}", f"{initial}. {tail}", f"{initial} {tail}",
        f"{tail}, {given}", f"{surname}, {given}", f"{surname}, {initial}.",
    ]
    if prefix:
        full.append(f"{surname}, {given} {prefix}")
    stub = f"{prefix} {surname[0]}".strip()
    partial = [f"{given} {stub}.", f"{given} {stub}"]
    return list(dict.fromkeys(full)), list(dict.fromkeys(partial))


def compare_name(subject_name: str, written: str | None, text: str) -> str:
    """full, partial, conflict or absent."""
    full, partial = name_variants(subject_name)
    body = normalize(text)
    if written:
        seen = normalize(written)
        if any(_contains(seen, v) for v in full):
            return "full"
        if any(_contains(seen, v) for v in partial):
            return "partial"
        first, _, surname = split_name(subject_name)
        seen_first, _, seen_surname = split_name(written)
        if seen_surname == surname and seen_first and first:
            other = seen_first[0].rstrip(".")
            if len(other) > 1 and other != first[0]:
                return "conflict"
    if any(_contains(body, v) for v in full):
        return "full"
    if any(_contains(body, v) for v in partial):
        return "partial"
    return "absent"


def _same_place(a: str, b: str) -> bool:
    a, b = normalize(a), normalize(b)
    return bool(a and b) and (a == b or _contains(a, b) or _contains(b, a))


def compare_city(subject_city: str, written: str | None, text: str) -> str:
    if not subject_city:
        return "absent"
    if written:
        return "match" if _same_place(subject_city, written) else "conflict"
    return "match" if _contains(normalize(text), normalize(subject_city)) else "absent"


def compare_employer(subject_employer: str, written: str | None, text: str) -> str:
    if not subject_employer:
        return "absent"
    if written:
        return "match" if _same_place(subject_employer, written) else "conflict"
    return "match" if _contains(normalize(text), normalize(subject_employer)) else "absent"


def compare_age(birth_year: int | None, age: int | None, publication_year: int | None) -> tuple[str, str]:
    """Age in an article plus its publication year gives an approximate birth year (±1)."""
    if not birth_year or age is None:
        return "absent", ""
    if not publication_year:
        return "absent", "Age stated, but the publication date is unknown."
    implied = publication_year - age
    if abs(implied - birth_year) <= 1:
        return "match", f"Age {age} in {publication_year} fits birth year {birth_year}."
    return "conflict", f"Age {age} in {publication_year} implies about {implied}, not {birth_year}."


def compare_profession(subject_profession: str, written: str | None) -> str:
    # Deliberately never a conflict: people hold several roles, so a different
    # job title is weak evidence against identity.
    terms = PROFESSION_TERMS.get(subject_profession or "")
    if not terms or not written:
        return "absent"
    seen = normalize(written)
    return "match" if any(_contains(seen, term) for term in terms) else "absent"


def decide_tier(card: dict) -> tuple[str, int, str]:
    """Return (identity, confidence_score 0-3, reason). Any conflict wins."""
    statuses = {key: value["status"] for key, value in card.items()}
    conflicts = [key for key, status in statuses.items() if status == "conflict"]
    if conflicts:
        return "unrelated", 0, "Contradicting " + ", ".join(conflicts) + "."
    name = statuses.get("name", "absent")
    if name == "absent":
        return "unrelated", 0, "The subject's name was not found in this source."
    city = statuses.get("city") == "match"
    strong = sum(statuses.get(key) == "match" for key in STRONG_ANCHORS)
    if (name == "full" and city and strong >= 1) or (name == "partial" and city and strong >= 2):
        return "confirmed", 3, "Name and city match, with no contradictions, plus " + (
            f"{strong} strong identifier." if strong == 1 else f"{strong} strong identifiers.")
    if city or strong:
        need = "one more strong identifier" if name == "full" else "two strong identifiers"
        return "possible", 2, f"Candidate: needs {need} (employer, age or profession)."
    return "possible", 1, "Only the name matches."
