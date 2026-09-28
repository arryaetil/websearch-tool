import unittest
import os
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch

from fastapi.testclient import TestClient

from api import app
from run_store import RETENTION_SECONDS, get_run, list_runs, save_run


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health(self):
        self.assertEqual(self.client.get("/health").json(), {"status": "ok"})

    def test_research_returns_workflow_result(self):
        expected = {"subject": {"name": "Alex Jansen", "city": "Utrecht"}, "sources": []}
        Path("data").mkdir(exist_ok=True)
        database = Path("data") / f"test-{uuid4()}.sqlite3"
        with patch.dict(os.environ, {"KYCX_RUN_DB": str(database)}), patch("api.run_identity_research", return_value=expected) as workflow:
            response = self.client.post("/research", json={"name": "Alex Jansen", "city": "Utrecht"})
            run_id = response.json()["saved_run"]["id"]
            self.assertEqual(self.client.get("/runs").json()["runs"][0]["id"], run_id)
            self.assertEqual(self.client.get(f"/runs/{run_id}").json(), expected)
            self.assertEqual(self.client.delete(f"/runs/{run_id}").status_code, 200)
            self.assertEqual(self.client.get(f"/runs/{run_id}").status_code, 404)
        database.unlink(missing_ok=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["subject"], expected["subject"])
        self.assertEqual(response.headers["cache-control"], "no-store")
        workflow.assert_called_once_with("Alex Jansen", "Utrecht", "", "", birth_year=None, profession="unknown", aliases="")

    def test_research_rejects_implausible_birth_year(self):
        response = self.client.post("/research", json={"name": "Alex Jansen", "city": "Utrecht", "birth_year": 1800})
        self.assertEqual(response.status_code, 422)

    def test_research_rejects_missing_identity_clues(self):
        response = self.client.post("/research", json={"name": "Alex Jansen", "city": ""})
        self.assertEqual(response.status_code, 422)

    def test_saved_run_expires_after_seven_days(self):
        Path("data").mkdir(exist_ok=True)
        database = Path("data") / f"test-{uuid4()}.sqlite3"
        with patch.dict(os.environ, {"KYCX_RUN_DB": str(database)}), patch("run_store.time.time", return_value=1000):
            run_id = save_run({"subject": {"name": "Example Person", "city": "Utrecht"}})["id"]
        with patch.dict(os.environ, {"KYCX_RUN_DB": str(database)}), patch("run_store.time.time", return_value=1000 + RETENTION_SECONDS):
            self.assertIsNone(get_run(run_id))
            self.assertEqual(list_runs(), [])
        database.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
