"""
researcher.py - OpenAI Responses API met gpt-4o + web_search_preview
Simpele en betrouwbare versie met initiaal-eerste zoekstrategie
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
 
IMPORTANT ABOUT DUTCH/BELGIAN MEDIA:
- Media in the Netherlands and Belgium often writes "A. Lastname" instead of the full name
- This is especially true for legal cases, fraud, bankruptcy, court cases
- Always search for both the full name AND the initial+lastname version
- If you find "A. Lastname" articles from the same city/region, include them as matches
 
Respond with ONLY a valid JSON object. Keep strings under 200 chars. Max 5 items per array. No newlines in strings."""
 
 
def build_prompt(name, city, age, employer, context):
    parts = name.strip().split()
    last_name = parts[-1] if parts else name
    first_initial = parts[0][0] if parts else ""
    initial_lastname = f"{first_initial}. {last_name}"
 
    lines = [
        "Research this person for financial compliance. Use web search.",
        "",
        f"FULL NAME: {name}",
        f"ALSO SEARCH AS: {initial_lastname}",
        f"LOCATION: {city}",
    ]
    if age:
        lines.append(f"AGE: {age}")
    if employer:
        lines.append(f"EMPLOYER: {employer}")
    if context:
        lines.append(f"CONTEXT: {context}")
 
    lines += [
        "",
        "Run these searches in order:",
        f'1. "{initial_lastname}" {city}',
        f'2. "{name}" {city}',
        f'3. "{initial_lastname}" OR "{name}" linkedin OR kvk OR bedrijf',
        f'4. "{initial_lastname}" fraude OR faillissement OR rechtbank OR schulden',
        f'5. "{initial_lastname}" FIOD OR oplichting OR curator OR insolventie',
        f'6. "{last_name}" {city} nieuws',
        "",
        "Combine all findings into one report.",
        "Return ONLY this JSON:",
        '{',
        '  "identity_matches": [{"name": "string", "description": "string", "confidence": "high|medium|low"}],',
        '  "professional_profiles": [{"platform": "string", "role": "string", "company": "string", "url_hint": "string"}],',
        '  "media_mentions": [{"title": "string", "source": "string", "date": "string", "summary": "string", "sentiment": "positive|neutral|negative"}],',
        '  "business_records": [{"entity": "string", "role": "string", "status": "string", "source": "string"}],',
        '  "social_media_presence": [{"platform": "string", "description": "string"}],',
        '  "risk_flags": [{"severity": "high|medium|low", "category": "string", "description": "string"}],',
        '  "confidence_score": "0-100",',
        '  "confidence_verdict": "Low|Moderate|High|Very High",',
        '  "confidence_reasoning": "string",',
        '  "name_variations_searched": ["list of name variations searched"],',
        '  "sources": [{"name": "string", "url": "string", "type": "string"}]',
        '}',
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
 
        report = parse_response(raw_text)
        return report, None
 
    except (json.JSONDecodeError, ValueError) as e:
        return fallback_report(name, city), f"JSON parse error: {e}"
    except Exception as e:
        return fallback_report(name, city), str(e)
 