import json
from openai import OpenAI

SYSTEM_PROMPT = """You are an identity research assistant for a financial institution compliance team.

Use public web sources only.
Do not speculate.
If identity is uncertain, say so.
Do not accuse anyone of crimes.
Return only facts that can be tied to public sources.
Human analyst review is always required.
"""

SCHEMA = {
    "type": "object",
    "properties": {
        "identity_matches": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "confidence": {"type": "string"}
                },
                "required": ["name", "description", "confidence"],
                "additionalProperties": False
            }
        },
        "professional_profiles": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "platform": {"type": "string"},
                    "role": {"type": "string"},
                    "company": {"type": "string"},
                    "url_hint": {"type": "string"}
                },
                "required": ["platform", "role", "company", "url_hint"],
                "additionalProperties": False
            }
        },
        "media_mentions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "source": {"type": "string"},
                    "date": {"type": "string"},
                    "summary": {"type": "string"},
                    "sentiment": {"type": "string"}
                },
                "required": ["title", "source", "date", "summary", "sentiment"],
                "additionalProperties": False
            }
        },
        "business_records": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "entity": {"type": "string"},
                    "role": {"type": "string"},
                    "status": {"type": "string"},
                    "source": {"type": "string"}
                },
                "required": ["entity", "role", "status", "source"],
                "additionalProperties": False
            }
        },
        "social_media_presence": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "platform": {"type": "string"},
                    "description": {"type": "string"}
                },
                "required": ["platform", "description"],
                "additionalProperties": False
            }
        },
        "risk_flags": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "severity": {"type": "string"},
                    "category": {"type": "string"},
                    "description": {"type": "string"}
                },
                "required": ["severity", "category", "description"],
                "additionalProperties": False
            }
        },
        "confidence_score": {"type": "integer"},
        "confidence_verdict": {"type": "string"},
        "confidence_reasoning": {"type": "string"},
        "name_variations_searched": {
            "type": "array",
            "items": {"type": "string"}
        },
        "sources": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "url": {"type": "string"},
                    "type": {"type": "string"}
                },
                "required": ["name", "url", "type"],
                "additionalProperties": False
            }
        }
    },
    "required": [
        "identity_matches",
        "professional_profiles",
        "media_mentions",
        "business_records",
        "social_media_presence",
        "risk_flags",
        "confidence_score",
        "confidence_verdict",
        "confidence_reasoning",
        "name_variations_searched",
        "sources"
    ],
    "additionalProperties": False
}


def build_prompt(name, city, age="", employer="", context=""):
    parts = name.strip().split()
    first_name = parts[0] if parts else name
    last_name = parts[-1] if parts else name
    first_initial = first_name[0] if first_name else ""
    initial_lastname = f"{first_initial}. {last_name}" if first_initial and last_name else name

    prompt = f"""
Research this person using public web sources only.

Subject:
- Full name: {name}
- City/region: {city}
- Age: {age or "unknown"}
- Employer: {employer or "unknown"}
- Context: {context or "unknown"}

Also search likely name variations:
- {name}
- {initial_lastname}
- {first_name} {last_name}

Goals:
1. Identify likely identity matches
2. Find professional profiles
3. Find media mentions
4. Find business records
5. Find public social presence
6. Note factual public risk indicators only if clearly source-supported
7. Return a confidence score for the identity match

Rules:
- Prefer reliable sources such as LinkedIn, company websites, business registries, established news sites
- If multiple people match, say so
- If information is weak, return low confidence
- Do not speculate
- Do not make unsupported accusations
- Keep summaries concise
"""
    return prompt.strip()


def fallback_report(name, city, error_message="Insufficient data found or API error."):
    return {
        "identity_matches": [{"name": name, "description": f"Individual in {city}", "confidence": "low"}],
        "professional_profiles": [],
        "media_mentions": [],
        "business_records": [],
        "social_media_presence": [],
        "risk_flags": [{"severity": "low", "category": "Data quality", "description": "Limited data found. Manual verification recommended."}],
        "confidence_score": 10,
        "confidence_verdict": "Low",
        "confidence_reasoning": error_message,
        "name_variations_searched": [],
        "sources": []
    }


def run_research(api_key, name, city, age="", employer="", context=""):
    try:
        client = OpenAI(api_key=api_key)

        response = client.responses.create(
            model="gpt-5.4",
            instructions=SYSTEM_PROMPT,
            input=build_prompt(name, city, age, employer, context),
            tools=[{"type": "web_search"}],
            include=["web_search_call.action.sources"],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "identity_research_report",
                    "schema": SCHEMA
                }
            }
        )

        result = json.loads(response.output_text)

        # Merge tool-returned sources into result["sources"]
        seen_urls = {s.get("url") for s in result.get("sources", []) if s.get("url")}
        extra_sources = []

        for item in getattr(response, "output", []):
            if getattr(item, "type", None) == "web_search_call":
                action = getattr(item, "action", None)
                if action and getattr(action, "sources", None):
                    for src in action.sources:
                        url = getattr(src, "url", None)
                        if not url or url in seen_urls:
                            continue
                        seen_urls.add(url)
                        extra_sources.append({
                            "name": getattr(src, "title", url) or url,
                            "url": url,
                            "type": "web"
                        })

        result["sources"] = result.get("sources", []) + extra_sources
        return result, None

    except Exception as e:
        return fallback_report(name, city, str(e)), str(e)