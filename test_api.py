import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from api import app


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health(self):
        self.assertEqual(self.client.get("/health").json(), {"status": "ok"})

    def test_research_returns_workflow_result(self):
        expected = {"subject": {"name": "Alex Jansen", "city": "Utrecht"}, "sources": []}
        with patch("api.run_identity_research", return_value=expected) as workflow:
            response = self.client.post("/research", json={"name": "Alex Jansen", "city": "Utrecht"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)
        self.assertEqual(response.headers["cache-control"], "no-store")
        workflow.assert_called_once_with("Alex Jansen", "Utrecht", "", "")

    def test_research_rejects_missing_identity_clues(self):
        response = self.client.post("/research", json={"name": "Alex Jansen", "city": ""})
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
