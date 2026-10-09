import unittest
from contracts import Budget, Decision, Status, Task
from offline_demo import FakeClock, FlakyTotal, ScriptedPlanner, final, scenario, total_call
from stop_core import run_agent


class StopTests(unittest.TestCase):
    def run_script(self, decisions, **kwargs):
        planner = ScriptedPlanner(decisions)
        result = run_agent(planner, Task(4, 25000), **kwargs)
        self.assertEqual(result.trace[-1]["event"], "stopped")
        self.assertEqual(sum(e["event"] == "stopped" for e in result.trace), 1)
        return result, planner

    def test_all_scenarios(self):
        expected = {
            "A": (Status.COMPLETED, "criteria_met", 2, 1, 1),
            "B": (Status.FAILED, "validation_failed", 2, 1, 1),
            "C": (Status.BLOCKED, "missing_input", 0, 0, 0),
            "D": (Status.FAILED, "retry_exhausted", 1, 2, 0),
            "E": (Status.BUDGET_EXHAUSTED, "step_limit", 1, 1, 1),
            "F": (Status.BUDGET_EXHAUSTED, "tool_limit", 1, 1, 0),
            "G": (Status.BUDGET_EXHAUSTED, "time_limit", 1, 1, 0),
            "H": (Status.FAILED, "no_progress", 3, 2, 2),
            "I": (Status.COMPLETED, "criteria_met", 2, 2, 1),
            "J": (Status.BLOCKED, "approval_required", 0, 0, 0),
        }
        for name, values in expected.items():
            with self.subTest(case=name):
                result = scenario(name)
                self.assertEqual((result.status, result.reason, result.steps,
                                  result.tool_calls, len(result.partial_results)), values)

    def test_final_without_evidence_is_not_completion(self):
        result, _ = self.run_script([final()])
        self.assertEqual(result.reason, "validation_failed")
        self.assertIsNone(result.output)

    def test_correct_final_at_last_step_is_accepted(self):
        result, planner = self.run_script([total_call(), final()], budget=Budget(max_steps=2))
        self.assertEqual(result.status, Status.COMPLETED)
        self.assertEqual(planner.calls, 2)

    def test_no_extra_summary_after_step_limit(self):
        result, planner = self.run_script([total_call(), final()], budget=Budget(max_steps=1))
        self.assertEqual(result.reason, "step_limit")
        self.assertEqual(planner.calls, 1)

    def test_final_can_follow_last_tool_attempt(self):
        result, _ = self.run_script([total_call(), final()], budget=Budget(max_tool_calls=1))
        self.assertEqual(result.status, Status.COMPLETED)

    def test_retry_is_counted_as_tool_attempt_not_model_step(self):
        result, planner = self.run_script([total_call(), final()],
                                         tools={"calculate_total": FlakyTotal(1)})
        self.assertEqual((result.steps, result.tool_calls, planner.calls), (2, 2, 2))

    def test_zero_retries_stops_on_first_transient_error(self):
        result, _ = self.run_script([total_call()], budget=Budget(max_retries=0),
                                    tools={"calculate_total": FlakyTotal(1)})
        self.assertEqual((result.reason, result.tool_calls), ("retry_exhausted", 1))

    def test_permanent_tool_error_is_not_retried(self):
        invalid = Decision("tool", "calculate_total", {"quantity": 4, "unit_price": -1})
        result, _ = self.run_script([invalid])
        self.assertEqual((result.reason, result.tool_calls), ("tool_error", 1))

    def test_unknown_tool_never_executes(self):
        result, _ = self.run_script([Decision("tool", "delete_files")])
        self.assertEqual((result.reason, result.tool_calls), ("protocol_error", 0))

    def test_non_decision_model_output_fails(self):
        result, _ = self.run_script([{"kind": "final"}])
        self.assertEqual(result.reason, "protocol_error")

    def test_model_error_counts_attempt_and_redacts_message(self):
        result, _ = self.run_script([RuntimeError("secret-test-token")])
        self.assertEqual((result.reason, result.steps), ("model_error", 1))
        self.assertNotIn("secret-test-token", repr(result.trace))

    def test_missing_input_never_calls_model(self):
        planner = ScriptedPlanner([final()])
        result = run_agent(planner, Task(None, 25000))
        self.assertEqual((result.status, planner.calls), (Status.BLOCKED, 0))

    def test_approval_gate_never_calls_model(self):
        planner = ScriptedPlanner([final()])
        result = run_agent(planner, Task(4, 25000, True, False))
        self.assertEqual((result.reason, planner.calls), ("approval_required", 0))

    def test_trusted_approval_allows_new_run(self):
        planner = ScriptedPlanner([total_call(), final()])
        result = run_agent(planner, Task(4, 25000, True, True))
        self.assertEqual(result.status, Status.COMPLETED)

    def test_non_boolean_approved_is_rejected_before_planner(self):
        for value in ("false", "true", "", 0, 1, None, [], {}):
            with self.subTest(approved=value):
                planner = ScriptedPlanner([total_call(), final()])
                result = run_agent(planner, Task(4, 25000, True, value))
                self.assertEqual((result.status, result.reason),
                                 (Status.FAILED, "invalid_input"))
                self.assertEqual((planner.calls, result.steps, result.tool_calls), (0, 0, 0))

    def test_non_boolean_needs_approval_is_rejected_before_planner(self):
        for value in ("false", "true", "", 0, 1, None, [], {}):
            with self.subTest(needs_approval=value):
                planner = ScriptedPlanner([total_call(), final()])
                result = run_agent(planner, Task(4, 25000, value, False))
                self.assertEqual((result.status, result.reason),
                                 (Status.FAILED, "invalid_input"))
                self.assertEqual((planner.calls, result.steps, result.tool_calls), (0, 0, 0))

    def test_rewriting_history_cannot_forge_tool_evidence(self):
        def rewriting_planner(task, history):
            if not history:
                return total_call(2, 25000)
            history[1]["args"]["quantity"] = 4
            history[1]["data"]["total"] = 100000
            return final()

        result = run_agent(rewriting_planner, Task(4, 25000))
        self.assertEqual((result.status, result.reason),
                         (Status.FAILED, "validation_failed"))
        self.assertEqual(result.partial_results[0]["args"]["quantity"], 2)
        self.assertEqual(result.partial_results[0]["data"]["total"], 50000)
        self.assertIsNone(result.output)

    def test_mutating_retained_history_cannot_change_run_result(self):
        result, planner = self.run_script([total_call(), final()])
        planner.histories[1][1]["args"]["quantity"] = 99
        planner.histories[1][1]["data"]["total"] = 1
        self.assertEqual(result.partial_results[0]["args"]["quantity"], 4)
        self.assertEqual(result.partial_results[0]["data"]["total"], 100000)
        self.assertEqual(result.output["total"], 100000)

    def test_boolean_task_quantity_is_invalid(self):
        result = run_agent(ScriptedPlanner([]), Task(True, 25000))
        self.assertEqual(result.reason, "invalid_input")

    def test_zero_total_is_valid(self):
        result = run_agent(ScriptedPlanner([total_call(0), final(0)]), Task(0, 25000))
        self.assertEqual(result.status, Status.COMPLETED)

    def test_wrong_tool_arguments_cannot_validate_task(self):
        result, _ = self.run_script([total_call(2, 50000), final()])
        self.assertEqual(result.reason, "validation_failed")

    def test_wrong_currency_cannot_validate(self):
        result, _ = self.run_script([total_call(), Decision("final", candidate={"total": 100000, "currency": "USD"})])
        self.assertEqual(result.reason, "validation_failed")

    def test_boolean_final_total_is_invalid(self):
        result, _ = self.run_script([total_call(), Decision("final", candidate={"total": True, "currency": "VND"})])
        self.assertEqual(result.reason, "validation_failed")

    def test_malformed_final_is_invalid(self):
        for candidate in (None, [], {}, {"total": 100000}, {"total": 100000, "currency": "VND", "extra": 1}):
            with self.subTest(candidate=candidate):
                result, _ = self.run_script([Decision("final", candidate=candidate)])
                self.assertEqual(result.reason, "validation_failed")

    def test_non_finite_arguments_never_call_tool(self):
        result, _ = self.run_script([Decision("tool", "calculate_total", {"quantity": float("nan")})])
        self.assertEqual((result.reason, result.tool_calls), ("protocol_error", 0))

    def test_non_json_arguments_never_call_tool(self):
        result, _ = self.run_script([Decision("tool", "calculate_total", {"quantity": object()})])
        self.assertEqual((result.reason, result.tool_calls), ("protocol_error", 0))

    def test_deadline_after_model_stops_before_tool(self):
        clock = FakeClock()

        def slow_planner(task, history):
            clock.now += 10.0
            return total_call()

        result = run_agent(slow_planner, Task(4, 25000), clock=clock)
        self.assertEqual((result.reason, result.steps, result.tool_calls), ("time_limit", 1, 0))

    def test_deadline_takes_priority_over_late_model_error(self):
        clock = FakeClock()

        def late_error(task, history):
            clock.now += 11.0
            raise ConnectionError("late")

        result = run_agent(late_error, Task(4, 25000), clock=clock)
        self.assertEqual(result.reason, "time_limit")

    def test_deadline_takes_priority_over_late_final(self):
        clock = FakeClock()
        calls = 0

        def planner(task, history):
            nonlocal calls
            calls += 1
            if calls == 1:
                return total_call()
            clock.now += 10.0
            return final()

        result = run_agent(planner, Task(4, 25000), clock=clock)
        self.assertEqual((result.reason, len(result.partial_results)), ("time_limit", 1))
        self.assertIsNone(result.output)

    def test_tool_output_schema_is_checked(self):
        result, _ = self.run_script([total_call()], tools={"calculate_total": lambda **kw: "100000"})
        self.assertEqual(result.reason, "tool_protocol")

    def test_reordered_argument_keys_share_repeat_key(self):
        reordered = Decision("tool", "calculate_total", {"unit_price": 25000, "quantity": 4})
        result, _ = self.run_script([total_call(), reordered, total_call()])
        self.assertEqual((result.reason, result.tool_calls), ("no_progress", 2))

    def test_retry_does_not_spend_repeat_proposal_allowance(self):
        result, _ = self.run_script([total_call(), final()], budget=Budget(max_same_call=1),
                                    tools={"calculate_total": FlakyTotal(1)})
        self.assertEqual(result.status, Status.COMPLETED)

    def test_history_contains_successful_tool_evidence(self):
        result, planner = self.run_script([total_call(), final()])
        self.assertEqual(planner.histories[1][1]["data"], result.output)

    def test_counters_are_new_for_each_run(self):
        for _ in range(2):
            result, _ = self.run_script([total_call(), final()])
            self.assertEqual((result.steps, result.tool_calls), (2, 1))

    def test_invalid_budget_is_rejected_before_run(self):
        for kwargs in ({"max_steps": 0}, {"max_tool_calls": True},
                       {"max_retries": -1}, {"max_seconds": float("inf")},
                       {"max_seconds": float("nan")}, {"max_seconds": False}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                Budget(**kwargs)


if __name__ == "__main__":
    unittest.main()
