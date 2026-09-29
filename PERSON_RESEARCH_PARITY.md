# Person researcher: Perplexity baseline and LangGraph parity

The user's pasted Streamlit implementation is the baseline for the **person** check. It calls Perplexity `sonar-deep-research` through the OpenAI-compatible Python client. Its separate company researcher calls OpenAI `gpt-5.1` with web search. The client library alone does not identify the provider.

## Baseline behavior

- Search Dutch and English, including full names, first initials, abbreviated surnames and compound names.
- Follow relevant company, court, insolvency, professional and social-profile leads.
- Separate same-name people, state identity uncertainty, report adverse facts as allegations where appropriate.
- Return identity matches, professional profiles, media, legal records, business records, social presence, risk flags, a confidence score/reason, searched name forms and source URLs.

## Current LangGraph implementation

`intake -> (search -> fetch | sanctions | BIG register) -> identity -> follow_leads -> adverse -> archive -> assemble`.

Initial Serper queries cover English and Dutch adverse terms, official sites, name forms, employer/context and identity context. The graph reserves positions across query groups for up to 12 candidate URLs. A model extracts source facts and exact quotes; deterministic rules classify identity. Up to two quoted company/court leads trigger one further search pass and up to four additional source assessments. Query text and hit counts appear in `search_trace`. Each source assessment carries its own identity card and evidence. The graph does not infer guilt or treat an unverified possible identity as a confirmed finding.

## Quality gate before claiming parity

Run the old and new person researchers on the **same approved cases**, with the same inputs and as close in time as possible. Use a set that includes full-name matches, Dutch abbreviated names, nicknames, namesakes, linked businesses/court cases, and cases with little public information. Have an analyst mark a reference set of source URLs, identity labels and material findings before comparing model output. Record:

1. Relevant-source recall and important finding recall, especially abbreviated-name cases.
2. False person links and unsupported adverse assertions. These are release blockers.
3. Citation validity: accessible source URL and a quote that supports each claim.
4. Coverage and explicit uncertainty when sources are inaccessible.
5. End-to-end elapsed time, Serper queries, model calls/tokens and actual provider billing for each case.

At present there is **no paired benchmark** against Perplexity and no evidence that LangGraph meets or exceeds its outcome quality. The current confidence score is a per-source, rule-based identity tier (0–3), not the old researcher's 0–100 report score; do not compare the numbers directly. The LangGraph implementation also does not yet return all of the baseline's professional, business and social-profile sections. Those fields need source-linked implementation if the product requires full report parity beyond the adverse-media person check.

## Comparison report to produce

For each approved test case, capture the same input, execution time and date, provider/model versions, and any source changes between runs. Report side-by-side:

| Dimension | Measurement |
| --- | --- |
| Identity quality | Correct matches, false matches, unresolved matches and analyst rationale |
| Finding quality | Material findings found/missed, unsupported claims, allegation versus conviction wording |
| Evidence | Working URLs, quote support, independent corroboration and inaccessible pages |
| Search coverage | Name forms, languages, query count, relevant-source recall, follow-up leads |
| Traceability | Visible queries, source-to-claim path, identity decision factors, stage errors |
| Speed | Median and 90th-percentile total time, plus search/fetch/model stage times |
| Cost | Actual Perplexity invoice/usage where available; Serper credits, model tokens, hosting allocation and cost per completed run |
| Reliability | Provider errors, timeouts, partial results and repeat-run variation |
| Privacy | Data sent to each provider, stored result lifetime, access and deletion behavior |

Show raw per-case values, aggregate summaries and a short failure analysis. If Perplexity does not expose exact search queries or usage charges per run, mark those cells **unavailable** rather than estimate them as measured facts. A lower score or faster run cannot compensate for a false person link or an unsupported adverse finding.
