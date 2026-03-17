"""
researcher.py - OpenAI Responses API met gpt-4o + web_search_preview
"""

import json
import re
from openai import OpenAI

SYSTEM_PROMPT = """You are an AI-powered identity research assistant for a financial institution compliance team.
Use web search to find publicly available information about the subject.

RULES:
- Only report what you actually find via web search
- Never fabricate or speculate
- Return empty arrays when nothing is found
- No accusations - factual findings only
- Human analyst review is always required

CRITICAL: You MUST respond with ONLY a valid JSON object using EXACTLY these field names.
Do NOT use different field names. Do NOT add extra fields. Do NOT add markdown.
Max 5 items per array. Max 200 chars per string value. No newlines in strings.

REQUIRED JSON STRUCTURE:
{
  "identity_matches": [{"name": "string", "description": "string", "confidence": "high|medium|low"}],
  "professional_profiles": [{"platform": "string", "role": "string", "company": "string", "url_hint": "string"}],
  "media_mentions": [{"title": "string", "source": "string", "date": "string", "summary": "string", "sentiment": "positive|neutral|negative"}],
  "business_records": [{"entity": "string", "role": "string", "status": "string", "source": "string"}],
  "social_media_presence": [{"platform": "string", "description": "string"}],
  "risk_flags": [{"severity": "high|medium|low", "category": "string", "description": "string"}],
  "confidence_score": "integer 0-100 as string",
  "confidence_verdict": "Low|Moderate|High|Very High",
  "confidence_reasoning": "string",
  "name_variations_searched": ["string"],
  "sources": [{"name": "string", "url": "string", "type": "string"}]
}"""


def build_prompt(name, city, age, employer, context):
    parts = name.strip().split()
    last_name = parts[-1] if parts else name
    first_initial = parts[0][0] if parts else ""
    initial_lastname = f"{first_initial}. {last_name}"

    lines = [
        "Search the web and research this individual for financial compliance.",
        "",
        f"Name: {name}",
        f"Also search as: {initial_lastname}",
        f"City/Region: {city}",
    ]
    if age:      lines.append(f"Age: {age}")
    if employer: lines.append(f"Employer: {employer}")
    if context:  lines.append(f"Context: {context}")

    lines += [
        "",
        "Run these searches:",
        f'1. "{initial_lastname}" {city}',
        f'2. "{name}" {city}',
        f'3. "{initial_lastname}" OR "{name}" linkedin OR kvk OR bedrijf',
        f'4. "{initial_lastname}" fraude OR faillissement OR rechtbank OR schulden',
        f'5. "{last_name}" {city} nieuws OR oplichting OR FIOD',
        "",
        "IMPORTANT: Return ONLY the JSON object with EXACTLY the field names from the schema.",
        "Do not use different field names like 'professional_history' or 'sanctions_legal_issues'.",
        "Use EXACTLY: identity_matches, professional_profiles, media_mentions, business_records,",
        "social_media_presence, risk_flags, confidence_score, confidence_verdict,",
        "confidence_reasoning, name_variations_searched, sources",
    ]
    return "\n".join(lines)


def fallback_report(name, city):
    return {
        "identity_matches": [{"name": name, "description": f"Individual in {city}", "confidence": "low"}],
        "professional_profiles": [],
        "media_mentions": [],
        "business_records": [],
        "social_media_presence": [],
        "risk_flags": [{"severity": "low", "category": "Data quality", "description": "Limited data found. Manual verification recommended."}],
        "confidence_score": "10",
        "confidence_verdict": "Low",
        "confidence_reasoning": "Insufficient data found or API error.",
        "name_variations_searched": [],
        "sources": []
    }


def normalize_report(data):
    """Map any non-standard field names to our schema."""
    result = fallback_report("", "")

    # Identity matches
    for key in ["identity_matches", "identity", "matches"]:
        if key in data and data[key]:
            items = data[key]
            result["identity_matches"] = []
            for item in items[:5]:
                if isinstance(item, dict):
                    result["identity_matches"].append({
                        "name": item.get("name", item.get("full_name", "")),
                        "description": item.get("description", item.get("aliases", [""])[0] if item.get("aliases") else ""),
                        "confidence": item.get("confidence", "medium")
                    })
            break

    # Professional profiles
    for key in ["professional_profiles", "professional_history", "employment", "work_history"]:
        if key in data and data[key]:
            items = data[key]
            result["professional_profiles"] = []
            for item in items[:5]:
                if isinstance(item, dict):
                    activities = item.get("activities", [])
                    desc = activities[0] if activities else ""
                    result["professional_profiles"].append({
                        "platform": item.get("platform", item.get("source", "Public record")),
                        "role": item.get("role", item.get("title", "")),
                        "company": item.get("company", item.get("organization", "")),
                        "url_hint": item.get("url_hint", item.get("url", ""))
                    })
            break

    # Media mentions
    for key in ["media_mentions", "news_adverse_media", "news", "media", "adverse_media"]:
        if key in data and data[key]:
            items = data[key]
            result["media_mentions"] = []
            for item in items[:5]:
                if isinstance(item, dict):
                    result["media_mentions"].append({
                        "title": item.get("title", item.get("headline", "")),
                        "source": item.get("source", item.get("outlet", "")),
                        "date": item.get("date", item.get("published", "")),
                        "summary": item.get("summary", item.get("description", "")),
                        "sentiment": item.get("sentiment", "neutral")
                    })
            break

    # Business records
    for key in ["business_records", "business_registrations", "companies", "registrations"]:
        if key in data and data[key]:
            items = data[key]
            result["business_records"] = []
            for item in items[:5]:
                if isinstance(item, dict):
                    result["business_records"].append({
                        "entity": item.get("entity", item.get("name", item.get("company", ""))),
                        "role": item.get("role", item.get("position", "")),
                        "status": item.get("status", item.get("state", "")),
                        "source": item.get("source", item.get("url", ""))
                    })
            break

    # Social media
    for key in ["social_media_presence", "social_media", "social"]:
        if key in data and data[key]:
            items = data[key]
            result["social_media_presence"] = []
            for item in items[:5]:
                if isinstance(item, dict):
                    result["social_media_presence"].append({
                        "platform": item.get("platform", ""),
                        "description": item.get("description", item.get("url", ""))
                    })
            break

    # Risk flags — map from sanctions_legal_issues or similar
    for key in ["risk_flags", "sanctions_legal_issues", "legal_issues", "sanctions", "risks"]:
        if key in data and data[key]:
            items = data[key]
            result["risk_flags"] = []
            for item in items[:5]:
                if isinstance(item, dict):
                    desc = item.get("description", item.get("summary", item.get("details", "")))
                    result["risk_flags"].append({
                        "severity": item.get("severity", "high"),
                        "category": item.get("category", item.get("type", "Legal / Criminal")),
                        "description": str(desc)[:200]
                    })
            break

    # Scalar fields
    result["confidence_score"] = str(data.get("confidence_score", "50"))
    result["confidence_verdict"] = data.get("confidence_verdict", "Moderate")
    result["confidence_reasoning"] = data.get("confidence_reasoning", "")
    result["name_variations_searched"] = data.get("name_variations_searched", [])

    # Sources
    for key in ["sources", "references", "urls"]:
        if key in data and data[key]:
            items = data[key]
            result["sources"] = []
            for item in items[:10]:
                if isinstance(item, dict):
                    result["sources"].append({
                        "name": item.get("name", item.get("title", "")),
                        "url": item.get("url", item.get("link", "#")),
                        "type": item.get("type", "Web")
                    })
            break

    # Auto-generate confidence if missing or 0
    score = int(result["confidence_score"]) if result["confidence_score"].isdigit() else 0
    if score == 0:
        score = 10
        if result["identity_matches"]: score += 25
        if result["professional_profiles"]: score += 15
        if result["business_records"]: score += 15
        if result["media_mentions"]: score += 10
        if result["risk_flags"]: score += 10
        result["confidence_score"] = str(min(score, 95))

    s = int(result["confidence_score"])
    if s >= 75:   result["confidence_verdict"] = "High"
    elif s >= 50: result["confidence_verdict"] = "Moderate"
    else:         result["confidence_verdict"] = "Low"

    return result


def parse_response(raw):
    cleaned = re.sub(r"```(?:json)?", "", raw).strip()
    cleaned = cleaned.replace("```", "").strip()
    match = re.search(r"\{[\s\S]*\}", cleaned)
    if not match:
        raise ValueError("No JSON found")
    json_str = match.group(0)
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        pass
    for end_marker in ['"}', '"]', '}', ']']:
        last_pos = json_str.rfind(end_marker)
        if last_pos > 0:
            truncated = json_str[:last_pos + len(end_marker)]
            open_braces = truncated.count('{') - truncated.count('}')
            open_brackets = truncated.count('[') - truncated.count(']')
            truncated += ']' * max(0, open_brackets) + '}' * max(0, open_braces)
            try:
                return json.loads(truncated)
            except json.JSONDecodeError:
                continue
    raise ValueError("Could not parse JSON")


def run_research(api_key, name, city, age="", employer="", context=""):
    try:
        client = OpenAI(api_key=api_key)

        response = client.responses.create(
            model="gpt-4o",
            tools=[{"type": "web_search_preview"}],
            instructions=SYSTEM_PROMPT,
            input=build_prompt(name, city, age, employer, context)
        )

        raw_text = ""
        for block in response.output:
            if hasattr(block, "content"):
                for part in block.content:
                    if hasattr(part, "text"):
                        raw_text += part.text
            elif hasattr(block, "text"):
                raw_text += block.text

        if not raw_text.strip():
            return fallback_report(name, city), None

        raw_report = parse_response(raw_text)
        report = normalize_report(raw_report)
        return report, None

    except (json.JSONDecodeError, ValueError) as e:
        return fallback_report(name, city), f"JSON parse error: {e}"
    except Exception as e:
        return fallback_report(name, city), str(e)