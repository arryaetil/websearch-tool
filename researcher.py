import json
from urllib.parse import urlparse
from openai import OpenAI

SYSTEM_PROMPT = """You are an identity research assistant for a financial institution compliance team.

Use public web sources only.
Do not speculate.
Do not accuse.
Only report verifiable facts supported by reliable public sources.

Important:
- If reliable public sources explicitly mention bankruptcy, insolvency, court cases,
  fraud, tax fraud, FIOD, civil liability, legal rulings, curator findings, or
  public adverse media, include those factually.
- Do not soften or omit clear public legal facts.
- If identity is uncertain, say so clearly.
- Prefer official registries, court/insolvency records, reputable news outlets,
  company websites, LinkedIn, and business registries.
- Exclude unrelated sources that merely share the same first name or surname.
- Human analyst review is always required.
"""

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "identity_matches": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "confidence": {"type": "string"}
                },
                "required": ["name", "description", "confidence"]
            }
        },
        "professional_profiles": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "platform": {"type": "string"},
                    "role": {"type": "string"},
                    "company": {"type": "string"},
                    "url_hint": {"type": "string"}
                },
                "required": ["platform", "role", "company", "url_hint"]
            }
        },
        "media_mentions": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "title": {"type": "string"},
                    "source": {"type": "string"},
                    "date": {"type": "string"},
                    "summary": {"type": "string"},
                    "sentiment": {"type": "string"}
                },
                "required": ["title", "source", "date", "summary", "sentiment"]
            }
        },
        "legal_public_records": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "issue_type": {"type": "string"},
                    "source": {"type": "string"},
                    "date": {"type": "string"},
                    "summary": {"type": "string"}
                },
                "required": ["issue_type", "source", "date", "summary"]
            }
        },
        "business_records": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "entity": {"type": "string"},
                    "role": {"type": "string"},
                    "status": {"type": "string"},
                    "source": {"type": "string"}
                },
                "required": ["entity", "role", "status", "source"]
            }
        },
        "social_media_presence": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "platform": {"type": "string"},
                    "description": {"type": "string"}
                },
                "required": ["platform", "description"]
            }
        },
        "risk_flags": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "severity": {"type": "string"},
                    "category": {"type": "string"},
                    "description": {"type": "string"}
                },
                "required": ["severity", "category", "description"]
            }
        },
        "confidence_score": {
            "type": "integer",
            "minimum": 0,
            "maximum": 100
        },
        "confidence_verdict": {
            "type": "string",
            "enum": ["Low", "Moderate", "High", "Very High"]
        },
        "confidence_reasoning": {
            "type": "string"
        },
        "name_variations_searched": {
            "type": "array",
            "items": {"type": "string"}
        },
        "sources": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "name": {"type": "string"},
                    "url": {"type": "string"},
                    "type": {"type": "string"}
                },
                "required": ["name", "url", "type"]
            }
        }
    },
    "required": [
        "identity_matches",
        "professional_profiles",
        "media_mentions",
        "legal_public_records",
        "business_records",
        "social_media_presence",
        "risk_flags",
        "confidence_score",
        "confidence_verdict",
        "confidence_reasoning",
        "name_variations_searched",
        "sources"
    ]
}

BLOCKED_DOMAINS = {
    "wikipedia.org",
    "werelate.org",
    "gamma.be",
    "rijksmuseum.nl",
    "mediacourant.nl",
    "calvin.edu",
    "ghdk-flandre.fr",
    "deces-en-france.fr",
    "crtm.es",
    "clerk.ulstercountyny.gov",
    "graftombe.nl",
}

TRUSTED_HINTS = [
    "linkedin",
    "kvk",
    "faillissement",
    "faillissements",
    "rechtspraak",
    "curator",
    "insolvent",
    "bankruptcy",
    "court",
    "tribunal",
    "figaro",
    "pappers",
    "bodacc",
    "company",
    "entreprise",
    "bedrijven",
    "ondernemersvereniging",
    "telefoonboek",
    "nieuws",
    "news",
]

LEGAL_KEYWORDS = {
    "bankruptcy": "Bankruptcy / insolvency record",
    "faillissement": "Bankruptcy / insolvency record",
    "insolvency": "Bankruptcy / insolvency record",
    "insolvent": "Bankruptcy / insolvency record",
    "curator": "Curator / insolvency report",
    "rechtbank": "Court record",
    "court": "Court record",
    "vonnis": "Court ruling",
    "liable": "Civil liability",
    "aansprakelijk": "Civil liability",
    "fraud": "Fraud-related public record",
    "fraude": "Fraud-related public record",
    "belastingfraude": "Tax fraud public record",
    "fiod": "FIOD / tax fraud public record",
    "veroordeeld": "Conviction-related public record",
}

def build_prompt(name, city, age="", employer="", context="", extra_queries=None):
    parts = name.strip().split()
    first = parts[0] if parts else name
    last = parts[-1] if parts else name
    initial = f"{first[0]}. {last}" if first and last else name

    base = f"""
Research this person using public web sources.

Subject:
- Name: {name}
- City/region: {city}
- Age: {age or "unknown"}
- Employer: {employer or "unknown"}
- Context: {context or "unknown"}

Search likely name variants:
- {name}
- {initial}
- {first} {last}

Prioritize:
1. Identity resolution
2. Professional profiles
3. Business registrations
4. Public media mentions
5. Legal and insolvency public records
6. Public social presence
7. Risk indicators from reliable public records only

Targeted searches to perform:
- "{name}" "{city}"
- "{initial}" "{city}"
- "{name}" LinkedIn OR bedrijf OR bestuurder OR directeur
- "{name}" faillissement OR curator OR rechtbank OR insolventie
- "{name}" fraude OR FIOD OR belastingfraude OR veroordeeld
- "{name}" aansprakelijk OR civiel OR vonnis
- "{name}" "{city}" nieuws

Output rules:
- Only include sources directly relevant to the identified subject
- Exclude unrelated people with the same surname or first name
- confidence_verdict must be exactly one of: Low, Moderate, High, Very High
- Keep summaries concise and factual
""".strip()

    if extra_queries:
        follow_up = "\n\nAdditional targeted follow-up searches based on prior findings:\n"
        follow_up += "\n".join(f"- {q}" for q in extra_queries)
        return base + follow_up

    return base

def fallback_report(name, city, error_message="Insufficient data found or API error."):
    return {
        "identity_matches": [
            {
                "name": name,
                "description": f"Possible individual in {city}, but insufficient public data found.",
                "confidence": "low"
            }
        ],
        "professional_profiles": [],
        "media_mentions": [],
        "legal_public_records": [],
        "business_records": [],
        "social_media_presence": [],
        "risk_flags": [
            {
                "severity": "low",
                "category": "Data quality",
                "description": "Limited data found. Manual verification recommended."
            }
        ],
        "confidence_score": 10,
        "confidence_verdict": "Low",
        "confidence_reasoning": error_message,
        "name_variations_searched": [name],
        "sources": []
    }

def host_from_url(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().replace("www.", "")
    except Exception:
        return ""

def is_relevant_source(url: str, subject_name: str, city: str) -> bool:
    if not url:
        return False

    host = host_from_url(url)
    if any(host.endswith(domain) for domain in BLOCKED_DOMAINS):
        return False

    url_l = url.lower()
    city_l = city.lower().strip()
    name_parts = [p.lower().strip() for p in subject_name.split() if p.strip()]

    has_name = any(part in url_l for part in name_parts)
    has_city = city_l in url_l if city_l else False
    has_trusted_hint = any(hint in url_l for hint in TRUSTED_HINTS)

    return has_trusted_hint or (has_name and has_city)

def clean_report(result: dict) -> dict:
    result["identity_matches"] = result.get("identity_matches", [])[:5]
    result["professional_profiles"] = result.get("professional_profiles", [])[:5]
    result["media_mentions"] = result.get("media_mentions", [])[:5]
    result["legal_public_records"] = result.get("legal_public_records", [])[:5]
    result["business_records"] = result.get("business_records", [])[:5]
    result["social_media_presence"] = result.get("social_media_presence", [])[:5]
    result["risk_flags"] = result.get("risk_flags", [])[:5]
    result["sources"] = result.get("sources", [])[:10]

    allowed = {"Low", "Moderate", "High", "Very High"}
    score = result.get("confidence_score", 0)

    if result.get("confidence_verdict") not in allowed:
        if score >= 85:
            result["confidence_verdict"] = "Very High"
        elif score >= 70:
            result["confidence_verdict"] = "High"
        elif score >= 45:
            result["confidence_verdict"] = "Moderate"
        else:
            result["confidence_verdict"] = "Low"

    return result

def derive_legal_public_records(result: dict) -> dict:
    legal_records = result.get("legal_public_records", [])
    seen = {
        (
            rec.get("issue_type", ""),
            rec.get("source", ""),
            rec.get("date", ""),
            rec.get("summary", "")
        )
        for rec in legal_records
    }

    text_candidates = []

    for m in result.get("media_mentions", []):
        text_candidates.append({
            "source": m.get("source", ""),
            "date": m.get("date", ""),
            "summary": f'{m.get("title", "")}. {m.get("summary", "")}'.strip()
        })

    for b in result.get("business_records", []):
        text_candidates.append({
            "source": b.get("source", ""),
            "date": "",
            "summary": f'{b.get("entity", "")}. {b.get("status", "")}. {b.get("role", "")}'.strip()
        })

    for s in result.get("sources", []):
        text_candidates.append({
            "source": s.get("name", ""),
            "date": "",
            "summary": s.get("url", "")
        })

    for item in text_candidates:
        blob = (item.get("summary", "") + " " + item.get("source", "")).lower()
        for kw, issue_type in LEGAL_KEYWORDS.items():
            if kw in blob:
                candidate = {
                    "issue_type": issue_type,
                    "source": item.get("source", "") or "Public source",
                    "date": item.get("date", ""),
                    "summary": item.get("summary", "")[:220]
                }
                key = (
                    candidate["issue_type"],
                    candidate["source"],
                    candidate["date"],
                    candidate["summary"]
                )
                if key not in seen:
                    legal_records.append(candidate)
                    seen.add(key)
                break

    result["legal_public_records"] = legal_records[:5]
    return result

def enrich_risk_flags(result: dict) -> dict:
    flags = result.get("risk_flags", [])
    existing = {(f.get("category", ""), f.get("description", "")) for f in flags}

    combined_text = json.dumps({
        "media_mentions": result.get("media_mentions", []),
        "legal_public_records": result.get("legal_public_records", []),
        "business_records": result.get("business_records", [])
    }).lower()

    candidates = []

    if any(k in combined_text for k in ["fiod", "belastingfraude"]):
        candidates.append({
            "severity": "high",
            "category": "Tax/Fraud public record",
            "description": "Public sources indicate FIOD or tax-fraud-related context. Human review required."
        })

    if any(k in combined_text for k in ["faillissement", "bankruptcy", "insolvency", "curator", "insolvent"]):
        candidates.append({
            "severity": "medium",
            "category": "Insolvency public record",
            "description": "Public insolvency or bankruptcy-related record found."
        })

    if any(k in combined_text for k in ["aansprakelijk", "liable", "vonnis", "rechtbank", "court ruling"]):
        candidates.append({
            "severity": "high",
            "category": "Civil liability / court outcome",
            "description": "Public source suggests a liability finding or court-related outcome."
        })

    if any(k in combined_text for k in ["fraud", "fraude", "veroordeeld"]):
        candidates.append({
            "severity": "high",
            "category": "Fraud / conviction-related public record",
            "description": "Public source includes fraud-related or conviction-related context. Manual review required."
        })

    for candidate in candidates:
        key = (candidate["category"], candidate["description"])
        if key not in existing:
            flags.append(candidate)
            existing.add(key)

    result["risk_flags"] = flags[:5]
    return result

def dedupe_sources(sources: list) -> list:
    cleaned = []
    seen = set()

    for s in sources:
        url = s.get("url", "")
        if not url or url in seen:
            continue
        seen.add(url)
        cleaned.append(s)

    return cleaned[:10]

def dedupe_items(items: list, key_fields: list) -> list:
    """Deduplicate a list of dicts by a tuple of field values."""
    seen = set()
    unique = []
    for item in items:
        key = tuple(str(item.get(k, "")).strip().lower() for k in key_fields)
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def run_single_pass(client, name, city, age="", employer="", context="", extra_queries=None):
    """Execute one OpenAI web-search pass and return a parsed report dict."""
    response = client.responses.create(
        model="gpt-5.4",
        instructions=SYSTEM_PROMPT,
        input=build_prompt(name, city, age, employer, context, extra_queries=extra_queries),
        tools=[{"type": "web_search"}],
        text={
            "format": {
                "type": "json_schema",
                "name": "report",
                "schema": SCHEMA,
            }
        },
    )
    return json.loads(response.output_text)


def extract_followup_queries(result: dict, name: str, city: str) -> list:
    """
    Produce a ranked, high-signal set of follow-up search queries derived from
    an initial pass result.  Queries are ordered by expected relevance:
      1. Legal / adverse (highest signal)
      2. Name + entity/company + role keyword
      3. Name + city + legal terms
      4. Name variant + city (lowest priority, only if variant is meaningfully different)

    Returns at most 5 deduplicated queries.
    """
    MAX = 5
    _SKIP = {"unknown", "—", "", "-"}

    def _clean(v):
        return (v or "").strip()

    def _skip(v):
        return not v or v.lower() in _SKIP

    # ── Collect signals from the result ───────────────────────────────────────
    companies = []
    for p in result.get("professional_profiles", []):
        c = _clean(p.get("company"))
        if not _skip(c):
            companies.append(c)
    for b in result.get("business_records", []):
        e = _clean(b.get("entity"))
        if not _skip(e):
            companies.append(e)

    legal_records = result.get("legal_public_records", [])

    def _legal_text(rec):
        """Return the searchable text for a single legal record."""
        return " ".join([
            (rec.get("issue_type") or ""),
            (rec.get("summary") or ""),
        ]).lower()

    _legal_blob = " ".join(_legal_text(r) for r in legal_records)

    has_legal      = bool(legal_records)
    has_insolvency = any(k in _legal_blob for k in (
        "faillissement", "bankruptcy", "insolvency", "curator", "insolvent"
    ))
    has_fraud      = any(k in _legal_blob for k in (
        "fraud", "fraude", "fiod", "belastingfraude", "veroordeeld"
    ))
    has_liability  = any(k in _legal_blob for k in (
        "aansprakelijk", "liable", "vonnis", "civiel"
    ))
    risk_flags = result.get("risk_flags", [])
    high_risk = any((f.get("severity") or "").lower() == "high" for f in risk_flags)

    variants = [
        v for v in result.get("name_variations_searched", [])
        if v and v.strip().lower() != name.strip().lower()
    ]

    # ── Build ranked candidate list ───────────────────────────────────────────
    # Tier 1 — legal / adverse (highest signal, generated first)
    candidates = []

    if has_insolvency or high_risk:
        # Name + city + insolvency (Dutch + English)
        candidates.append(
            f'"{name}" "{city}" faillissement OR bankruptcy OR curator OR insolvent'
        )

    if has_fraud or high_risk:
        # Name + city + fraud (Dutch + English)
        candidates.append(
            f'"{name}" "{city}" fraude OR fraud OR FIOD OR belastingfraude OR veroordeeld'
        )

    if has_liability:
        candidates.append(
            f'"{name}" "{city}" aansprakelijk OR liable OR vonnis OR "court ruling"'
        )

    if has_legal and not has_insolvency and not has_fraud and not has_liability:
        # Generic legal follow-up when we know there's something but can't classify it yet
        candidates.append(
            f'"{name}" "{city}" rechtbank OR court OR rechtspraak OR tribunal'
        )

    # Tier 2 — name + company/entity + role/legal keyword
    for company in companies[:2]:                        # cap at 2 entities to avoid dilution
        if has_fraud or high_risk:
            candidates.append(f'"{name}" "{company}" fraude OR fraud OR aansprakelijk OR liable')
        elif has_insolvency:
            candidates.append(f'"{name}" "{company}" faillissement OR bankruptcy OR curator')
        else:
            candidates.append(f'"{name}" "{company}" bestuurder OR directeur OR eigenaar OR director')

    # Tier 3 — name + city + professional context (only if no strong legal signal)
    if not has_legal and not high_risk and companies:
        candidates.append(
            f'"{name}" "{city}" LinkedIn OR KVK OR bedrijf OR onderneming OR company'
        )

    # Tier 4 — name variant + city (lowest priority)
    for variant in variants[:1]:                         # at most one variant query
        candidates.append(f'"{variant}" "{city}" -site:wikipedia.org')

    # ── Deduplicate and return top MAX ────────────────────────────────────────
    seen: set = set()
    unique = []
    for q in candidates:
        q_norm = q.strip().lower()
        if q_norm not in seen:
            seen.add(q_norm)
            unique.append(q)
        if len(unique) == MAX:
            break

    return unique


def merge_reports(reports: list) -> dict:
    """
    Merge multiple pass result dicts into one combined report.
    List fields are concatenated then deduplicated.
    The highest confidence_score across passes wins.
    """
    if not reports:
        return {}
    if len(reports) == 1:
        return reports[0]

    merged = reports[0]

    for report in reports[1:]:
        merged["identity_matches"] = dedupe_items(
            merged.get("identity_matches", []) + report.get("identity_matches", []),
            ["name", "description"],
        )
        merged["professional_profiles"] = dedupe_items(
            merged.get("professional_profiles", []) + report.get("professional_profiles", []),
            ["platform", "role", "company"],
        )
        merged["media_mentions"] = dedupe_items(
            merged.get("media_mentions", []) + report.get("media_mentions", []),
            ["title", "source"],
        )
        merged["legal_public_records"] = dedupe_items(
            merged.get("legal_public_records", []) + report.get("legal_public_records", []),
            ["issue_type", "source", "summary"],
        )
        merged["business_records"] = dedupe_items(
            merged.get("business_records", []) + report.get("business_records", []),
            ["entity", "role"],
        )
        merged["social_media_presence"] = dedupe_items(
            merged.get("social_media_presence", []) + report.get("social_media_presence", []),
            ["platform", "description"],
        )
        merged["risk_flags"] = dedupe_items(
            merged.get("risk_flags", []) + report.get("risk_flags", []),
            ["category", "description"],
        )
        merged["sources"] = dedupe_items(
            merged.get("sources", []) + report.get("sources", []),
            ["url"],
        )
        merged["name_variations_searched"] = list({
            v for v in
            merged.get("name_variations_searched", []) + report.get("name_variations_searched", [])
            if v
        })

        # Take the higher confidence score and its associated verdict/reasoning
        if report.get("confidence_score", 0) > merged.get("confidence_score", 0):
            merged["confidence_score"] = report["confidence_score"]
            merged["confidence_verdict"] = report.get("confidence_verdict", merged.get("confidence_verdict"))
            merged["confidence_reasoning"] = report.get("confidence_reasoning", merged.get("confidence_reasoning"))

    return merged


def run_research(api_key, name, city, age="", employer="", context=""):
    MAX_PASSES = 3
    MAX_FOLLOWUPS = 5

    try:
        client = OpenAI(api_key=api_key)
        pass_results = []

        # ── Pass 1: broad initial search ──────────────────────────────────────
        result1 = run_single_pass(client, name, city, age, employer, context)
        pass_results.append(result1)

        pending_queries = extract_followup_queries(result1, name, city)[:MAX_FOLLOWUPS]

        # ── Passes 2–3: targeted follow-up searches ───────────────────────────
        for pass_num in range(2, MAX_PASSES + 1):
            if not pending_queries:
                break

            # Spread remaining queries evenly across remaining passes
            remaining_passes = MAX_PASSES - pass_num + 1
            batch_size = max(1, len(pending_queries) // remaining_passes)
            batch, pending_queries = pending_queries[:batch_size], pending_queries[batch_size:]

            try:
                result_n = run_single_pass(
                    client, name, city, age, employer, context,
                    extra_queries=batch,
                )
                pass_results.append(result_n)

                # Surface any new follow-up clues from this pass
                new_queries = extract_followup_queries(result_n, name, city)
                for q in new_queries:
                    if q not in pending_queries and len(pending_queries) < MAX_FOLLOWUPS:
                        pending_queries.append(q)

            except Exception:
                # A failed follow-up pass is non-fatal; continue with what we have
                continue

        # ── Merge all passes ──────────────────────────────────────────────────
        result = merge_reports(pass_results)

        # ── Post-processing (unchanged) ───────────────────────────────────────
        model_sources = [
            src for src in result.get("sources", [])
            if is_relevant_source(src.get("url", ""), name, city)
        ]
        result["sources"] = dedupe_sources(model_sources)
        result = clean_report(result)
        result = derive_legal_public_records(result)
        result = enrich_risk_flags(result)
        result = clean_report(result)

        return result, None

    except Exception as e:
        return fallback_report(name, city, str(e)), str(e)