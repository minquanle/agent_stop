import json
from collections import Counter
from copy import deepcopy
from time import monotonic
from contracts import Budget, Decision, RunResult, Status, validate_final
from tools import TOOL_MAP


def run_agent(planner, task, budget=None, tools=None, clock=monotonic):
    budget = Budget() if budget is None else budget
    tools = TOOL_MAP if tools is None else tools
    trace, history, evidence = [], [], []
    counts = Counter()
    steps, tool_calls = 0, 0
    started = clock()

    def expired():
        return clock() - started >= budget.max_seconds

    def finish(status, reason, next_action, output=None):
        trace.append({"event": "stopped", "status": status.value,
                      "reason": reason, "step": steps})
        return RunResult(status, reason, steps, tool_calls, output,
                         evidence.copy(), trace.copy(), next_action)

    def exhausted(reason):
        return finish(Status.BUDGET_EXHAUSTED, reason,
                      "Review partial results and grant a new budget if needed.")

    if task.quantity is None or task.unit_price is None:
        return finish(Status.BLOCKED, "missing_input",
                      "Provide quantity and unit_price, then start a new run.")
    if (type(task.quantity) is not int or type(task.unit_price) is not int
            or not 0 <= task.quantity <= 1_000_000
            or not 0 <= task.unit_price <= 1_000_000_000
            or type(task.needs_approval) is not bool
            or type(task.approved) is not bool):
        return finish(Status.FAILED, "invalid_input", "Correct the task input.")
    if task.needs_approval and not task.approved:
        return finish(Status.BLOCKED, "approval_required",
                      "Request approval through the trusted application UI.")

    while True:
        if expired():
            return exhausted("time_limit")
        if steps >= budget.max_steps:
            return exhausted("step_limit")
        steps += 1
        trace.append({"event": "model_attempt", "step": steps})
        try:
            decision = planner(task, deepcopy(history))
        except Exception as exc:
            trace.append({"event": "model_error", "step": steps,
                          "error_type": type(exc).__name__})
            if expired():
                return exhausted("time_limit")
            return finish(Status.FAILED, "model_error", "Check the model adapter.")
        if expired():
            return exhausted("time_limit")
        if not isinstance(decision, Decision):
            return finish(Status.FAILED, "protocol_error", "Fix the decision schema.")
        if decision.kind == "final":
            valid = validate_final(task, decision.candidate, evidence)
            if expired():
                return exhausted("time_limit")
            if valid:
                return finish(Status.COMPLETED, "criteria_met",
                              "Use the verified output.", decision.candidate.copy())
            return finish(Status.FAILED, "validation_failed",
                          "Inspect the candidate and its tool evidence.")
        if (decision.kind != "tool" or type(decision.tool) is not str
                or decision.tool not in tools or type(decision.args) is not dict):
            return finish(Status.FAILED, "protocol_error", "Fix the tool proposal.")
        try:
            key = json.dumps([decision.tool, decision.args],
                             sort_keys=True, allow_nan=False)
        except (TypeError, ValueError):
            return finish(Status.FAILED, "protocol_error", "Use finite JSON arguments.")
        if counts[key] >= budget.max_same_call:
            return finish(Status.FAILED, "no_progress",
                          "Review the repeated request before running again.")
        counts[key] += 1

        # A retry belongs to this decision; it does not call the planner again.
        retries = 0
        while True:
            if expired():
                return exhausted("time_limit")
            if tool_calls >= budget.max_tool_calls:
                return exhausted("tool_limit")
            tool_calls += 1
            trace.append({"event": "tool_attempt", "step": steps,
                          "name": decision.tool, "attempt": retries + 1})
            data, error = None, None
            try:
                data = tools[decision.tool](**decision.args)
            except Exception as exc:
                error = exc
                trace.append({"event": "tool_error", "step": steps,
                              "error_type": type(exc).__name__})
            if expired():
                return exhausted("time_limit")
            if error is not None:
                if not isinstance(error, (TimeoutError, ConnectionError)):
                    return finish(Status.FAILED, "tool_error", "Fix the tool or arguments.")
                if retries >= budget.max_retries:
                    return finish(Status.FAILED, "retry_exhausted", "Check the dependency.")
                retries += 1
                trace.append({"event": "retry", "step": steps, "retry": retries})
                continue
            if (type(data) is not dict or set(data) != {"total", "currency"}
                    or type(data["total"]) is not int or data["currency"] != "VND"):
                return finish(Status.FAILED, "tool_protocol", "Fix the tool output schema.")
            record = {"tool": decision.tool, "args": decision.args.copy(),
                      "data": data.copy()}
            evidence.append(record)
            history.extend([decision, record])
            trace.append({"event": "tool_success", "step": steps,
                          "name": decision.tool})
            break
