import json
import unittest
from unittest.mock import MagicMock, patch

from identity_workflow import assess, assemble, safe_public_url, search
from evidence_pdf import generate_evidence_pdf


class IdentityWorkflowTests(unittest.TestCase):
    def page(self, content):
        return {
            "url": "https://example.com/story", "title": "Story", "content": content,
            "retrieved_at": "2026-01-01T00:00:00Z", "sha256": "abc",
        }

    def assess_with_model(self, content, model_result):
        client = MagicMock()
        client.responses.create.return_value.output_text = json.dumps(model_result)
        client.responses.create.return_value.usage = None
        with patch.dict("identity_workflow.os.environ", {"OPENAI_API_KEY": "test-key"}), patch("identity_workflow.OpenAI", return_value=client):
            return assess({
                "name": "Alex Jansen", "city": "Utrecht", "employer": "",
                "pages": [self.page(content)],
            })["assessments"][0]

    def test_initials_do_not_confirm(self):
        item = self.assess_with_model(
            "A. Jansen lives in Utrecht.",
            {"identity": "confirmed", "reason": "same city", "claims": [
                {"summary": "Lives in Utrecht", "exact_quote": "A. Jansen lives in Utrecht."}
            ]},
        )
        self.assertEqual(item["identity"], "possible")
        self.assertEqual(item["claims"], [])

    def test_name_alone_does_not_confirm(self):
        item = self.assess_with_model(
            "Alex Jansen is a director in Rotterdam.",
            {"identity": "confirmed", "reason": "name", "claims": []},
        )
        self.assertEqual(item["identity"], "possible")

    def test_only_exact_evidence_is_kept(self):
        item = self.assess_with_model(
            "A report says Alex Jansen of Utrecht is under investigation for fraud.",
            {"identity": "confirmed", "reason": "name and city", "claims": [
                {"summary": "The report says an investigation is ongoing.", "exact_quote": "under investigation for fraud"},
                {"summary": "Fraud", "exact_quote": "convicted of bribery"},
            ]},
        )
        self.assertEqual(item["identity"], "confirmed")
        self.assertEqual(len(item["claims"]), 1)
        report = assemble({"name": "Alex Jansen", "city": "Utrecht", "assessments": [item]})["report"]
        self.assertEqual(len(report["confirmed_findings"]), 1)
        self.assertEqual(report["review_status"], "awaiting_human_review")

    def test_private_urls_are_rejected(self):
        self.assertFalse(safe_public_url("http://127.0.0.1/private"))
        self.assertFalse(safe_public_url("http://192.168.1.1/private"))
        self.assertFalse(safe_public_url("file:///etc/passwd"))
        self.assertFalse(safe_public_url("https://example.com:bad/path"))

    def test_search_keeps_dutch_and_identity_results(self):
        def fake_post(url, headers, json, timeout):
            query = json["q"]
            group = "dutch" if "fraude" in query else "english" if "fraud" in query else "identity"
            response = MagicMock()
            response.json.return_value = {"organic": [
                {"link": f"https://{group}.example/{i}", "title": group}
                for i in range(10)
            ]}
            return response

        with patch.dict("identity_workflow.os.environ", {"SERPER_API_KEY": "test-key"}), \
             patch("identity_workflow.requests.post", side_effect=fake_post), \
             patch("identity_workflow.safe_public_url", return_value=True):
            result = search({"name": "Alex Jansen", "city": "Utrecht"})
        urls = [item["url"] for item in result["results"]]
        self.assertEqual(result["metrics"]["search_queries"], 3)
        self.assertEqual(len(urls), 8)
        self.assertTrue(any("dutch.example" in url for url in urls))
        self.assertTrue(any("identity.example" in url for url in urls))

    def test_pdf_is_generated_for_review_draft(self):
        data = generate_evidence_pdf({"subject": {"name": "Alex Jansen", "city": "Utrecht"}, "sources": []})
        self.assertTrue(data.startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()
