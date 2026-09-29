import json
import unittest
from unittest.mock import MagicMock, patch

import review_agent
from identity_workflow import route_after_review, build_graph


def source(url, identity, tier, candidate=()):
    return {"url": url, "title": "Story", "identity": identity, "confidence_score": tier,
            "identity_card": {"name": {"status": "partial", "quote": "Jan de V."}}, "reason": "rule",
            "claims": [], "candidate_claims": list(candidate)}


def client_returning(payload):
    client = MagicMock()
    client.responses.create.return_value.output_text = json.dumps(payload)
    client.responses.create.return_value.usage = MagicMock(input_tokens=1000, output_tokens=200)
    return lambda: client


STATE = {"name": "Jan de Vries", "city": "Zwolle", "aliases": ["appie"], "search_trace": [],
         "assessments": [source("https://a.example", "possible", 2), source("https://b.example", "possible", 2)]}


class ReviewAgentTests(unittest.TestCase):
    def test_reviewer_decides_with_original_verdicts(self):
        review, metrics = review_agent.run_review(STATE, client_returning(
            {"score": 88, "summary": [{"text": "Both reports describe a Zwolle director.", "refs": ["S1", "S2"]}]}))
        self.assertEqual(review["score"], 88)
        self.assertEqual(review["label"], "Very High")
        self.assertEqual(review_agent.label_for(70), "High")
        self.assertEqual(review_agent.label_for(45), "Moderate")
        self.assertEqual(metrics["review_input_tokens"], 1000)

    def test_score_stays_low_when_no_source_carries_the_name(self):
        state = {**STATE, "assessments": [source("https://x.example", "unrelated", 0)]}
        review, _ = review_agent.run_review(state, client_returning({"score": 90, "summary": []}))
        self.assertEqual(review["score"], 44)

    def test_invalid_refs_and_guilt_language_are_dropped(self):
        review, _ = review_agent.run_review(STATE, client_returning({"score": 40, "summary": [
            {"text": "He is guilty of fraud.", "refs": ["S1"]},
            {"text": "An unrelated claim.", "refs": ["S9"]},
            {"text": "One report says the director was fined.", "refs": ["S1"]},
        ]}))
        self.assertEqual([s["text"] for s in review["summary"]], ["One report says the director was fined."])

    def test_sections_keep_only_cited_records(self):
        review, _ = review_agent.run_review(STATE, client_returning({"score": 50, "summary": [], "business_records": [
            {"entity": "Voorbeeld Bouw BV", "role": "director", "status": "bankrupt", "source": "news", "refs": ["S2"]},
            {"entity": "Invented BV", "role": "owner", "status": "active", "source": "?", "refs": []},
        ]}))
        self.assertEqual([r["entity"] for r in review["sections"]["business_records"]], ["Voorbeeld Bouw BV"])
        self.assertEqual(review["sections"]["media_mentions"], [])

    def test_deeper_queries_must_name_the_subject(self):
        queries = review_agent.safe_queries(
            ['"Jan de V." "Voorbeeld Bouw"', "cheap flights zwolle", '"Appie" Zwolle makelaar', "x" * 200], STATE, set())
        self.assertEqual(queries, ['"Jan de V." "Voorbeeld Bouw"', '"Appie" Zwolle makelaar'])

    def test_model_failure_falls_back_to_a_plain_summary(self):
        def broken():
            raise RuntimeError("offline")
        review, metrics = review_agent.run_review(STATE, broken)
        self.assertIsNone(review["score"])
        self.assertEqual(review["label"], "Unavailable")
        self.assertIn("2 sources assessed", review["summary"][0]["text"])
        self.assertEqual(metrics, {})

    def test_no_evidence_needs_no_model_call(self):
        review, _ = review_agent.run_review({"name": "Jan de Vries", "assessments": []}, lambda: 1 / 0)
        self.assertEqual((review["score"], review["label"]), (0, "No relevant sources"))

    def test_likely_identity_surfaces_candidate_claims_as_review_flags(self):
        from identity_workflow import assemble
        claim = {"summary": "A deal with prosecutors was reported.", "quote": "deal", "type": "settlement"}
        items = [source("https://a.example", "possible", 2, [claim]), source("https://b.example", "possible", 2, [claim])]
        likely = assemble({"name": "Jan de Vries", "city": "Zwolle", "assessments": items,
                           "review": {"score": 90, "label": "Very High"}})["report"]
        flag = next(f for f in likely["flags"] if f["code"] == "likely_reported_settlement")
        self.assertEqual((flag["group"], len(flag["source_urls"])), ("review", 2))
        self.assertEqual((flag["severity"], flag["identity"], flag["mentions"]), ("High", "likely", 2))
        self.assertEqual(len(flag["items"]), 1)  # The same reported fact twice is listed once.
        self.assertEqual(likely["risk_summary"]["level"], "High")
        self.assertEqual(likely["risk_summary"]["identity"], "likely")
        self.assertEqual(likely["confirmed_findings"], [])
        self.assertEqual(len(likely["candidate_findings"]), 2)
        doubtful = assemble({"name": "Jan de Vries", "city": "Zwolle", "assessments": items,
                             "review": {"score": 60, "label": "Moderate"}})["report"]
        self.assertFalse(any(f["code"].startswith("likely_") for f in doubtful["flags"]))

    def test_routing_runs_deeper_search_once_for_unresolved_cases(self):
        wanted = {"review": {"score": 60, "deeper_search": {"needed": True, "queries": ['"Jan de V." Zwolle']}}}
        self.assertEqual(route_after_review({**STATE, **wanted}), "deep_search")
        for clear in (8, 90):  # A clear verdict ends the search.
            self.assertEqual(route_after_review({**STATE, "review": {**wanted["review"], "score": clear}}), "assemble")
        self.assertEqual(route_after_review({**STATE, **wanted, "deep_search_done": True}), "assemble")
        confirmed = {**STATE, "assessments": [source("https://c.example", "confirmed", 3)], **wanted}
        self.assertEqual(route_after_review(confirmed), "assemble")

    def test_graph_loops_through_deeper_search_and_back(self):
        calls = []

        def fake_review(state):
            calls.append(state.get("deep_search_done", False))
            return {"review": {"score": 50, "deeper_search": {"needed": True, "queries": ['"Jan de V." Zwolle']}}}

        pages = [source("https://a.example", "possible", 2)]
        with patch("identity_workflow.search", return_value={"results": []}), \
             patch("identity_workflow.fetch", return_value={}), \
             patch("identity_workflow.check_sanctions", return_value={}), \
             patch("identity_workflow.assess", return_value={"assessments": pages}), \
             patch("identity_workflow.follow_leads", return_value={}), \
             patch("identity_workflow.archive", side_effect=lambda s: {"assessments": s["assessments"]}), \
             patch("identity_workflow.review", side_effect=fake_review), \
             patch("identity_workflow.deep_search", return_value={"deep_search_done": True}):
            report = build_graph().invoke({"name": "Jan de Vries", "city": "Zwolle", "errors": [], "coverage": [], "metrics": {}})["report"]
        self.assertEqual(calls, [False, True])
        self.assertEqual(report["review"]["score"], 50)


if __name__ == "__main__":
    unittest.main()
