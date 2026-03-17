import json
from openai import OpenAI
from urllib.parse import urlparse

SYSTEM_PROMPT = """You are an identity research assistant for a financial institution compliance team.

Use public web sources only.
Do not speculate.
Do not accuse.
Only report verifiable facts.

CRITICAL:
If reliable public sources explicitly mention:
- bankruptcy
- insolvency
- court cases
- fraud
- tax fraud (FIOD)
- civil liability
- legal rulings

You MUST include them factually in the output.

Do NOT soften or omit clear public legal facts.

Human analyst review is always required.
"""

SCHEMA = {
    "type": "object",
    "properties": {
        "identity_matches": {"type": "array", "items": {"type": "object", "properties": {
            "name": {"type": "string"},
            "description": {"type": "string"},
            "confidence": {"type": "string"}
        }, "required": ["name","description","confidence"]}},
        
        "professional_profiles": {"type": "array", "items": {"type": "object", "properties": {
            "platform": {"type": "string"},
            "role": {"type": "string"},
            "company": {"type": "string"},
            "url_hint": {"type": "string"}
        }, "required": ["platform","role","company","url_hint"]}},

        "media_mentions": {"type": "array", "items": {"type": "object", "properties": {
            "title": {"type": "string"},
            "source": {"type": "string"},
            "date": {"type": "string"},
            "summary": {"type": "string"},
            "sentiment": {"type": "string"}
        }, "required": ["title","source","date","summary","sentiment"]}},

        "legal_public_records": {"type": "array", "items": {"type": "object", "properties": {
            "issue_type": {"type": "string"},
            "source": {"type": "string"},
            "date": {"type": "string"},
            "summary": {"type": "string"}
        }, "required": ["issue_type","source","date","summary"]}},

        "business_records": {"type": "array", "items": {"type": "object", "properties": {
            "entity": {"type": "string"},
            "role": {"type": "string"},
            "status": {"type": "string"},
            "source": {"type": "string"}
        }, "required": ["entity","role","status","source"]}},

        "social_media_presence": {"type": "array", "items": {"type": "object", "properties": {
            "platform": {"type": "string"},
            "description": {"type": "string"}
        }, "required": ["platform","description"]}},

        "risk_flags": {"type": "array", "items": {"type": "object", "properties": {
            "severity": {"type": "string"},
            "category": {"type": "string"},
            "description": {"type": "string"}
        }, "required": ["severity","category","description"]}},

        "confidence_score": {"type": "integer", "minimum": 0, "maximum": 100},
        "confidence_verdict": {"type": "string", "enum": ["Low","Moderate","High","Very High"]},
        "confidence_reasoning": {"type": "string"},
        "name_variations_searched": {"type": "array", "items": {"type": "string"}},

        "sources": {"type": "array", "items": {"type": "object", "properties": {
            "name": {"type": "string"},
            "url": {"type": "string"},
            "type": {"type": "string"}
        }, "required": ["name","url","type"]}}
    },
    "required": ["identity_matches","professional_profiles","media_mentions","legal_public_records",
                 "business_records","social_media_presence","risk_flags",
                 "confidence_score","confidence_verdict","confidence_reasoning",
                 "name_variations_searched","sources"]
}


def build_prompt(name, city, age="", employer="", context=""):
    parts = name.split()
    first = parts[0]
    last = parts[-1]
    initial = f"{first[0]}. {last}"

    return f"""
Research this person using public web sources.

Name: {name}
City: {city}
Age: {age or "unknown"}
Employer: {employer or "unknown"}

Search variations:
- {name}
- {initial}

Focus on:
1. Identity matching
2. Professional profile
3. Media mentions
4. Legal/public records (bankruptcy, fraud, court)
5. Business registrations

Search queries:
- "{name}" {city}
- "{initial}" {city}
- "{name}" linkedin OR bedrijf OR directeur
- "{name}" faillissement OR curator OR rechtbank
- "{name}" fraude OR FIOD OR belastingfraude
- "{name}" aansprakelijk OR vonnis
"""


def clean_sources(sources, name, city):
    cleaned = []
    seen = set()

    for s in sources:
        url = s.get("url","")
        if not url or url in seen:
            continue

        if any(x in url.lower() for x in ["wikipedia","gamma","rijksmuseum","pdf unrelated"]):
            continue

        seen.add(url)
        cleaned.append(s)

    return cleaned[:10]


def enrich_risk_flags(result):
    text = json.dumps(result).lower()

    flags = result.get("risk_flags", [])

    if "fiod" in text or "belastingfraude" in text:
        flags.append({"severity":"high","category":"Tax fraud","description":"FIOD/tax fraud reference found"})

    if "faillissement" in text or "bankruptcy" in text:
        flags.append({"severity":"medium","category":"Insolvency","description":"Bankruptcy-related record found"})

    if "aansprakelijk" in text or "liable" in text:
        flags.append({"severity":"high","category":"Legal liability","description":"Civil liability indication"})

    result["risk_flags"] = flags[:5]
    return result


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

        result["sources"] = clean_sources(result.get("sources", []), name, city)
        result = enrich_risk_flags(result)

        return result, None

    except Exception as e:
        return None, str(e)