"""Official EU and Dutch sanctions lists, downloaded daily and matched locally.

No subject data leaves the server: lists are fetched in full and compared here.
"""

from __future__ import annotations

import json
import os
import re
import time
import xml.etree.ElementTree as ET
import zipfile
from difflib import SequenceMatcher
from io import BytesIO
from pathlib import Path

import requests

from identity_rules import normalize

EU_URL = "https://webgate.ec.europa.eu/fsd/fsf/public/files/xmlFullSanctionsList_1_1/content?token=dG9rZW4tMjAxNw"
NL_URL = ("https://www.rijksoverheid.nl/site/binaries/site-content/collections/documents/"
          "2015/08/27/nationale-terrorismelijst/ned-terrorismelijst.ods")
NL_PAGE = "https://www.rijksoverheid.nl/documenten/2015/08/27/nationale-terrorismelijst"
REFRESH_SECONDS = 24 * 60 * 60
STALE_SECONDS = 2 * 24 * 60 * 60
MIN_SIMILARITY = 0.9

_memory: dict = {}


def _data_dir() -> Path:
    run_db = os.environ.get("KYCX_RUN_DB", "./data/research_runs.sqlite3")
    return Path(os.environ.get("KYCX_DATA_DIR", Path(run_db).parent))


def parse_eu(xml_bytes: bytes) -> list[dict]:
    ns = "{http://eu.europa.ec/fpi/fsd/export}"
    entries = []
    for _, element in ET.iterparse(BytesIO(xml_bytes)):
        if element.tag != f"{ns}sanctionEntity":
            continue
        subject = element.find(f"{ns}subjectType")
        if subject is not None and subject.get("code") == "person":
            names = [a.get("wholeName", "") for a in element.findall(f"{ns}nameAlias") if a.get("wholeName")]
            years = sorted({int(b.get("year")) for b in element.findall(f"{ns}birthdate") if (b.get("year") or "").isdigit()})
            regulation = element.find(f"{ns}regulation")
            url = regulation.findtext(f"{ns}publicationUrl", "") if regulation is not None else ""
            entries.append({
                "list": "EU sanctions list", "names": names, "birth_years": years,
                "reference": element.get("euReferenceNumber", ""),
                "programme": regulation.get("programme", "") if regulation is not None else "",
                "url": url,
            })
        element.clear()
    return entries


def _ods_rows(ods_bytes: bytes) -> list[list[str]]:
    ns = {"table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
          "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0"}
    root = ET.fromstring(zipfile.ZipFile(BytesIO(ods_bytes)).read("content.xml"))
    repeat = "{urn:oasis:names:tc:opendocument:xmlns:table:1.0}number-columns-repeated"
    rows = []
    for row in root.iter(f"{{{ns['table']}}}table-row"):
        cells = []
        for cell in row:
            value = " ".join("".join(p.itertext()) for p in cell.findall("text:p", ns)).strip()
            cells.extend([value] * min(int(cell.get(repeat, "1")), 20))
        rows.append(cells)
    return rows


def parse_nl(ods_bytes: bytes) -> list[dict]:
    rows = _ods_rows(ods_bytes)
    header = next((i for i, r in enumerate(rows) if r and r[0].strip().casefold() == "achternaam"), None)
    if header is None:
        raise ValueError("Unexpected layout of the Dutch sanctions list")
    entries = []
    for row in rows[header + 1:]:
        row = (row + [""] * 7)[:7]
        surname, given, alias, born, _place, _decision, notice = (c.strip() for c in row)
        if not surname:
            continue
        match = re.search(r"(\d{4})\s*$", born)
        entries.append({
            "list": "Dutch national terrorism sanctions list",
            "names": [n for n in (f"{given} {surname}".strip(), alias) if n],
            "birth_years": [int(match.group(1))] if match else [],
            "reference": notice, "programme": "Sanctiewet 1977", "url": NL_PAGE,
        })
    return entries


def _refresh(name: str, url: str, parser) -> tuple[list[dict], float]:
    directory = _data_dir()
    directory.mkdir(parents=True, exist_ok=True)
    index = directory / f"sanctions_{name}.json"
    fetched_at = 0.0
    if index.exists():
        cached = json.loads(index.read_text(encoding="utf-8"))
        fetched_at = cached["fetched_at"]
        if time.time() - fetched_at < REFRESH_SECONDS:
            return cached["entries"], fetched_at
    try:
        response = requests.get(url, timeout=60, headers={"User-Agent": "KYCX/0.2"})
        response.raise_for_status()
        entries = parser(response.content)
        if not entries:
            raise ValueError("Empty sanctions list")
        fetched_at = time.time()
        index.write_text(json.dumps({"fetched_at": fetched_at, "entries": entries}), encoding="utf-8")
        return entries, fetched_at
    except Exception:
        if index.exists():  # An older copy is better than none; the report flags it as stale.
            return json.loads(index.read_text(encoding="utf-8"))["entries"], fetched_at
        raise


def load_lists() -> dict[str, tuple[list[dict], float]]:
    lists = {}
    for name, url, parser in (("eu", EU_URL, parse_eu), ("nl", NL_URL, parse_nl)):
        cached = _memory.get(name)
        if cached and time.time() - cached[1] < REFRESH_SECONDS:
            lists[name] = cached
        else:
            lists[name] = _memory[name] = _refresh(name, url, parser)
    return lists


def _similar(subject: str, candidate: str) -> float:
    a, b = sorted(normalize(subject).split()), sorted(normalize(candidate).split())
    return SequenceMatcher(None, " ".join(a), " ".join(b)).ratio()


def match_entries(entries: list[dict], name: str, birth_year: int | None) -> list[dict]:
    """Name-based candidates, decided by birth year when both sides have one."""
    tokens = set(normalize(name).split())
    given = normalize(name).split()[0]
    hits = []
    for entry in entries:
        # Cheap prefilter: an alias must share at least one name token.
        aliases = [a for a in entry["names"] if tokens & set(normalize(a).split())]
        if not aliases:
            continue
        best = max(aliases, key=lambda alias: _similar(name, alias))
        score = _similar(name, best)
        # A different first name ("Uday Saddam ..." for "Saddam ...") is another person.
        first = normalize(best).split()[0]
        if score < MIN_SIMILARITY or SequenceMatcher(None, given, first).ratio() < 0.85:
            continue
        years = entry["birth_years"]
        if birth_year and years:
            if birth_year in years:
                identity, tier, reason = "confirmed", 3, f"Name matches and listed birth year {birth_year} matches."
            else:
                identity, tier, reason = "unrelated", 0, f"Listed birth year {', '.join(map(str, years))} differs from {birth_year}."
        elif years:
            identity, tier, reason = "possible", 2, "Name matches. Add a birth year to confirm or rule out."
        else:
            identity, tier, reason = "possible", 2, "Name matches. The list gives no birth date."
        hits.append({**entry, "matched_name": best, "similarity": round(score, 3),
                     "identity": identity, "confidence_score": tier, "reason": reason})
    return hits
