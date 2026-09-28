# KYCX Adverse Media Check — evidence-first MVP

KYCX is an adverse media check prototype with a Next.js interface and a Python FastAPI/LangGraph backend. The app uses the original project's KYCX wordmark alongside a simple eye mark. The login and dashboard use official IBC group technology artwork and the unaltered white IBC group logo from the September 2026 brand asset ZIPs. Night/Seasalt foundations, Ubuntu typography and restrained blue/violet accents follow the IBC group brand guide. The company-research Streamlit prototype remains in `app.py`.

## Local start

Use Python 3.12 or 3.13 and Node.js 20 or newer.

Terminal 1 — backend:

```powershell
python -m pip install -r requirements-api.txt
$env:SERPER_API_KEY = "your-serper-key"
$env:OPENAI_API_KEY = "your-model-key"
python -m uvicorn api:app --reload --port 8000
```

Terminal 2 — frontend:

```powershell
cd frontend
npm install
$env:KYCX_ACCESS_PASSWORD = "a-strong-local-password"
$env:KYCX_SESSION_SECRET = "a-separate-long-random-secret"
npm run dev
```

Open `http://localhost:3000` and sign in as `admin@etil.nl` with the configured password. The workspace contains a clearly labeled fictional sample case. Live checks require both `SERPER_API_KEY` and `OPENAI_API_KEY` in the backend environment. Do not put keys in `NEXT_PUBLIC_` variables or commit `.env` files.

## Session-only privacy behavior

- No search history or research database is created by this prototype. The result exists in browser memory until refresh or navigation.
- The single-admin login uses a signed, HttpOnly, eight-hour cookie. The cookie contains an expiry and signature, not research content. This basic gate does not provide per-user accounts, audit trails or rate limiting.
- The old Streamlit audit-file writes have been removed. The sidebar shows a fictional walkthrough, not a record of past searches.
- The research and PDF API responses use `Cache-Control: no-store`; the Docker backend disables HTTP access logs. PDF files are saved only when the analyst explicitly downloads one.
- This does **not** mean there is no personal-data processing. Serper receives search queries, the model provider receives selected source text and identity clues, and hosting/provider logs or retention policies may still apply. Review the provider contracts, data locations, legal basis, notification duties, and source categories before real client use.
- Storing reviewed reports in a later version is a separate product and legal decision. Define a purpose, access rules and a justified retention period first; some client obligations may require retention.

Run the checks:

```powershell
python -m unittest -q test_identity_workflow.py test_api.py
cd frontend
npm run build
```

## What the person check does

1. Serper searches for public adverse reporting using the full name and supplied city, plus an employer or general identity query.
2. The backend reads up to eight public HTML pages. Search snippets are never treated as evidence.
3. LangGraph runs search, fetch, identity assessment and report assembly.
4. A page is only marked `confirmed` if the full name and another supplied clue occur in the page text and the model assessment agrees. Initials alone never confirm identity.
5. Claims appear only for confirmed matches, with an exact quote present in the retrieved page.
6. The result and PDF are labeled as drafts for human review. There is no automatic risk score or eligibility decision.

The model writes identity reasons and adverse finding summaries in plain, neutral prose, following the useful-text and fact-preservation principles of [blader/humanizer](https://github.com/blader/humanizer) (MIT). Source quotes stay verbatim. A reviewer must still check whether each summary accurately reflects its source.

Crawl4AI is an optional fallback for pages with little readable HTML. Install it separately and set `ENABLE_CRAWL4AI=1` after reviewing browser navigation controls. PDF and paywalled sources are outside the current default fetcher.

## Railway layout

Deploy **two services from the same repository** in the Amsterdam region:

- Backend: repository root, using the root `Dockerfile`. Keep this service on Railway's private network. Set `SERPER_API_KEY` and `OPENAI_API_KEY` as backend variables. Set `PORT=8000`; `/health` is the health check.
- Frontend: root directory `frontend`, build `npm run build`, start `npm run start`. Set server-side `BACKEND_URL=http://kycx-api.railway.internal:8000`, `KYCX_ACCESS_PASSWORD`, and `KYCX_SESSION_SECRET`. Do not use a `NEXT_PUBLIC_` prefix for any of these variables.

The frontend's `/api/research` and `/api/report` routes call the backend from the server, so provider keys are not shipped to the browser. **Before real personal data is used**, add user-specific access control, brute-force protection, appropriate logging without retaining research content, and complete a privacy review. The current app is a reviewable MVP, not a production compliance system. The deployed backend has no public domain. An OpenAI key still needs to be configured for live checks.

## Files

- `frontend/app/page.tsx` — search and source-review interface
- `frontend/app/globals.css` — visual system and responsive layouts
- `frontend/app/icon.svg` — vector eye mark
- `frontend/app/login/page.tsx`, `frontend/auth.ts`, `frontend/proxy.ts` — single-admin login and route gate
- `frontend/app/api/*` — server-side proxy routes
- `api.py` — FastAPI service
- `identity_workflow.py` — Serper, retrieval, identity checks, LangGraph
- `evidence_pdf.py` — draft PDF export
- `test_identity_workflow.py`, `test_api.py` — focused checks

The original `researcher.py` and `app.py` remain available for the legacy Streamlit prototype.
