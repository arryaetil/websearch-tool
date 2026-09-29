# KYCX handover

## Latest state (29 September 2026)

- A liquid-glass refinement was added to the login card, input fields, navigation and search controls using translucent blue surfaces, backdrop blur, reflected top edges and the existing official IBC technology image. Source text/detail stays on an opaque dark plane for reading. Desktop (1280px) and mobile (390px) browser previews were inspected; `npm run build` passed and the Impeccable detector returned `[]`. Frontend Railway deployment `41d9dc43-a7b6-4367-98f2-c8e86f27908f` reached `SUCCESS`, and the public login was visually verified.
- The user still wants 40/40 on Impeccable. Do not claim this from a clean detector or visual refinement. Prior independent Nielsen estimate was 28/40, technical audit 13/20. Next pass: show analyst review status/limitations and evidence trace for each risk flag; clarify the report-level identity score; improve mobile menu focus/ARIA, progress/recovery, source coverage and keyboard/screen-reader testing; then commission independent re-score with authenticated flow access.

- GitHub `main` is at `40f8900` (`Search on nicknames and shortened names, add Known as field`) when checked. Working tree was clean. Read `git log -5` before editing because work has continued beyond the older history below.
- Latest frontend Railway deployment observed: `4b88426c-57c0-4f1d-abb7-fb8d4a1d036e`, status `SUCCESS`. The API and frontend have since gained Dutch source modules, a rule-based identity card, grouped risk flags, nickname matching and a Known as input. Check the current deployed API revision before claiming a particular feature works end to end.
- `OSINT_PLAN.md` now prioritizes KVK extracts as a business-person identity anchor, BIG/NOvA for regulated professions, and official EU sanctions as a separate adverse source. KVK company-search API is not a general person-identity lookup. Rechtspraak generally pseudonymizes natural persons. Keep LangGraph as the routing and evidence workflow.
- The Impeccable follow-up used two independent read-only agents. Nielsen UX estimate improved from 20/40 to 28/40 based on code, with no authenticated browser validation; technical audit was 13/20. The bundled detector returned `[]`. Remaining concerns were report-level score ambiguity, mixing substantive flags with review warnings, visibility of review/coverage limitations, and mobile menu accessibility. Do not claim 40/40.

The sections below record earlier decisions and may describe older deployments or pre-integration behavior; use the latest code and deployment status for current facts.

## Repository and current state

- GitHub remote: `https://github.com/arryaetil/websearch-tool.git`.
- This working tree contains the new Next.js frontend and FastAPI/LangGraph adverse media workflow. Check `git status` and the latest commit before continuing.
- Public Railway frontend: `https://kycx-adverse-media-production.up.railway.app`. Railway project: `kycx-adverse-media` (`3b9dd43c-a2d3-430e-bfe9-e7cbe965bc6e`). Services: `kycx-adverse-media` frontend and private `kycx-api` backend, both configured for Amsterdam.
- The published login has the original KYCX wordmark centered, no eye icon, centered “Sign in”, and centered official IBC group attribution. The workspace cleanup, source links and stricter identity logic are live. Storage backend deployment `8f7e8848-13ff-4732-b3df-1050dbb6e6b4` reached `SUCCESS`. The frontend was accidentally overwritten with the backend by `railway up` from the `frontend` working directory, causing a FastAPI 404 on `/login`. It was restored with `railway up ./frontend --path-as-root --service kycx-adverse-media` from the repository root; deployment `14f3d9e7-734f-4647-ad53-05c489b1f562` reached `SUCCESS`, and `/login` returned HTTP 200 with Next.js HTML. Always use the explicit path-as-root command for future frontend deploys.
- The private Railway backend has both `SERPER_API_KEY` and `OPENAI_API_KEY` configured. The user explicitly requested setting the OpenAI key on Railway. Do not put secrets in Git, handover text, logs, or screenshots.
- The OpenAI API key was supplied through the clipboard and also saved in the local, Git-ignored `.env`. Do not read or print its value.
- Local Railway access credentials are in the workspace `outputs/kycx-railway-access.txt`; this is deliberately outside the repository and must never be committed or put in the source ZIP.

## Product decisions

- Purpose: adverse media checks on a person, with strong identity matching and source-linked evidence. Search snippets are leads, not findings. Human review is required.
- The user now authorizes short-lived evaluation storage. New code stores successful reports in SQLite for seven days, max 100, with reopen/delete/clear controls. Railway volume `d749466d-fd9d-471b-b959-eb398b063b92` is attached to private `kycx-api` at `/data`, and `KYCX_RUN_DB=/data/research_runs.sqlite3` is set. Confirm deployment status before telling the user it is live. The shared admin credential exposes all saved runs to every holder; this remains a controlled evaluation feature.
- The user requested OSINT brainstorming with LangGraph central. No OSINT source was integrated. `OSINT_PLAN.md` lists source candidates, graph nodes, evaluation criteria and governance questions. A username or online account is only a lead, not evidence of misconduct or person identity.
- The user requested more liquid-glass visual style. The deployed CSS adds translucent structural surfaces and blue/violet depth while keeping source reading text on an opaque plane. The build passed; browser visual QA was blocked by `ERR_BLOCKED_BY_CLIENT`, so inspect visually when a browser connection is available.
- The user pointed to [pbakaus/impeccable](https://github.com/pbakaus/impeccable) for frontend design. It has a Codex-compatible skill, design critique/audit/distill/polish/adapt commands and optional browser iteration. The skill was not installed, but `npx --yes impeccable detect --json frontend` was run locally. It flagged two CSS patterns: `Inter` in the first `:root` declaration (overridden later by Ubuntu) and a left border on `.quote` (an evidence quotation, not a card). Review these in a targeted design pass; do not blindly follow warnings. Preserve IBC branding, useful-only copy and evidence readability. The repo is Apache-2.0.
- Interface copy should be sparse and useful. Official, unaltered IBC logo and technology image are included; Ubuntu and selected IBC colors are used. The original frontend was built manually; the later source-link pass used `npxskillui` as the user requested.
- Crawl4AI is currently an opt-in fallback when a page has little HTML. It may help with JavaScript rendering and difficult layouts. Do not represent CAPTCHA or paywall bypass as a reliable source path; prefer a permitted API, license, or manual review.
- A later frontend pass used `npx skillui@1.3.4` to extract an Attio design reference into the ignored local `skillui-reference/` folder. The source link uses a visible action, linked title and wrapping URL. Do not copy Attio branding over IBC branding.
- The sidebar contains the KYCX wordmark, New check, saved checks and official IBC attribution. The non-functional Sources item and sample walkthrough were removed; the app starts with an empty search form. The eye was removed from the dashboard and favicon.
- Full name plus city alone is now only a candidate match. A strong match requires the supplied full name, city and employer in the source plus the model's same-person assessment. This deliberately lowers recall when no employer is supplied. The UI says “Strong match” rather than “Confirmed match”; human review remains necessary. Source corroboration across independent pages and additional identifiers such as birth year or role are future work.
- Any results generated before the stronger matching rule, including the user's earlier Albert Bril check, should be reviewed again under the new rule before relying on a person link.
- Useful open-source candidates: Trafilatura for article text extraction; RapidFuzz for name-variant candidate generation only; Crawl4AI for a browser fallback; OpenSanctions yente for a separate sanctions screening module. Check data licenses separately from code licenses before using OpenSanctions data commercially.
- [plutopulp/adverse-media-screening](https://github.com/plutopulp/adverse-media-screening) is a close application reference: it screens one analyst-supplied article URL against person details and explains matching. It does not replace KYCX's multi-source discovery and saves results by default. The README calls it a technical assessment, and a clear code license was not visible in the repository root; do not copy code into KYCX without checking permission.
- [kingsleyweb-tech/OSINT-APP](https://github.com/kingsleyweb-tech/OSINT-APP) is a person-research reference for collecting profiles and clustering likely identities. It uses SerpApi and persists investigations in Firebase, so it conflicts with KYCX's current Serper integration and no-history decision. Its license needs checking before copying code. Reuse the ideas of identity clusters and corroborating attributes, not its storage or search stack wholesale.
- [alephdata/aleph](https://github.com/alephdata/aleph) is a mature investigative document and entity platform, suited to large internal corpora rather than this lightweight check workflow. Its code is MIT-licensed, but deployment and integration would be substantial.

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

- `python -m pytest -q -p no:cacheprovider test_api.py test_identity_workflow.py` — 12 tests passed, including persistence and expiration.
- `cd frontend; npm run build` — passed after adding the metrics display.
- The deployed frontend and backend versions before the instrumentation both reached Railway `SUCCESS`.

## Current frontend and evidence-score pass (28 September 2026)

- The Impeccable critique used two independent subagents and found a 20/40 baseline on Nielsen heuristics. This is a subjective UX assessment, not an automated pass/fail test. The first follow-up removed redundant summary cards and the subtitle under the KYCX wordmark on login and dashboard, improved evidence links, filter empty states, deletion confirmation, readability, focus and tablet layout. The technical audit and independent rescore remain to be completed.
- `identity_workflow.py` now adds a per-source `confidence_score` from 0–3: 0 no person link, 1 full name only, 2 full name and city but still unresolved, 3 full name, city and employer with the model's same-person assessment. This is an evidence tier, not a probability or misconduct score. It also adds report `risk_flags` for linked adverse reporting, unresolved identity and source coverage gaps. Flags come from verified source quotes/identity status, not general web-search snippets. Older saved checks do not have these fields and should be rerun for a score.
- The frontend shows these fields; no flag means no flag in reviewed sources, not clearance. Both services were deployed successfully to Railway: backend `c00bea01-b5ae-495a-a3d4-e60c6ac1b613`, frontend `ec49b06b-ca38-4982-8294-df68ae1cef79`. The public `/login` returned HTTP 200 and the removed subtitle was absent. Deploy backend from repo root with `railway up --service kycx-api --detach --json` (the explicit `.` path returns `prefix not found` on CLI 5.8); deploy frontend from repo root with `railway up ./frontend --path-as-root --service kycx-adverse-media --detach --json`. Running frontend deploy from inside `frontend` without `--path-as-root` previously uploaded the API and caused `/login` 404.
- `test_identity_workflow.py` has regression tests for score tiers and flags; 13 backend tests pass. TypeScript `npx tsc --noEmit` passes. Local `next build` compiles successfully but final worker spawning is blocked with `EPERM` in the current sandbox; repeat in Railway build.
- A fictional local browser case verified that a zero-result source filter clears the prior source detail. No real person data was used for this UI test.
- OSINT Framework is a discovery catalogue, not a data provider. Its current repository lists tool status, pricing, API and access metadata. Evaluate official registers and licensed sources before social-account or illicit-market leads; keep LangGraph routing and identity validation central. See `OSINT_PLAN.md`.

## Packaging

- `outputs/kycx-research-mvp.zip` is a source archive generated with `work/package_mvp.py`. Regenerate it after changes. It excludes `.env`, `audit_log.jsonl`, `.git`, `.next`, and `node_modules`.
- Keep deliverables in the workspace `outputs` directory; keep temporary analysis under `work`.
