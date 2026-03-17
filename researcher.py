"""
researcher.py - OpenAI Responses API met gpt-4o + web_search_preview
Geoptimaliseerde zoekstrategie voor Nederlandse/Belgische namen
Inclusief adverse media detectie en geanonimiseerde vermeldingen
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

ANONYMIZATION AWARENESS:
- Dutch and Belgian media often anonymize people in legal cases as "A. Lastname" or "Firstname B."
- If you find anonymized mentions that likely match the subject (same city, same profession, same timeframe), include them
- Clearly mark these as "possible match - anonymized in source"
- Common aliases: shortened first names (Appie=Albert, Bert=Albert, Hank=Hendrik, etc.)

IMPORTANT - JSON OUTPUT:
- Respond with ONLY a valid JSON object
- Keep all string values SHORT (max 200 characters per field)
- Keep arrays to max 5 items each
- No newlines inside string values"""


def generate_name_variations(name):
    parts = name.strip().split()
    variations = []

    if len(parts) >= 2:
        first = parts[0]
        last = parts[-1]
        middle = parts[1:-1]

        variations.append(f"{first[0]}. {' '.join(middle + [last])}")
        variations.append(name)
        variations.append(last)

        if middle:
            variations.append(f"{first} {last}")
            variations.append(f"{first[0]}. {last}")

        short_names = {
            "albert": ["bert", "al", "appie"],
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
    first_name = parts[0] if parts else name

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
        "SEARCH INSTRUCTIONS - execute ALL of these searches:",
        "",
        "── IDENTITY SEARCHES ──",
        f'1. "{first_initial}. {last_name}" {city}',
        f'2. "{name}" {city}',
        f'3. "{last_name}" {city}',
        "",
        "── PROFESSIONAL SEARCHES ──",
        f'4. "{first_initial}. {last_name}" OR "{name}" kvk OR linkedin OR bedrijf OR directeur',
        f'5. "{last_name}" {city} eigenaar OR bestuurder OR ondernemer',
        "",
        "── ADVERSE MEDIA SEARCHES ──",
        f'6. "{first_initial}. {last_name}" fraude OR faillissement OR rechtbank OR schulden',
        f'7. "{last_name}" {city} fraude OR oplichting OR FIOD OR belastingdienst OR strafrecht',
        f'8. "{name}" OR "{first_initial}. {last_name}" surseance OR curator OR insolventie',
        "",
        "ANONYMIZATION NOTE:",
        f"Dutch media often writes '{first_initial}. {last_name}' or '{first_name} B.' in legal cases.",
        "If you find articles mentioning an anonymized person from the same city/region",
        "with matching context (profession, timeframe), include it as a possible match.",
        "",
        "Combine ALL findings into ONE report.",
        "Return ONLY this JSON (no markdown, no explanation):",
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
        '  "name_variations_searched": ["list of variations actually searched"],',
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