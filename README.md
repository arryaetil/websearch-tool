# Identity Research Tool — Python MVP

AI-assisted identity research for financial compliance teams.
Powered by OpenAI GPT-5 with web search + Streamlit UI.

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the app
streamlit run app.py
```

## Usage

1. Enter your OpenAI API key in the sidebar
2. Fill in the subject's name and city/region
3. Optionally add age, employer, and research context
4. Enter your analyst name (for the audit log)
5. Click "Run Identity Research"

## Files

| File | Purpose |
|------|---------|
| `app.py` | Streamlit UI — input form, results display |
| `researcher.py` | OpenAI API logic — web search + JSON parsing |
| `requirements.txt` | Python dependencies |
| `audit_log.jsonl` | Auto-created — logs every search (GDPR audit trail) |

## Model notes

The MVP uses `gpt-4o-mini-search-preview` by default (cheaper, fast).
To use GPT-5, change the model string in `researcher.py`:

```python
# Current (cheap, fast):
model="gpt-4o-mini-search-preview"

# Better quality:
model="gpt-4o-search-preview"

# GPT-5 (when available on your API tier):
model="gpt-5-search-preview"
```

## Output

- Live results in Streamlit UI
- Downloadable JSON report
- Automatic audit log (`audit_log.jsonl`)

## Important

- Human review is always required before any decision
- Only public data is used
- Audit log is written for every search (GDPR compliance)
- Never use without a valid legal basis (KYC, compliance, etc.)
