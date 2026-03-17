"""
researcher.py - OpenAI Responses API met gpt-4o + web_search_preview
Geoptimaliseerde zoekstrategie voor Nederlandse/Belgische namen
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
 
IMPORTANT - JSON OUTPUT:
- Respond with ONLY a valid JSON object
- Keep all string values SHORT (max 200 characters per field)
- Keep arrays to max 5 items each
- No newlines inside string values"""
 
 
def generate_name_variations(name):
    """Generate Dutch name variations for better search coverage."""
    parts = name.strip().split()
    variations = []
 
    if len(parts) >= 2:
        first = parts[0]
        last = parts[-1]
        middle = parts[1:-1]
 
        # 1. Initiaal + achternaam eerst (werkt vaak beter in NL media)
        variations.append(f"{first[0]}. {' '.join(middle + [last])}")
        # 2. Volledige naam
        variations.append(name)
        # 3. Alleen achternaam + stad
        variations.append(last)
        # 4. Zonder tussenvoegsel
        if middle:
            variations.append(f"{first} {last}")
            variations.append(f"{first[0]}. {last}")
 
        # 5. Bekende Nederlandse bijnamen
        short_names = {
            "albert": ["bert", "al"],
            "wilhelmus": ["wim", "willem"],
            "johannes": ["jan", "jo", "hans"],
            "jacobus": ["jaap"],
            "cornelis": ["cor", "kees"],
            "henricus": ["henk"],
            "theodorus": ["theo"],
            "antonius": ["ton", "toon"],
            "franciscus": ["frank", "frans"],
            "petrus": ["peter", "piet"],
            "gerardus": ["gerard", "gerrit"],
            "alexander": ["alex", "sander"],
            "thomas": ["tom"],
            "michael": ["mike", "michel"],
            "robert": ["rob"],
            "hendrik": ["henk"],
            "william": ["wim"],
        }
        if first.lower() in short_names:
            for nick in short_names[first.lower()]:
                variations.append(f"{nick.capitalize()} {' '.join(middle + [last])}")
 
    # Dedupliceer
    seen = set()
    unique = []
    for v in variations:
        if v.lower() not in seen:
            seen.add(v.lower())
            unique.append(v)
 
    return unique[:6]
 
 
def build_prompt(name, city, age, employer, context):
    variations = generate_name_variations(name)
    parts = name.strip().split()
    last_name = parts[-1] if parts else name
    first_initial = parts[0][0] if parts else ""
 
    lines = [
        "You are researching a person for financial compliance. Use web search.",
        "",
        f"SUBJECT: {name}",
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
        "SEARCH INSTRUCTIONS - execute these searches in order:",
        f'1. Search: "{first_initial}. {last_name}" {city}',
        f'2. Search: "{name}" {city}',
        f'3. Search: "{last_name}" {city} bedrijf OR directeur OR eigenaar',
        f'4. Search: "{name}" OR "{first_initial}. {last_name}" kvk OR linkedin',
        f'5. Search: "{last_name}" {city} nieuws OR rechtbank OR fraude',
        "",
        "IMPORTANT:",
        "- Try ALL searches above, even if the first one returns results",
        "- Different searches may reveal different information",
        "- Merge all findings into one report",
        "- If you find the person under one name variation, use that for follow-up searches",
        "",
        "Return ONLY this JSON object, no markdown:",
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
        '  "name_variations_searched": ["list of name variations actually used"],',
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
        raise ValueError("No JSON object found in response")
 
    json_str = match.group(0)
 
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        pass
 
    # Repair truncated JSON
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