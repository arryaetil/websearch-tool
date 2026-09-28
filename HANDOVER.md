# KYCX handover

## Repository and current state

- GitHub remote: `https://github.com/arryaetil/websearch-tool.git`.
- This working tree contains the new Next.js frontend and FastAPI/LangGraph adverse media workflow. Check `git status` and the latest commit before continuing.
- Public Railway frontend: `https://kycx-adverse-media-production.up.railway.app`. Railway project: `kycx-adverse-media` (`3b9dd43c-a2d3-430e-bfe9-e7cbe965bc6e`). Services: `kycx-adverse-media` frontend and private `kycx-api` backend, both configured for Amsterdam.
- The published login has the original KYCX wordmark centered, no eye icon, centered “Sign in”, and centered official IBC group attribution. The backend timing/cost instrumentation, JSON request fix and balanced Serper search, plus the frontend run-metrics line, are live. Backend deployment `126fc2cf-ed3e-45ee-aaa5-f756e8369b97` and frontend deployment `9d751425-abd9-4fdd-8b0d-a2b515e3dece` both reached `SUCCESS`.
- The private Railway backend has both `SERPER_API_KEY` and `OPENAI_API_KEY` configured. The user explicitly requested setting the OpenAI key on Railway. Do not put secrets in Git, handover text, logs, or screenshots.
- The OpenAI API key was supplied through the clipboard and also saved in the local, Git-ignored `.env`. Do not read or print its value.
- Local Railway access credentials are in the workspace `outputs/kycx-railway-access.txt`; this is deliberately outside the repository and must never be committed or put in the source ZIP.

## Product decisions

- Purpose: adverse media checks on a person, with strong identity matching and source-linked evidence. Search snippets are leads, not findings. Human review is required.
- The app does not store past research runs. Reports exist only in browser memory unless an analyst exports a PDF. Provider and hosting retention still need review before client use.
- Interface copy should be sparse and useful. Official, unaltered IBC logo and technology image are included; Ubuntu and selected IBC colors are used. The original frontend was built manually; the later source-link pass used `npxskillui` as the user requested.
- Crawl4AI is currently an opt-in fallback when a page has little HTML. It may help with JavaScript rendering and difficult layouts. Do not represent CAPTCHA or paywall bypass as a reliable source path; prefer a permitted API, license, or manual review.
- A later frontend pass used `npx skillui@1.3.4` to extract an Attio design reference into the ignored local `skillui-reference/` folder. The source link uses a visible action, linked title and wrapping URL. Do not copy Attio branding over IBC branding.
- The sidebar now contains only the KYCX wordmark, New check and official IBC attribution. The non-functional Sources item and sample walkthrough were removed; the app starts with an empty search form. The eye was removed from the dashboard and favicon.
- Full name plus city alone is now only a candidate match. A strong match requires the supplied full name, city and employer in the source plus the model's same-person assessment. This deliberately lowers recall when no employer is supplied. The UI says “Strong match” rather than “Confirmed match”; human review remains necessary. Source corroboration across independent pages and additional identifiers such as birth year or role are future work.
- Useful open-source candidates: Trafilatura for article text extraction; RapidFuzz for name-variant candidate generation only; Crawl4AI for a browser fallback; OpenSanctions yente for a separate sanctions screening module. Check data licenses separately from code licenses before using OpenSanctions data commercially.

## Benchmark so far

- Authorized test subject: Albert Bril, Bergentheim. Do not store or publish the retrieved page content.
- Previous Serper search implementation: 1.94 s, eight candidate URLs, but it could stop after the first query and miss Dutch and context searches.
- Revised local Serper implementation: three parallel queries, 2.01 s, eight candidate URLs. Results reserve space for English adverse, Dutch adverse, and identity-context searches.
- Revised local search plus HTML retrieval: search 1.94 s; fetch 5.48 s; eight candidate URLs; four readable pages. This is **not** a full end-to-end benchmark because the model key is missing.
- A fictional one-page model assessment took 4.52 s, using 350 input and 122 output tokens. Its estimated model cost at GPT-4.1 mini list rates is about $0.00034. Real pages can be much longer, so this is not a per-run estimate.
- The first fictional call revealed an OpenAI JSON-format request error; `identity_workflow.py` now explicitly asks for JSON in the input and a regression test covers it.
- An attempted real-person end-to-end benchmark was rejected by automatic approval review: sending Albert Bril's identity data and potentially sensitive source text to OpenAI requires explicit authorization for that specific transfer. A user question is pending. Do not work around the rejection or run that test before explicit approval.
- Serper Starter list price is $1/1,000 successful queries, so three searches are approximately $0.003 before tax. The local code estimates GPT-4.1 mini cost from actual reported input, cached-input and output tokens at $0.40, $0.10 and $1.60 per million respectively. This is an estimate, not an invoice, and excludes hosting. Official pricing: `https://serper.dev/#pricing` and `https://developers.openai.com/api/docs/models/gpt-4.1-mini`.
- The current page retrieval and model assessments are sequential. After obtaining a real full-run baseline, consider bounded parallelism, with rate-limit and source-quality checks. Avoid cutting identity evidence solely to save tokens.

## Next steps

1. The KYCX commits were pushed to `main` at `https://github.com/arryaetil/websearch-tool`. A `git clone` of `arryaetil/KYC4etil` was blocked earlier because the approval reviewer hit its usage limit. Obtain and inspect that repository when access resumes; do not use `app.py` in this repo as a substitute because it is a different company-research prototype.
2. After explicit user approval for transferring the real-person source text, run a controlled end-to-end benchmark on the agreed test case. Record stage times, token counts, source coverage, and estimated cost. Never print the key or raw personal research to logs. If approval is not given, continue with fictional data only.
3. Redeploy the local timing/cost instrumentation and balanced search to both Railway services after validation. Confirm the latest deployments reach `SUCCESS` and test the public page.
4. Benchmark the older KYC4etil Streamlit workflow on the same subject and environment, including provider calls and source coverage. Report both latency and output quality; do not claim improvement from different workloads.
5. Evaluate Crawl4AI on a few permitted, JavaScript-heavy sources. Keep ordinary HTML as the default and measure fallback frequency and delay.

## Validation

- `python -m pytest -q test_api.py test_identity_workflow.py` — ten passing tests after the JSON request fix.
- `cd frontend; npm run build` — passed after adding the metrics display.
- The deployed frontend and backend versions before the instrumentation both reached Railway `SUCCESS`.

## Packaging

- `outputs/kycx-research-mvp.zip` is a source archive generated with `work/package_mvp.py`. Regenerate it after changes. It excludes `.env`, `audit_log.jsonl`, `.git`, `.next`, and `node_modules`.
- Keep deliverables in the workspace `outputs` directory; keep temporary analysis under `work`.
