# KYCX handover

Updated 29 September 2026. This file is shareable on GitHub. Full evaluation inputs, outputs, source links and private analyst notes stay in Git-ignored `data/`; do not copy them into the repository.

## Objective and current evidence

Build an evidence-first person check with LangGraph as the orchestration layer. The old Streamlit **person** researcher used Perplexity `sonar-deep-research`; its separate company researcher used OpenAI. The user chose an interim comparison with the old person prompt/schema on GPT-5.1 + hosted web search because a Perplexity key was unavailable. See `PERSON_RESEARCH_PARITY.md` and the shareable `COMPARISON_REPORT.md`.

Three preliminary paired measurements were made: a historical positive control, a public negative control, and one specifically approved personal case. The personal case exposed a material quality gap: hosted web search produced relevant findings, while LangGraph found related sources but did not confirm the identity link. **Do not claim outcome-quality parity.** Cost estimates suggest LangGraph is cheaper, but workload and source availability varied, so do not claim a stable speed advantage. Four further proposed person cases lack enough verified identifying context; do not select arbitrary namesakes or imply that work about fraud is personal wrongdoing.

The user specifically approved the personal case's name, location, alias, organisation, public source text, OpenAI and Serper transfers after an earlier automatic approval rejection. The retry succeeded. Approval for this named transfer does not resolve which identity is meant for the other four cases. A request for place, organisation or source link for those cases is pending.

## Code and architecture

- `identity_workflow.py` builds `intake -> (search -> fetch | sanctions | BIG register) -> identity -> follow_leads -> adverse -> archive -> assemble`. Serper searches Dutch/English terms, official sites, aliases, employers and context. A bounded second pass follows source-quoted company or court leads. `search_trace` records queries and hit counts.
- Up to 24 candidate URLs are available to obtain at most eight readable initial pages; up to four follow-up pages can be assessed. HTML and PDF text are fetched with bounded parallelism, then source assessments run in parallel. Source text is untrusted, quotations must occur verbatim, and deterministic rules classify identity. A possible identity does not produce a confirmed adverse finding.
- The analyst interface now shows source-extracted `candidate_claims` for possible identity matches as items to review. They are separate from confirmed findings; the user must confirm identity before relying on them.
- `identity_rules.py` covers Dutch abbreviated names, supplied aliases, common nicknames, middle names, city/employer/age/profession checks. A different company is now missing corroboration rather than a contradiction. A quote that explicitly names another person cannot supply the subject's city. Regression tests cover these errors. These are safeguards, not proof of correct identity on every source.
- `benchmark_person_research.py` performs paired local runs from a case JSON under `data/`, records timing and usage, and keeps complete output outside Git. It prunes comparison JSON older than seven days on the next harness run. No benchmark key or case input belongs in Git.
- A compiled Python cache file that had accidentally been tracked was removed from Git's index; the local copy remains ignored.

## Validation and deployment

- `python -m pytest -q -p no:cacheprovider test_identity_rules.py test_identity_workflow.py test_api.py`: 41 passed before the current commit. Run again after edits.
- The public frontend is `https://kycx-adverse-media-production.up.railway.app/login`. Railway project ID `3b9dd43c-a2d3-430e-bfe9-e7cbe965bc6e`; backend service `kycx-api`, frontend service `kycx-adverse-media`.
- Current successful deployments: backend `80a0f456-8e8f-444c-be9c-91b26240dba7`, frontend `942bea97-3738-4b52-86d6-a310efab9ff4`. PDF, search, parallelism and candidate-claims changes are live. Deploy future backend changes from repository root with `railway up --service kycx-api --detach --json`; poll deployment status. Deploy frontend changes with `railway up ./frontend --path-as-root --service kycx-adverse-media --detach --json` from the repository root. A prior frontend deployment from the wrong directory caused `/login` 404.
- The app stores evaluation runs for seven days in the private backend's SQLite volume. This retention is an evaluation default, not a legal determination. The shared admin credential exposes all saved runs to every holder.
- Backend credentials are already configured on Railway. Local `.env` is Git-ignored. Never print or commit keys. `data/` is also ignored.

## Next work

1. The approved personal case after the city-attribution rule still has a recall gap: all eight evaluated sources remained possible matches, with zero confirmed findings. Do not relax identity thresholds merely to inflate findings. Evaluate a conditional deeper-search step with source corroboration.
2. Obtain reliable identity anchors for the remaining proposed cases. Build an analyst-reviewed reference set with both correct persons and namesakes, then compare false links, missed material findings, quote validity, time and cost.
3. Consider a conditional deeper-search branch in LangGraph for unresolved cases. It can improve recall at a higher cost, but any output still needs source-linked verification and clear review status.
