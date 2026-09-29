# Person-check comparison: shareable summary

Measured on 29 September 2026. Full case inputs, outputs, source URLs, and detailed analyst notes are stored only in the Git-ignored `data/` directory. Do not copy them into a public repository. The original Streamlit **person** baseline used Perplexity `sonar-deep-research`. This interim comparison instead uses the old person prompt/schema with OpenAI GPT-5.1 and hosted web search, as requested by the user.

| Case | Purpose | Web search | LangGraph | Estimated variable cost: web search / LangGraph |
| --- | --- | ---: | ---: | ---: |
| H1 | Historical public positive control | 72.19 s | 76.45 s | $0.06274 / $0.02412 |
| N1 | Public negative control: distinguish work *about* fraud from personal misconduct | 41.29 s | 33.89 s | $0.04566 / $0.02237 |
| C1 | User-approved personal check | 51.34 s | 25.41 s | $0.05729 / $0.01924 |

The costs are estimates from API usage and published list rates, not invoice totals. GPT-5.1 token rates and the web-search call price come from the [model page](https://developers.openai.com/api/docs/models/gpt-5.1) and [pricing page](https://developers.openai.com/api/docs/pricing). The LangGraph estimate uses the app's configured Serper and GPT-4.1 mini rates; hosting is excluded.

## What the measurements show

- LangGraph exposes each search query, stage timing, model usage and a source-level identity card with exact quotes. OpenAI's hosted [web-search response](https://developers.openai.com/api/docs/guides/tools-web-search) also exposes a search action and, in these runs, its search queries. LangGraph gives more control over individual steps; the hosted search is not wholly opaque.
- Both methods avoided a false personal misconduct conclusion in N1. The initial LangGraph identity rules nevertheless mishandled a nickname, a middle name and an employer acronym in the control cases. Regression tests now cover those failures.
- C1 is the decisive quality gap: the hosted search produced a relevant narrative, while LangGraph found related sources but did not establish a strong enough identity link for confirmed findings. Faster and cheaper is not sufficient. The full private report records the source-level reasons and the remaining analyst questions.
- Parallel retrieval and assessment reduced elapsed time in follow-up H1 runs, but the number of readable pages varied. A speed claim requires matched workload and repeated runs. Reserve URLs and PDF extraction were added to improve coverage before another paired test.

## Decision and next measurement

Outcome quality has **not** reached the required parity. The next paired run should use a frozen case set with independent identity references and analyst-reviewed material findings. For each case record false links, missed material sources, quote support, elapsed time, model/tool usage, estimated and invoiced cost where available, and provider errors. Do not compare the old 0–100 confidence score numerically with LangGraph's per-source 0–3 identity tier. The four remaining user-suggested cases require reliable identity anchors before model evaluation.

## Update after the review agent (29 September 2026, afternoon)

LangGraph now has a separate review agent that returns the original researcher's 0–100 score and verdict with source-cited sections. Same three cases, same inputs, run minutes apart:

| Case | Time: original / LangGraph | Estimated cost: original / LangGraph | Verdict: original / LangGraph | Visible queries | Claims with verbatim quote and URL |
| --- | ---: | ---: | --- | ---: | --- |
| H1 | 68.2 s / 67.5 s | $0.066 / $0.065 | Very High / Very High | 4 / 11 | not in schema / 19 of 19 |
| N1 | 58.6 s / 52.8 s | $0.055 / $0.045 | Very High / Very High | 4 / 11 | not in schema / none |
| C1 | 67.9 s / 115.6 s | $0.057 / $0.097 | High / Very High | 4 / 13 | not in schema / 21 of 21 |

The review ran on GPT-5.1 here; in C1 the deeper-search loop ran it twice (75 s). A replay of the review on identical evidence compared five models:

| Review model | Seconds per review | USD per review | Verdicts | Section items (H1 / N1 / C1) |
| --- | ---: | ---: | --- | --- |
| gpt-5.1 | 25–42 | 0.021–0.036 | all Very High | 13 / 8 / 15 |
| gpt-5.6-luna | 19–22 | 0.003–0.004 | all Very High | 13 / 7 / 15 |
| gpt-5.6-terra | 19–28 | 0.026–0.039 | all Very High | 6 / 8 / 12 |
| gpt-6-luna | 16–24 | 0.002 | all Very High | 6 / 7 / 12 |
| gpt-6-sol | 28–39 | 0.025–0.034 | all Very High | 7 / 8 / 13 |

**Decision:** the review agent now defaults to `gpt-5.6-luna`. All three cases concern the intended person, so this replay does not test whether a model rejects a namesake; a namesake case is still required. Risk flags differ: the original lists adverse items as flags, while LangGraph keeps unconfirmed-identity items under review because per-source rules found no strong source in C1.

## Repeated runs and namesake test (review agent on gpt-5.6-luna)

Three runs per case, run consecutively on 29 September 2026. Median (minimum–maximum):

| Case | Runs | Seconds: original / LangGraph | Estimated USD: original / LangGraph | Verdicts: original / LangGraph |
| --- | ---: | --- | --- | --- |
| H1 | 3 | 40.3 (31.3–47.7) / 51.0 (49.6–56.5) | 0.055 (0.051–0.071) / 0.037 (0.031–0.039) | Very High / Very High |
| N1 | 3 | 34.3 (33.7–37.4) / 42.3 (33.5–45.2) | 0.048 (0.047–0.054) / 0.026 (0.021–0.027) | Very High / Very High |
| C1 | 3 | 40.2 (39.1–49.9) / 89.5 (80.9–101) | 0.060 (0.057–0.065) / 0.043 (0.042–0.046) | High / Very High |
| Namesake of H1 | 1 | 19.2 / 78.5 | 0.037 / 0.031 | Low / Low |

The namesake case uses H1's public name with a fictional city, employer and birth year. Both approaches rejected the link (original 20 Low, LangGraph 8 Low); LangGraph linked no findings. LangGraph is cheaper in every case but slower, mainly because the deeper-search loop runs a second review in C1 and in the namesake case. The original's hosted-search latency varied between morning and afternoon runs (about 68 s versus 40 s), so single runs do not support a speed claim.
