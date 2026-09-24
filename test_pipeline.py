import unittest
import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from database.database import init_db, get_db_connection
from database.models import get_stats, get_agents, get_failures, get_pull_requests
from services.orchestrator import MultiAgentOrchestrator
from services.test_service import TestService
from services.ai_service import AIService


class TestSHCICDPipeline(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db()

    def test_database_initialization(self):
        """Verify DB initializes with 4 agents and default stats."""
        agents = get_agents()
        agent_names = [a["agent_name"] for a in agents]
        self.assertIn("Dispatcher", agent_names)
        self.assertIn("Context Gatherer", agent_names)
        self.assertIn("Engineer", agent_names)
        self.assertIn("Reviewer", agent_names)

        stats = get_stats()
        self.assertGreaterEqual(stats["total_failures"], 1)
        self.assertGreaterEqual(stats["total_prs"], 1)

    def test_test_service_syntax(self):
        """Verify syntax validation identifies valid and invalid Python."""
        ts = TestService()
        valid_res = ts.validate_syntax("def add(a, b):\n    return a + b\n")
        self.assertTrue(valid_res["valid"])

        invalid_res = ts.validate_syntax("def add(a, b)\n    return a + b\n")
        self.assertFalse(invalid_res["valid"])

    def test_multi_agent_healing_syntax_error(self):
        """Simulate a SyntaxError failure and verify all 4 agents heal and approve it."""
        orchestrator = MultiAgentOrchestrator()
        failure_data = {
            "repo_name": "demo-user/sh-cicd-demo",
            "workflow_name": "Python CI Suite",
            "run_id": "test-run-101",
            "error_type": "SyntaxError",
            "error_message": "SyntaxError: expected ':' (calculator.py, line 4)",
            "raw_logs": """Run python -m py_compile demo_repo/calculator.py
  File "demo_repo/calculator.py", line 4
    def add(a, b)
                 ^
SyntaxError: expected ':'
Error: Process completed with exit code 1."""
        }

        result = orchestrator.run_healing_pipeline(failure_data=failure_data)
        self.assertTrue(result["success"])
        self.assertEqual(result["verdict"], "APPROVED")
        self.assertGreaterEqual(result["confidence"], 80.0)
        self.assertIsNotNone(result["pull_request"])
        self.assertIn("pr_number", result["pull_request"])
        self.assertEqual(len(result["steps"]), 4)


if __name__ == "__main__":
    unittest.main()
