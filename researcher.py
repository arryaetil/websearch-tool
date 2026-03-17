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
 
Respond with ONLY a valid JSON object using this exact schema:
{
  "identity_matches": [{"name": "string", "description": "string", "confidence": "high|medium|low"}],
  "professional_profiles": [{"platform": "string", "role": "string", "company": "string", "url_hint": "string"}],
  "media_mentions": [{"title": "string", "source": "string", "date": "string", "summary": "string", "sentiment": "positive|neutral|negative"}],
  "business_records": [{"entity": "string", "role": "string", "status": "string", "source": "string"}],
  "social_media_presence": [{"platform": "string", "description": "string"}],
  "risk_flags": [{"severity": "high|medium|low", "category": "string", "description": "string"}],
  "confidence_score": "0-100",
  "confidence_verdict": "Low|Moderate|High|Very High",
  "confidence_reasoning": "string",
  "sources": [{"name": "string", "url": "string", "type": "string"}]
}"""
 
 
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
        "sources": []
    }
 
 
def parse_response(raw):
    cleaned = re.sub(r"```(?:json)?", "", raw).strip()
    match = re.search(r"\{[\s\S]*\}", cleaned)
    if match:
        return json.loads(match.group(0))
    return json.loads(cleaned)
 
 
def run_research(api_key, name, city, age="", employer="", context=""):
    try:
        client = OpenAI(api_key=api_key)
 
        response = client.responses.create(
            model="gpt-4o",
            tools=[{"type": "web_search_preview"}],
            instructions=SYSTEM_PROMPT,
            input=build_prompt(name, city, age, employer, context)
        )
 
        # Extract text output
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
 
    except json.JSONDecodeError as e:
        return fallback_report(name, city), f"JSON parse error: {e}"
    except Exception as e:
        return fallback_report(name, city), str(e)
