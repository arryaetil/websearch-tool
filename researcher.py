import json
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = """You are an identity research assistant for a financial compliance team.

Search the web freely and thoroughly — the same way a skilled investigator would
type a name into Google and follow every relevant lead.

Rules:
- Use public sources only. Do not speculate or invent facts.
- Search in Dutch and English.
- Follow leads: if you find a company, search it. If you find a court case, search it.
- Report what you find factually. Do not soften or omit adverse findings.
- Exclude unrelated people who happen to share the same name.
- If identity is uncertain, say so clearly.
- Human analyst review is always required before any decision.
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


def build_prompt(name, city, age="", employer="", context=""):
    parts = name.strip().split()
    first = parts[0] if parts else name
    last  = parts[-1] if parts else name
    initial = f"{first[0]}. {last}" if first and last else name

    extras = []
    if age:
        extras.append(f"Age: {age}")
    if employer:
        extras.append(f"Employer: {employer}")
    if context:
        extras.append(f"Context: {context}")
    extra_str = "\n".join(f"- {e}" for e in extras)

    last_initial = f"{last[0]}." if last else ""
    first_initial = f"{first[0]}." if first else ""
    abbrev_last = f"{first} {last_initial}"       # e.g. "Albert B."  — Dutch media/court convention
    abbrev_first = f"{first_initial} {last}"      # e.g. "A. Bril"    — formal Dutch abbreviation

    return f"""
Search for everything publicly available about this person.

Name: {name}
Also try: {initial} · {abbrev_last} · {abbrev_first} · {first} {last}
Location: {city}
{extra_str}

Important: Dutch news articles, court records, and fraud reporting often use partial names
like "{abbrev_last}" or "{abbrev_first}" instead of the full name. Always search these
abbreviated forms — they are the same person and often lead to the most relevant findings.

Search freely. Start broad, then follow every relevant lead you find —
companies, news articles, court records, LinkedIn profiles, business registries,
social media, adverse media, insolvency records, anything public.

Cover: identity · professional history · business roles · media mentions ·
legal and court records · insolvency · fraud · social presence · risk indicators.
""".strip()


def fallback_report(name, city, error_message="Insufficient data found or API error."):
    return {
        "identity_matches": [{
            "name": name,
            "description": f"Possible individual in {city}, but insufficient public data found.",
            "confidence": "low"
        }],
        "professional_profiles": [],
        "media_mentions": [],
        "legal_public_records": [],
        "business_records": [],
        "social_media_presence": [],
        "risk_flags": [{
            "severity": "low",
            "category": "Data quality",
            "description": "Limited data found. Manual verification recommended."
        }],
        "confidence_score": 10,
        "confidence_verdict": "Low",
        "confidence_reasoning": error_message,
        "name_variations_searched": [name],
        "sources": []
    }


def dedupe_sources(sources: list) -> list:
    seen = set()
    unique = []
    for s in sources:
        url = s.get("url", "")
        if url and url not in seen:
            seen.add(url)
            unique.append(s)
    return unique[:10]


def clean_report(result: dict) -> dict:
    caps = {
        "identity_matches": 5,
        "professional_profiles": 5,
        "media_mentions": 5,
        "legal_public_records": 5,
        "business_records": 5,
        "social_media_presence": 5,
        "risk_flags": 5,
        "sources": 10,
    }
    for field, limit in caps.items():
        result[field] = result.get(field, [])[:limit]

    score = result.get("confidence_score", 0)
    if result.get("confidence_verdict") not in {"Low", "Moderate", "High", "Very High"}:
        if score >= 85:
            result["confidence_verdict"] = "Very High"
        elif score >= 70:
            result["confidence_verdict"] = "High"
        elif score >= 45:
            result["confidence_verdict"] = "Moderate"
        else:
            result["confidence_verdict"] = "Low"

    return result


def run_research(name, city, age="", employer="", context=""):
    try:
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

        response = client.responses.create(
            model="gpt-5.1",
            instructions=SYSTEM_PROMPT,
            input=build_prompt(name, city, age, employer, context),
            tools=[{"type": "web_search"}],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "report",
                    "schema": SCHEMA,
                }
            },
        )

        result = json.loads(response.output_text)
        result["sources"] = dedupe_sources(result.get("sources", []))
        result = clean_report(result)

        return result, None

    except Exception as e:
        return fallback_report(name, city, str(e)), str(e)
