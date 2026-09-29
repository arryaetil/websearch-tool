import json
import unittest
from unittest.mock import MagicMock, patch

from identity_workflow import adverse, assess, assemble, build_graph, fetch, fetch_page, follow_leads, safe_public_url, search
from evidence_pdf import generate_evidence_pdf


def person(**facts):
    """Model output where every fact carries the quote that states it."""
    result = {}
    for field, (value, quote) in facts.items():
        result[field] = value
        result["name_quote" if field == "name_as_written" else f"{field}_quote"] = quote
    return result


class IdentityWorkflowTests(unittest.TestCase):
    def page(self, content):
        return {
            "url": "https://example.com/story", "title": "Story", "content": content,
            "retrieved_at": "2026-01-01T00:00:00Z", "sha256": "abc",
        }

    def assess_with_model(self, content, model_result, **subject):
        client = MagicMock()
        client.responses.create.return_value.output_text = json.dumps(model_result)
        client.responses.create.return_value.usage = None
        state = {"name": "Alex Jansen", "city": "Utrecht", "employer": "", "pages": [self.page(content)], **subject}
        with patch.dict("identity_workflow.os.environ", {"OPENAI_API_KEY": "test-key"}), \
             patch("identity_workflow.OpenAI", return_value=client):
            return adverse({"assessments": assess(state)["assessments"]})["assessments"][0]

    def test_initials_and_city_alone_stay_candidate(self):
        item = self.assess_with_model(
            "A. Jansen lives in Utrecht.",
            {"person": person(name_as_written=("A. Jansen", "A. Jansen"), city=("Utrecht", "lives in Utrecht")),
             "claims": [{"summary": "Investigation reported", "exact_quote": "A. Jansen lives in Utrecht.", "type": "allegation"}]},
        )
        self.assertEqual(item["identity"], "possible")
        self.assertEqual(item["confidence_score"], 2)
        self.assertEqual(item["claims"], [])
        self.assertEqual(len(item["candidate_claims"]), 1)
        self.assertTrue(item["adverse_signal"])

    def test_nickname_and_surname_initial_are_not_a_different_person(self):
        content = "De omstreden failliete makelaar Appie B. komt in het bericht voor."
        client = MagicMock()
        client.responses.create.return_value.output_text = json.dumps({
            "person": person(name_as_written=("Appie B.", "makelaar Appie B.")),
            "summary": "The article mentions a realtor called Appie B.",
            "claims": [],
        })
        client.responses.create.return_value.usage = None
        with patch.dict("identity_workflow.os.environ", {"OPENAI_API_KEY": "test-key"}), \
             patch("identity_workflow.OpenAI", return_value=client):
            item = assess({"name": "Albert Bril", "city": "Bergentheim",
                           "pages": [self.page(content)]})["assessments"][0]
        self.assertEqual(item["identity_card"]["name"]["status"], "partial")
        self.assertEqual(item["identity"], "possible")
        self.assertEqual(item["confidence_score"], 1)

    def test_model_request_explicitly_asks_for_json(self):
        client = MagicMock()
        client.responses.create.return_value.output_text = '{"person":{},"claims":[]}'
        client.responses.create.return_value.usage = None
        with patch.dict("identity_workflow.os.environ", {"OPENAI_API_KEY": "test-key"}), \
             patch("identity_workflow.OpenAI", return_value=client):
            assess({"name": "Alex Jansen", "city": "Utrecht", "pages": [self.page("Alex Jansen in Utrecht")]})
        self.assertIn("JSON", client.responses.create.call_args.kwargs["input"])

    def test_name_alone_is_lowest_tier(self):
        item = self.assess_with_model("Alex Jansen is a director.", {"person": {}, "claims": []})
        self.assertEqual((item["identity"], item["confidence_score"]), ("possible", 1))

    def test_name_and_city_without_strong_identifier_do_not_confirm(self):
        item = self.assess_with_model(
            "Alex Jansen lives in Utrecht and is under investigation.",
            {"person": {}, "claims": [
                {"summary": "An investigation was reported.", "exact_quote": "is under investigation", "type": "allegation"}
            ]},
        )
        self.assertEqual(item["identity"], "possible")
        self.assertEqual(item["claims"], [])
        self.assertEqual(item["confidence_score"], 2)

    def test_age_counts_as_strong_identifier(self):
        item = self.assess_with_model(
            "Alex Jansen (54) from Utrecht was fined by the regulator.",
            {"person": person(age=(54, "Alex Jansen (54)")), "publication_date": "2026-03-01",
             "claims": [{"summary": "A fine was reported.", "exact_quote": "was fined by the regulator", "type": "fine"}]},
            birth_year=1972,
        )
        self.assertEqual(item["identity"], "confirmed")
        self.assertEqual(item["identity_card"]["age"]["status"], "match")
        self.assertEqual(item["claims"][0]["type"], "fine")

    def test_age_mismatch_marks_a_different_person(self):
        item = self.assess_with_model(
            "Alex Jansen (31) from Utrecht was fined.",
            {"person": person(age=(31, "Alex Jansen (31)")), "publication_date": "2026-03-01", "claims": []},
            birth_year=1972,
        )
        self.assertEqual((item["identity"], item["confidence_score"]), ("unrelated", 0))

    def test_unverified_model_facts_are_ignored(self):
        item = self.assess_with_model(
            "Alex Jansen from Utrecht spoke at a meeting.",
            {"person": person(employer=("Example Studio", "works at Example Studio")), "claims": []},
            employer="Example Studio",
        )
        self.assertEqual(item["identity_card"]["employer"]["status"], "absent")
        self.assertEqual(item["identity"], "possible")

    def test_other_persons_city_is_not_an_identity_anchor(self):
        item = self.assess_with_model(
            "Alex Jansen directs Example Studio. De heer Jan Pouwels te Utrecht is also a director.",
            {"person": person(name_as_written=("Alex Jansen", "Alex Jansen"),
                               city=("Utrecht", "de heer Jan Pouwels te Utrecht"),
                               employer=("Example Studio", "Alex Jansen directs Example Studio")),
             "claims": []}, employer="Example Studio",
        )
        self.assertEqual(item["identity_card"]["city"]["status"], "absent")
        self.assertEqual(item["identity"], "possible")

    def test_only_exact_evidence_is_kept(self):
        item = self.assess_with_model(
            "A report says Alex Jansen of Example Studio in Utrecht is under investigation for fraud.",
            {"person": person(employer=("Example Studio", "Alex Jansen of Example Studio")), "claims": [
                {"summary": "The report says an investigation is ongoing.", "exact_quote": "under investigation for fraud", "type": "allegation"},
                {"summary": "Fraud", "exact_quote": "convicted of bribery", "type": "conviction"},
            ]}, employer="Example Studio",
        )
        self.assertEqual(item["identity"], "confirmed")
        self.assertEqual(item["confidence_score"], 3)
        self.assertEqual(len(item["claims"]), 1)
        report = assemble({"name": "Alex Jansen", "city": "Utrecht", "employer": "Example Studio",
                           "assessments": [item]})["report"]
        self.assertEqual(len(report["confirmed_findings"]), 1)
        self.assertEqual(report["review_status"], "awaiting_human_review")
        self.assertEqual(report["flags"][0]["code"], "reported_allegation")
        self.assertEqual(report["flags"][0]["group"], "act")
        self.assertEqual(report["risk_flags"], ["Adverse reporting linked"])

    def test_biographical_fact_is_not_an_adverse_claim(self):
        item = self.assess_with_model(
            "Alex Jansen of Example Studio in Utrecht died in 2025.",
            {"person": person(employer=("Example Studio", "Alex Jansen of Example Studio")),
             "claims": [{"summary": "Died in 2025", "exact_quote": "died in 2025", "type": "other"}]},
            employer="Example Studio",
        )
        self.assertEqual(item["identity"], "confirmed")
        self.assertEqual(item["claims"], [])

    def test_flags_distinguish_unresolved_identity_and_coverage(self):
        report = assemble({
            "name": "Alex Jansen", "city": "Utrecht",
            "assessments": [{"identity": "possible", "claims": [], "url": "https://example.com/a"}],
            "errors": ["Could not read a source"],
            "coverage": [{"key": "sanctions", "label": "EU and Dutch sanctions lists", "status": "failed", "detail": "Lists unavailable"}],
        })["report"]
        self.assertEqual([f["group"] for f in report["flags"]], ["review", "coverage", "coverage"])
        self.assertEqual(report["confirmed_findings"], [])
        self.assertTrue(any(c["status"] == "manual" for c in report["coverage"]))

    def test_sanction_hits_become_flags(self):
        hit = {"list": "EU sanctions list", "matched_name": "Alex Jansen", "url": "https://eur-lex.example",
               "reason": "Name matches.", "identity": "possible"}
        report = assemble({"name": "Alex Jansen", "city": "Utrecht", "sanction_hits": [hit]})["report"]
        self.assertEqual(report["flags"][0]["code"], "possible_sanction_match")
        confirmed = assemble({"name": "Alex Jansen", "city": "Utrecht",
                              "sanction_hits": [{**hit, "identity": "confirmed"}]})["report"]
        self.assertEqual(confirmed["flags"][0]["group"], "act")

    def test_private_urls_are_rejected(self):
        self.assertFalse(safe_public_url("http://127.0.0.1/private"))
        self.assertFalse(safe_public_url("http://192.168.1.1/private"))
        self.assertFalse(safe_public_url("file:///etc/passwd"))
        self.assertFalse(safe_public_url("https://example.com:bad/path"))

    def test_search_keeps_dutch_official_and_identity_results(self):
        def fake_post(url, headers, json, timeout):
            query = json["q"]
            group = ("official" if "site:" in query else "alias" if '"Lex J."' in query else "dutch" if "fraude" in query
                     else "english" if "fraud" in query else "identity")
            response = MagicMock()
            response.json.return_value = {"organic": [
                {"link": f"https://{group}.example/{i}", "title": group}
                for i in range(10)
            ]}
            return response

        with patch.dict("identity_workflow.os.environ", {"SERPER_API_KEY": "test-key"}), \
             patch("identity_workflow.requests.post", side_effect=fake_post), \
             patch("identity_workflow.safe_public_url", return_value=True):
            result = search({"name": "Alex Jansen", "city": "Utrecht", "aliases": ["lex"]})
        urls = [item["url"] for item in result["results"]]
        self.assertEqual(result["metrics"]["search_queries"], 6)
        self.assertEqual(len(urls), 24)
        self.assertEqual(len(result["search_trace"]), 6)
        for group in ("dutch", "official", "alias", "identity"):
            self.assertTrue(any(f"{group}.example" in url for url in urls), group)

    def test_follow_up_only_uses_source_grounded_leads(self):
        state = {"name": "Alex Jansen", "city": "Utrecht", "pages": [],
                 "assessments": [{"identity": "possible", "leads": [
                     {"kind": "company", "value": "Example Studio", "source_url": "https://example.com/a"}]}],
                 "metrics": {"search_queries": 5}}
        response = MagicMock()
        response.json.return_value = {"organic": []}
        with patch.dict("identity_workflow.os.environ", {"SERPER_API_KEY": "test-key"}), \
             patch("identity_workflow.requests.post", return_value=response):
            result = follow_leads(state)
        self.assertEqual(result["metrics"]["search_queries"], 6)
        self.assertIn('"Example Studio"', result["search_trace"][0]["query"])
        self.assertEqual(result["assessments"], state["assessments"])

    def test_fetch_uses_backup_candidates_when_initial_pages_are_unreadable(self):
        hits = [{"url": f"https://example.com/{i}", "title": str(i)} for i in range(16)]
        def text_for(url):
            return "Readable source " * 30 if int(url.rsplit("/", 1)[-1]) >= 8 else ""
        with patch("identity_workflow.fetch_page", side_effect=text_for):
            result = fetch({"results": hits})
        self.assertEqual(len(result["pages"]), 8)
        self.assertEqual(result["pages"][0]["url"], "https://example.com/8")

    def test_pdf_source_text_is_read(self):
        response = MagicMock(status_code=200, is_redirect=False,
                             headers={"content-type": "application/pdf"})
        response.iter_content.return_value = [b"%PDF sample"]
        reader = MagicMock()
        reader.pages = [MagicMock()]
        reader.pages[0].extract_text.return_value = "Albert Jansen is director of Example BV."
        with patch("identity_workflow.safe_public_url", return_value=True), \
             patch("identity_workflow.requests.get", return_value=response), \
             patch("identity_workflow.PdfReader", return_value=reader):
            self.assertIn("director of Example BV", fetch_page("https://example.com/report/pdf"))

    def test_graph_runs_branches_and_survives_failures(self):
        with patch("identity_workflow.search", return_value={"results": [], "coverage": []}), \
             patch("identity_workflow.sanctions.load_lists", side_effect=OSError("offline")):
            report = build_graph().invoke({
                "name": "Alex Jansen", "city": "Utrecht", "employer": "", "birth_year": None,
                "profession": "unknown", "context": "", "errors": [], "coverage": [], "metrics": {},
            })["report"]
        statuses = {c["key"]: c["status"] for c in report["coverage"]}
        self.assertEqual(statuses["sanctions"], "failed")
        self.assertEqual(statuses["big"], "not_applicable")
        self.assertIn("source_failed", [f["code"] for f in report["flags"]])

    def test_pdf_is_generated_for_review_draft(self):
        data = generate_evidence_pdf({"subject": {"name": "Alex Jansen", "city": "Utrecht"}, "sources": [],
                                      "flags": [{"label": "Identity needs review", "group": "review", "reason": "1 source"}]})
        self.assertTrue(data.startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()
