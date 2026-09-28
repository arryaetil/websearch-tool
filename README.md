# KYCX Adverse Media Check — evidence-first MVP

KYCX is an adverse media check prototype with a Next.js interface and a Python FastAPI/LangGraph backend. The app uses the original project's KYCX wordmark. The login and dashboard use official IBC group technology artwork and the unaltered white IBC group logo from the September 2026 brand asset ZIPs. Night/Seasalt foundations, Ubuntu typography and restrained blue/violet accents follow the IBC group brand guide. The company-research Streamlit prototype remains in `app.py`.

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

Open `http://localhost:3000` and sign in as `admin@etil.nl` with the configured password. Live checks require both `SERPER_API_KEY` and `OPENAI_API_KEY` in the backend environment. Do not put keys in `NEXT_PUBLIC_` variables or commit `.env` files.

## Temporary evaluation storage

- Successful research reports are stored in a private SQLite database for seven days, with a maximum of 100 runs. Expired runs are purged on access, at backend startup, and hourly while it is running. The sidebar lets the signed-in analyst reopen, delete, or clear saved checks.
- Set `KYCX_RUN_DB=/data/research_runs.sqlite3` on Railway and mount a persistent volume at `/data` on the private backend service. Locally the default is `./data/research_runs.sqlite3`, which is Git-ignored. Losing the Railway volume loses saved runs.
- The single-admin login uses a signed, HttpOnly, eight-hour cookie. The cookie contains an expiry and signature, not research content. This basic gate does not provide per-user accounts, audit trails or rate limiting.
- The old Streamlit audit-file writes remain removed. All users sharing the single admin credential can see all saved checks, so this is for controlled evaluation only.
- The research and PDF API responses use `Cache-Control: no-store`; the Docker backend disables HTTP access logs. PDF files are saved only when the analyst explicitly downloads one.
- This does **not** mean there is no personal-data processing. Serper receives search queries, the model provider receives selected source text and identity clues, and hosting/provider logs or retention policies may still apply. Review the provider contracts, data locations, legal basis, notification duties, and source categories before real client use.
- Seven days is an evaluation default, not a legal retention determination. Define a purpose, access rules, legal basis, and appropriate retention before real client use.

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
4. A page is only marked `confirmed` if the full name, supplied city and supplied employer occur in the page text and the model assessment links them to the same person. Without an employer, matches remain `possible`. Initials alone never confirm identity. A strong match still requires human review.
5. Claims appear only for confirmed matches, with an exact quote present in the retrieved page.
6. The result and PDF are labeled as drafts for human review. There is no automatic risk score or eligibility decision.

The model writes identity reasons and adverse finding summaries in plain, neutral prose, following the useful-text and fact-preservation principles of [blader/humanizer](https://github.com/blader/humanizer) (MIT). Source quotes stay verbatim. A reviewer must still check whether each summary accurately reflects its source.

Crawl4AI is an optional fallback for pages with little readable HTML. Install it separately and set `ENABLE_CRAWL4AI=1` after reviewing browser navigation controls. PDF and paywalled sources are outside the current default fetcher.

## Railway layout

Deploy **two services from the same repository** in the Amsterdam region:

- Backend: repository root, using the root `Dockerfile`. Keep this service on Railway's private network. Set `SERPER_API_KEY` and `OPENAI_API_KEY` as backend variables. Set `PORT=8000`; `/health` is the health check.
- Backend storage: attach a volume mounted at `/data` and set `KYCX_RUN_DB=/data/research_runs.sqlite3`.
- Frontend: root directory `frontend`, build `npm run build`, start `npm run start`. Set server-side `BACKEND_URL=http://kycx-api.railway.internal:8000`, `KYCX_ACCESS_PASSWORD`, and `KYCX_SESSION_SECRET`. Do not use a `NEXT_PUBLIC_` prefix for any of these variables.

The frontend's `/api/research`, `/api/runs`, and `/api/report` routes call the backend from the server, so provider keys are not shipped to the browser. **Before real client use**, add user-specific access control, brute-force protection, appropriate logging without retaining research content, and complete a privacy review. The current app is a reviewable MVP, not a production compliance system. The deployed backend has no public domain. See `OSINT_PLAN.md` for the proposed LangGraph-centered source expansion.

## Files

- `frontend/app/page.tsx` — search and source-review interface
- `frontend/app/globals.css` — visual system and responsive layouts
- `frontend/app/icon.svg` — KYCX favicon
- `frontend/app/login/page.tsx`, `frontend/auth.ts`, `frontend/proxy.ts` — single-admin login and route gate
- `frontend/app/api/*` — server-side proxy routes
- `api.py` — FastAPI service
- `identity_workflow.py` — Serper, retrieval, identity checks, LangGraph
- `evidence_pdf.py` — draft PDF export
- `test_identity_workflow.py`, `test_api.py` — focused checks

The original `researcher.py` and `app.py` remain available for the legacy Streamlit prototype.
