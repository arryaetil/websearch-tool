"""
researcher.py - OpenAI Responses API met gpt-4o + web_search_preview
Two-call approach: identiteit + adverse media apart
"""
 
import json
import re
from openai import OpenAI
 
SYSTEM_PROMPT_IDENTITY = """You are an AI-powered identity research assistant for a financial institution compliance team.
Use web search to find publicly available information about the subject.
 
RULES:
- Only report what you actually find via web search
- Never fabricate or speculate
- Return empty arrays when nothing is found
- No accusations - factual findings only
- Human analyst review is always required
 
ANONYMIZATION AWARENESS:
- Dutch and Belgian media often anonymize people as "A. Lastname" or "Firstname B."
- If you find anonymized mentions matching the subject (same city, profession, timeframe), include them
- Mark these as "possible match - anonymized in source"
 
Respond with ONLY a valid JSON object. Keep strings under 200 chars. Max 5 items per array. No newlines in strings."""
 
SYSTEM_PROMPT_ADVERSE = """You are an adverse media specialist for a financial institution compliance team.
Your ONLY task is to find negative news, legal issues, and risk indicators about the subject.
Use web search extensively.
 
RULES:
- Only report what you actually find via web search
- Never fabricate
- Return empty arrays when nothing is found
- No accusations - factual findings only
 
WHAT TO SEARCH FOR:
- Fraud, scams, financial crimes
- Bankruptcy, insolvency, debt
- Court cases, lawsuits, judgments
- Tax fraud, money laundering
- Regulatory violations, sanctions
- Negative news articles
- ANONYMIZED mentions: Dutch/Belgian media writes "A. Lastname" or "Firstname B." in legal cases
  If you find anonymized mentions from the same city/region, include them as possible matches
 
Respond with ONLY a valid JSON object. Keep strings under 200 chars. Max 5 items per array. No newlines in strings."""
 
 
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
 
 
def build_identity_prompt(name, city, age, employer, context):
    parts = name.strip().split()
    last_name = parts[-1] if parts else name
    first_initial = parts[0][0] if parts else ""
 
    lines = [
        "Research this person's identity and professional background. Use web search.",
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
        "Run these searches:",
        f'1. "{first_initial}. {last_name}" {city}',
        f'2. "{name}" {city}',
        f'3. "{name}" OR "{first_initial}. {last_name}" linkedin OR kvk OR bedrijf',
        f'4. "{last_name}" {city} directeur OR eigenaar OR bestuurder',
        "",
        "Return ONLY this JSON:",
        '{',
        '  "identity_matches": [{"name": "string", "description": "string", "confidence": "high|medium|low"}],',
        '  "professional_profiles": [{"platform": "string", "role": "string", "company": "string", "url_hint": "string"}],',
        '  "business_records": [{"entity": "string", "role": "string", "status": "string", "source": "string"}],',
        '  "social_media_presence": [{"platform": "string", "description": "string"}],',
        '  "name_variations_searched": ["string"],',
        '  "sources": [{"name": "string", "url": "string", "type": "string"}]',
        '}',
    ]
    return "\n".join(lines)
 
 
def build_adverse_prompt(name, city, age, employer, context):
    parts = name.strip().split()
    last_name = parts[-1] if parts else name
    first_initial = parts[0][0] if parts else ""
    first_name = parts[0] if parts else name
 
    lines = [
        "Search for adverse media, legal issues and risk indicators for this person.",
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
 
    # Build all name forms
    initial_lastname = f"{first_initial}. {last_name}"
    full_name_q = name
 
    lines += [
        "",
        "CRITICAL: Run ALL searches IN ORDER - do not skip any:",
        "",
        "── PRIMARY (initial + lastname - most effective for NL/BE media) ──",
        f'1. "{initial_lastname}" {city}',
        f'2. "{initial_lastname}" fraude OR faillissement OR rechtbank',
        f'3. "{initial_lastname}" schulden OR oplichting OR FIOD OR belastingdienst',
        f'4. "{initial_lastname}" surseance OR curator OR insolventie OR failliet',
        "",
        "── SECONDARY (full name + lastname only) ──",
        f'5. "{full_name_q}" fraude OR faillissement OR rechtbank',
        f'6. "{last_name}" {city} fraude OR oplichting OR strafrecht',
        f'7. "{last_name}" {city} nieuws OR rechtszaak OR veroordeeld',
        "",
        "IMPORTANT: Dutch/Belgian media ALWAYS uses initial+lastname in legal cases.",
        f'"{initial_lastname}" searches will find most NL adverse media.',
        f'If you find "{initial_lastname}" or "{first_name} B." articles from {city} - include them.',
        "",
        "Return ONLY this JSON:",
        '{',
        '  "media_mentions": [{"title": "string", "source": "string", "date": "string", "summary": "string", "sentiment": "positive|neutral|negative"}],',
        '  "risk_flags": [{"severity": "high|medium|low", "category": "string", "description": "string"}],',
        '  "adverse_sources": [{"name": "string", "url": "string", "type": "string"}]',
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
 
 
def compute_confidence(identity_report, adverse_report):
    """Compute overall confidence score based on both reports."""
    score = 10
 
    # Identity signals
    matches = identity_report.get("identity_matches", [])
    if any(m.get("confidence") == "high" for m in matches):
        score += 35
    elif any(m.get("confidence") == "medium" for m in matches):
        score += 20
 
    if identity_report.get("professional_profiles"):
        score += 15
    if identity_report.get("business_records"):
        score += 15
    if identity_report.get("social_media_presence"):
        score += 10
 
    # Cap at 85 if no adverse, allow up to 95 with lots of data
    sources = len(identity_report.get("sources", []))
    score += min(sources * 3, 15)
 
    score = min(score, 95)
 
    if score >= 75:
        verdict = "High"
    elif score >= 50:
        verdict = "Moderate"
    elif score >= 25:
        verdict = "Low"
    else:
        verdict = "Low"
 
    reasoning = f"Based on {len(matches)} identity match(es), " \
                f"{len(identity_report.get('professional_profiles', []))} professional profile(s), " \
                f"{len(identity_report.get('business_records', []))} business record(s)."
 
    flags = adverse_report.get("risk_flags", [])
    if any(f.get("severity") == "high" for f in flags):
        reasoning += " HIGH risk indicators found."
    elif any(f.get("severity") == "medium" for f in flags):
        reasoning += " Medium risk indicators found."
 
    return str(score), verdict, reasoning
 
 
def merge_reports(identity_report, adverse_report, name, city):
    """Merge identity and adverse media reports into one."""
    all_sources = identity_report.get("sources", []) + adverse_report.get("adverse_sources", [])
 
    # Deduplicate sources by URL
    seen_urls = set()
    unique_sources = []
    for s in all_sources:
        url = s.get("url", "")
        if url not in seen_urls:
            seen_urls.add(url)
            unique_sources.append(s)
 
    score, verdict, reasoning = compute_confidence(identity_report, adverse_report)
 
    return {
        "identity_matches": identity_report.get("identity_matches", []),
        "professional_profiles": identity_report.get("professional_profiles", []),
        "media_mentions": adverse_report.get("media_mentions", []),
        "business_records": identity_report.get("business_records", []),
        "social_media_presence": identity_report.get("social_media_presence", []),
        "risk_flags": adverse_report.get("risk_flags", []),
        "confidence_score": score,
        "confidence_verdict": verdict,
        "confidence_reasoning": reasoning,
        "name_variations_searched": identity_report.get("name_variations_searched", []),
        "sources": unique_sources[:10]
    }
 
 
def run_research(api_key, name, city, age="", employer="", context=""):
    try:
        client = OpenAI(api_key=api_key)
 
        # ── Call 1: Identity + professional ──────────────────────────────────
        r1 = client.responses.create(
            model="gpt-4o",
            tools=[{"type": "web_search_preview"}],
            instructions=SYSTEM_PROMPT_IDENTITY,
            input=build_identity_prompt(name, city, age, employer, context)
        )
 
        raw1 = ""
        for block in r1.output:
            if hasattr(block, "content"):
                for part in block.content:
                    if hasattr(part, "text"):
                        raw1 += part.text
            elif hasattr(block, "text"):
                raw1 += block.text
 
        identity_report = parse_response(raw1) if raw1.strip() else {}
 
        # ── Call 2: Adverse media ─────────────────────────────────────────────
        r2 = client.responses.create(
            model="gpt-4o",
            tools=[{"type": "web_search_preview"}],
            instructions=SYSTEM_PROMPT_ADVERSE,
            input=build_adverse_prompt(name, city, age, employer, context)
        )
 
        raw2 = ""
        for block in r2.output:
            if hasattr(block, "content"):
                for part in block.content:
                    if hasattr(part, "text"):
                        raw2 += part.text
            elif hasattr(block, "text"):
                raw2 += block.text
 
        adverse_report = parse_response(raw2) if raw2.strip() else {}
 
        # ── Merge ─────────────────────────────────────────────────────────────
        report = merge_reports(identity_report, adverse_report, name, city)
        return report, None
 
    except (json.JSONDecodeError, ValueError) as e:
        return fallback_report(name, city), f"JSON parse error: {e}"
    except Exception as e:
        return fallback_report(name, city), str(e)
 