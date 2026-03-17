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
 
Respond with ONLY a valid JSON object. Keep strings under 200 chars. Max 5 items per array. No newlines in strings."""
 
 
def build_prompt(name, city, age, employer, context):
    lines = [
        "Search the web and research this individual for financial compliance review.",
        "",
        f"Name: {name}",
        f"City/Region: {city}",
    ]
    if age:      lines.append(f"Age: {age}")
    if employer: lines.append(f"Employer: {employer}")
    if context:  lines.append(f"Context: {context}")
    lines += [
        "",
        "Find: identity matches, professional history, news/adverse media,",
        "business registrations, social media, sanctions or legal issues.",
        "Return ONLY the JSON object."
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