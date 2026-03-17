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

def build_prompt(name, city, age="", employer="", context=""):
    parts = name.strip().split()
    first = parts[0] if parts else name
    last = parts[-1] if parts else name
    initial = f"{first[0]}. {last}" if first and last else name

    return f"""
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

def run_research(api_key, name, city, age="", employer="", context=""):
    try:
        client = OpenAI(api_key=api_key)

        response = client.responses.create(
            model="gpt-5.4",
            instructions=SYSTEM_PROMPT,
            input=build_prompt(name, city, age, employer, context),
            tools=[{"type": "web_search"}],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "report",
                    "schema": SCHEMA
                }
            }
        )

        result = json.loads(response.output_text)

        # Filter only the model-returned sources for relevance.
        model_sources = []
        for src in result.get("sources", []):
            if is_relevant_source(src.get("url", ""), name, city):
                model_sources.append(src)

        result["sources"] = dedupe_sources(model_sources)
        result = clean_report(result)
        result = derive_legal_public_records(result)
        result = enrich_risk_flags(result)
        result = clean_report(result)

        return result, None

    except Exception as e:
        return fallback_report(name, city, str(e)), str(e)