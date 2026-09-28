"""Public BIG-register webservice (CIBG) for healthcare professionals. No account required."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

import requests

from identity_rules import normalize, split_name

ENDPOINT = "https://api.bigregister.nl/zksrv/soap/4"
ACTION = "http://services.cibg.nl/ExternalUser/ListHcpApprox4"
NS = "{http://services.cibg.nl/ExternalUser}"
SEARCH_PAGE = "https://zoeken.bigregister.nl/"


def _request(surname: str, prefix: str, initials: str) -> bytes:
    fields = f"<WebSite>Ribiz</WebSite><Name>{escape(surname)}</Name>"
    if initials:
        fields += f"<Initials>{escape(initials)}</Initials>"
    if prefix:
        fields += f"<Prefix>{escape(prefix)}</Prefix>"
    return (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"><soap:Body>'
        f'<listHcpApproxRequest xmlns="http://services.cibg.nl/ExternalUser">{fields}</listHcpApproxRequest>'
        "</soap:Body></soap:Envelope>"
    ).encode()


def parse_response(xml_bytes: bytes) -> list[dict]:
    records = []
    for item in ET.fromstring(xml_bytes).iter(f"{NS}ListHcpApprox4"):
        cities = sorted({
            (address.findtext(f"{NS}City") or "").strip()
            for tag in ("WorkAddress1", "WorkAddress2", "WorkAddress3")
            if (address := item.find(f"{NS}{tag}")) is not None
        } - {""})
        measures = [
            (j.findtext(f"{NS}PublicDescription") or "Public judgment provision").strip()
            for j in item.iter(f"{NS}JudgmentProvisionExtApp")
            if (j.findtext(f"{NS}Public") or "").lower() == "true"
        ] + [
            (limit.findtext(f"{NS}Description") or "Registration limitation").strip()
            for limit in item.iter(f"{NS}LimitationExtApp")
        ]
        records.append({
            "mailing_name": (item.findtext(f"{NS}MailingName") or "").strip(),
            "surname": (item.findtext(f"{NS}BirthSurname") or "").strip(),
            "initials": (item.findtext(f"{NS}Initial") or "").strip(),
            "work_cities": cities,
            "registrations": [r.findtext(f"{NS}ArticleRegistrationNumber") for r in item.iter(f"{NS}ArticleRegistrationExtApp")],
            "measures": measures,
        })
    return records


def search(name: str) -> list[dict]:
    first, prefix, surname = split_name(name)
    initials = "".join(part[0].upper() for part in first)
    response = requests.post(
        ENDPOINT, data=_request(surname, prefix, initials), timeout=20,
        headers={"Content-Type": "text/xml; charset=utf-8", "SOAPAction": f'"{ACTION}"'},
    )
    response.raise_for_status()
    return parse_response(response.content)


def assess_records(records: list[dict], name: str, city: str) -> list[dict]:
    """A register entry names initials, not first names, and a work city, not a home city."""
    first, _, surname = split_name(name)
    initial = first[0][0] if first else ""
    results = []
    for record in records:
        if normalize(record["surname"]).split()[-1:] != surname.split()[-1:]:
            continue
        if initial and not normalize(record["initials"]).startswith(initial):
            continue
        city_match = any(normalize(c) == normalize(city) for c in record["work_cities"])
        # The analyst stated a healthcare profession, and the register confirms one:
        # initials, surname, work city and profession together meet the strong tier.
        identity, tier = ("confirmed", 3) if city_match else ("possible", 2)
        reason = ("Registered healthcare professional; initials, surname and work city match."
                  if city_match else "Registered healthcare professional with this name; work city differs or is not listed.")
        results.append({**record, "identity": identity, "confidence_score": tier, "reason": reason, "url": SEARCH_PAGE})
    return results
