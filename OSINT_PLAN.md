# KYCX OSINT plan (brainstorm; no new OSINT integrations deployed)

## Product boundary

The question is whether verifiable adverse information concerns the screened person. A name or shared username is a lead, never proof. Every match needs provenance, a retrieval date, corroborating identity attributes, contradictions, and analyst review. The product should display evidence and uncertainty, not label someone criminal from an unverified online account.

## LangGraph remains the core

Today the graph is `search -> fetch -> assess -> assemble`. Proposed graph:

1. **Input and purpose** — subject identifiers, check purpose, authorized source categories, search budget.
2. **Plan searches** — variants and targeted queries by source type, with bounded fan-out.
3. **Collect evidence in parallel** — news, official registers, sanctions/PEP, corporate records, and permitted public professional profiles. Each adapter returns the same source and provenance schema.
4. **Extract and normalize** — article text, entity names, dates, roles, locations, organizations, URLs, and exact supporting passages. Keep source snapshots/hashes only when justified.
5. **Resolve identity** — cluster candidate people; compare multiple identifiers and contradictions. Branch ambiguous cases to `needs_review`, not `strong_match`.
6. **Assess adverse relevance** — distinguish allegations, charges, convictions, sanctions, civil disputes, and unrelated mentions. Record event date and source reliability; no automatic guilt inference.
7. **Corroborate** — detect duplicated articles and copied claims, seek independent sources, and record conflicting facts.
8. **Human review interrupt** — analyst accepts/rejects identity links and findings before a final decision. Store the analyst's reason separately from the model output.
9. **Assemble report and metrics** — findings with clickable citations, uncertainty, missing coverage, timing, query count and provider cost.

LangGraph should control routing, retries, fan-out, review interrupts and state transitions. Search engines, extractors, matching rules and models remain replaceable tools inside graph nodes. Deterministic gates should prevent an LLM's unsupported identity or adverse conclusion from becoming a finding.

## Candidate sources, in order of value

| Source category | Possible contribution | First step |
| --- | --- | --- |
| News and investigative reporting | Adverse event and direct source links | Improve current Serper discovery, freshness and duplicate handling |
| Official sanctions and enforcement notices | Verifiable listed entity and action | Evaluate official lists or licensed OpenSanctions data; match extra identifiers |
| Company and director registers | Employer, directorship, place and entity relationships | Assess jurisdiction-specific access, licensing and update cadence |
| Court and regulator publications | Proceedings, decisions and dates | Limit to available official records; distinguish allegation from final outcome |
| Insolvency and disqualification registers | Relevant business history | Scope to the customer's due-diligence purpose |
| PEP sources | Public office and related exposure | Treat as a separate risk category, never inherently adverse |
| Public professional profiles and company websites | Job role, employer, location and career timeline for identity resolution | Use as corroboration; verify accounts before linking |
| Public social profiles and posts | Occasionally corroborate identity or a directly relevant event | Do not build broad behavioral monitoring; require purpose and source review |
| Ownership, domain and organization relationships | Connect a person to a relevant entity | Treat shared names/handles as tentative links |
| Licensed threat-intelligence or illicit-market indicators | Potential lead involving an account or entity | Only consider a compliant provider, provenance and independent identity corroboration; do not treat a username as proof |
| Breach exposure services | Account security exposure | Usually not an adverse-media signal; do not interpret victimization as misconduct |

## MVP sequence

1. Save short-lived evaluation runs (7 days, max 100), with delete controls and a persistent Railway volume. Use fictional or otherwise authorized cases for comparison.
2. Add structured identity clues and explicit conflicting clues to source assessments. Test homonyms, copied articles and weak city-only matches.
3. Add one high-value official source adapter, likely sanctions/enforcement, after checking commercial data terms and exact customer purpose.
4. Add candidate-person clustering and a review queue in LangGraph. Compare precision, recall, source coverage, run time and cost to the current graph.
5. Consider public professional-profile corroboration. Keep social activity and illicit-market signals outside the MVP until source reliability, access rights and the customer's legal basis are established.

## Evaluation criteria

Measure false person matches first, then missed relevant findings, unsupported claims, source freshness, analyst review time, latency and cost. Use paired cases against the existing workflow. A negative result must say which sources were searched; it must never imply complete clearance.

## Governance questions before expanding sources

Define the exact client purpose and legal basis; whether criminal-offence data is processed; source terms and commercial licenses; data-subject transparency and correction process; model/provider transfers; access controls; retention; and whether a DPIA is required. This plan is product design, not a legal determination.

References: [EDPB principles](https://www.edpb.europa.eu/topics/key-gdpr-concepts/basic-principles_en), [AP legal bases](https://autoriteitpersoonsgegevens.nl/themas/basis-avg/avg-algemeen/grondslagen-avg-uitgelegd), [OpenSanctions licensing](https://www.opensanctions.org/docs/api/), [HIBP API](https://haveibeenpwned.com/API/v3), [OCCRP Aleph](https://docs.aleph.occrp.org/).
