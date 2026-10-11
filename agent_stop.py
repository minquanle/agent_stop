import argparse
import json
from dataclasses import asdict
from time import monotonic
from contracts import Budget, Task
from gemini_planner import GeminiPlanner
from stop_core import run_agent


def execute(task, budget=None, tools=None, repeat_tool=False):
    planner = GeminiPlanner(repeat_tool=repeat_tool)
    started = monotonic()
    planner.deadline = started + (budget or Budget()).max_seconds
    try:
        result = run_agent(planner, task, budget=budget, tools=tools)
        return {"model": planner.model, "result": asdict(result),
                "api_calls": [c for c in planner.calls if c["request_sent"]],
                "planner_events": planner.calls,
                "elapsed_seconds": round(monotonic() - started, 3)}
    finally:
        planner.close()


def main():
    parser = argparse.ArgumentParser(description="Gemini 2.5 Flash stop controller")
    parser.add_argument("--quantity", type=int)
    parser.add_argument("--unit-price", type=int)
    parser.add_argument("--needs-approval", action="store_true")
    parser.add_argument("--approved", action="store_true")
    parser.add_argument("--max-steps", type=int, default=4)
    parser.add_argument("--max-tool-calls", type=int, default=3)
    parser.add_argument("--max-seconds", type=float, default=90)
    parser.add_argument("--max-retries", type=int, default=1)
    parser.add_argument("--max-same-call", type=int, default=2)
    args = parser.parse_args()
    try:
        budget = Budget(args.max_steps, args.max_tool_calls, args.max_seconds,
                        args.max_retries, args.max_same_call)
        task = Task(args.quantity, args.unit_price, args.needs_approval, args.approved)
        report = execute(task, budget)
    except Exception as exc:
        print(json.dumps({"startup_error": type(exc).__name__,
                          "next_action": "Check .env, dependencies and CLI values."}))
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["result"]["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
