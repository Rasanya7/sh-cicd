import unittest
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import app


class TestFlaskRoutes(unittest.TestCase):

    def setUp(self):
        self.client = app.test_client()

    def test_pages_render(self):
        routes = [
            "/",
            "/dashboard",
            "/failures",
            "/agents",
            "/analytics",
            "/pullrequests",
            "/settings"
        ]
        for r in routes:
            with self.subTest(route=r):
                response = self.client.get(r)
                self.assertEqual(response.status_code, 200, f"Route {r} failed with {response.status_code}")

    def test_api_endpoints(self):
        # 1. API Failures
        res = self.client.get("/api/failures")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertIn("failures", data)

        # 2. API Agents
        res = self.client.get("/api/agents")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertIn("agents", data)
        self.assertEqual(len(data["agents"]), 4)

        # 3. API Analytics
        res = self.client.get("/api/analytics")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertIn("total_failures", data)

        # 4. API PRs
        res = self.client.get("/api/pullrequests")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertIn("pull_requests", data)

    def test_simulate_failure_api(self):
        payload = {
            "workflow_name": "Test CI Suite",
            "error_type": "SyntaxError",
            "raw_logs": "File \"calculator.py\", line 4\n    def add(a, b)\n                 ^\nSyntaxError: expected ':'"
        }
        res = self.client.post("/api/simulate-failure", json=payload)
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("verdict"), "APPROVED")


if __name__ == "__main__":
    unittest.main()
