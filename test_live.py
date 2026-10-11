import unittest
import json
from pathlib import Path
from live_demo import scenario, summary


class LiveTests(unittest.TestCase):
    reports = []
    quota_exhausted = False

    @classmethod
    def tearDownClass(cls):
        root = Path(__file__).parent
        (root / "live_results.json").write_text(
            json.dumps(cls.reports, ensure_ascii=False, indent=2), encoding="utf-8")
        (root / "live_output.txt").write_text(
            "\n".join(summary(r) for r in cls.reports) + "\n", encoding="utf-8")

    def check_case(self, case, status, reason, api_minimum):
        if self.quota_exhausted and case not in "CJ":
            self.skipTest("Gemini quota exhausted; restore quota before rerunning.")
        report = scenario(case)
        self.reports.append(report)
        if any(c.get("http_status") == 429 for c in report["api_calls"]):
            type(self).quota_exhausted = True
        r = report["result"]
        self.assertEqual((r["status"], r["reason"]), (status, reason))
        self.assertGreaterEqual(len(report["api_calls"]), api_minimum)
        self.assertEqual(len(report["api_calls"]), r["steps"])
        for call in report["api_calls"]:
            self.assertTrue(call["ok"], call.get("error_type"))
            self.assertTrue(call.get("response_id"))
            self.assertEqual(call["model_version"], "gemini-2.5-flash")
        self.assertEqual(sum(e["event"] == "stopped" for e in r["trace"]), 1)
        if status == "completed":
            self.assertEqual(r["output"], {"total": 100000, "currency": "VND"})
            self.assertTrue(r["partial_results"])
        else:
            self.assertIsNone(r["output"])
        return report

    def test_A_completed(self):
        self.check_case("A", "completed", "criteria_met", 2)

    def test_B_wrong_evidence(self):
        self.check_case("B", "failed", "validation_failed", 2)

    def test_C_missing_input(self):
        report = self.check_case("C", "blocked", "missing_input", 0)
        self.assertEqual(report["api_calls"], [])

    def test_D_retry_exhausted(self):
        self.check_case("D", "failed", "retry_exhausted", 1)

    def test_E_step_limit(self):
        self.check_case("E", "budget_exhausted", "step_limit", 1)

    def test_F_tool_limit(self):
        self.check_case("F", "budget_exhausted", "tool_limit", 1)

    def test_G_real_deadline(self):
        report = self.check_case("G", "budget_exhausted", "time_limit", 1)
        self.assertGreaterEqual(report["elapsed_seconds"], 25)

    def test_H_repeated_proposals(self):
        self.check_case("H", "failed", "no_progress", 3)

    def test_I_retry_recovery(self):
        report = self.check_case("I", "completed", "criteria_met", 2)
        self.assertEqual(report["result"]["tool_calls"], 2)

    def test_J_approval_required(self):
        report = self.check_case("J", "blocked", "approval_required", 0)
        self.assertEqual(report["api_calls"], [])


if __name__ == "__main__":
    unittest.main()
