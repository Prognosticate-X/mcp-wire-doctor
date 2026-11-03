import os
import unittest
from mcp_wire_doctor.cli import run_full_audit
from mcp_wire_doctor.audits.base import AuditStatus


class TestAudits(unittest.TestCase):
    def setUp(self):
        self.examples_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "examples"))
        self.perfect_server = f"python3 {os.path.join(self.examples_dir, 'mock_perfect_server.py')}"
        self.faulty_server = f"python3 {os.path.join(self.examples_dir, 'mock_faulty_server.py')}"

    def test_perfect_server_passes_all(self):
        suite = run_full_audit(self.perfect_server)
        self.assertEqual(suite.fail_count, 0)
        self.assertEqual(suite.score, 100)

    def test_faulty_server_catches_all_bugs(self):
        suite = run_full_audit(self.faulty_server)
        # Should catch:
        # 1. Stdout pollution (SEC-STREAM-001)
        # 2. Zod validation failure (CLAUDE-ZOD-001)
        # 3. Dynamic timestamp destroying prompt cache (CACHE-DET-001)
        # 4. Token in global cache scope (SEC-CACHE-002)
        failed_rule_ids = {r.rule_id for r in suite.results if r.status == AuditStatus.FAIL}
        self.assertIn("SEC-STREAM-001", failed_rule_ids)
        self.assertIn("CLAUDE-ZOD-001", failed_rule_ids)
        self.assertIn("CACHE-DET-001", failed_rule_ids)
        self.assertIn("SEC-CACHE-002", failed_rule_ids)
        self.assertLess(suite.score, 60)


if __name__ == "__main__":
    unittest.main()
