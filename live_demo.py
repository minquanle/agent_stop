import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from time import sleep
from agent_stop import execute
from contracts import Budget, Task
from tools import calculate_total


class DiagnosticTotal:
    """Controlled tool faults; Gemini responses and elapsed time are real."""
    def __init__(self, failures=0, wrong_total=False, delay=0):
        self.failures, self.wrong_total, self.delay = failures, wrong_total, delay
        self.calls = 0

    def __call__(self, **args):
        self.calls += 1
        if self.calls <= self.failures:
            raise ConnectionError("diagnostic_tool_unavailable")
        if self.delay:
            sleep(self.delay)
        data = calculate_total(**args)
        if self.wrong_total:
            data["total"] += 1
        return data


def scenario(name):
    task, budget = Task(4, 25000), Budget()
    tools, repeat = None, False
    if name == "B":
        tools = {"calculate_total": DiagnosticTotal(wrong_total=True)}
    elif name == "C":
        task = Task(None, 25000)
    elif name == "D":
        tools = {"calculate_total": DiagnosticTotal(failures=10)}
    elif name == "E":
        budget = Budget(max_steps=1)
    elif name == "F":
        budget = Budget(max_tool_calls=1)
        tools = {"calculate_total": DiagnosticTotal(failures=1)}
    elif name == "G":
        budget = Budget(max_seconds=25)
        tools = {"calculate_total": DiagnosticTotal(delay=26)}
    elif name == "H":
        repeat = True
    elif name == "I":
        tools = {"calculate_total": DiagnosticTotal(failures=1)}
    elif name == "J":
        task = Task(4, 25000, needs_approval=True)
    elif name != "A":
        raise ValueError("unknown_case")
    report = execute(task, budget, tools, repeat_tool=repeat)
    report["case"] = name
    report["utc"] = datetime.now(timezone.utc).isoformat()
    report["diagnostic_tool"] = name in "BDFGI"
    return report


def summary(report):
    r = report["result"]
    status = r["status"].value if hasattr(r["status"], "value") else r["status"]
    return (f"{report['case']}: status={status}; reason={r['reason']}\n"
            f"  steps={r['steps']}; tool_calls={r['tool_calls']}; api_calls={len(report['api_calls'])}\n"
            f"  output={r['output']}; partial_results={len(r['partial_results'])}")


def main():
    parser = argparse.ArgumentParser(description="Live Gemini integration scenarios")
    parser.add_argument("--case", choices=list("ABCDEFGHIJ"))
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--save", type=Path)
    args = parser.parse_args()
    reports = []
    for name in ([args.case] if args.case else list("ABCDEFGHIJ")):
        try:
            report = scenario(name)
        except Exception as exc:
            report = {"case": name, "startup_error": type(exc).__name__}
        reports.append(report)
        print(json.dumps(report, ensure_ascii=False) if args.json
              or "startup_error" in report else summary(report), flush=True)
        if "startup_error" in report or any(c.get("http_status") == 429
                                          for c in report.get("api_calls", [])):
            break
    if args.save:
        args.save.parent.mkdir(parents=True, exist_ok=True)
        args.save.write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if all("result" in r and all(c["ok"] for c in r["api_calls"])
                    for r in reports) else 1


if __name__ == "__main__":
    raise SystemExit(main())
