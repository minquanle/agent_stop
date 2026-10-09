import argparse
from dataclasses import asdict
import json
from contracts import Budget, Decision, Task
from stop_core import run_agent
from tools import calculate_total


class ScriptedPlanner:
    def __init__(self, decisions):
        self.decisions = iter(decisions)
        self.calls = 0
        self.histories = []

    def __call__(self, task, history):
        self.calls += 1
        self.histories.append(history)
        decision = next(self.decisions)
        if isinstance(decision, Exception):
            raise decision
        return decision


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


class FlakyTotal:
    """Inject transient failures into the local demo; no network call."""

    def __init__(self, failures):
        self.failures = failures
        self.calls = 0

    def __call__(self, **args):
        self.calls += 1
        if self.calls <= self.failures:
            raise ConnectionError("simulated_unavailable")
        return calculate_total(**args)


def total_call(quantity=4, unit_price=25000):
    return Decision("tool", "calculate_total",
                    {"quantity": quantity, "unit_price": unit_price})


def final(total=100000):
    return Decision("final", candidate={"total": total, "currency": "VND"})


def scenario(name):
    task, budget = Task(4, 25000), Budget()
    tools, clock = None, None
    decisions = [total_call(), final()]
    if name == "B":
        decisions = [total_call(), final(99999)]
    elif name == "C":
        task = Task(None, 25000)
    elif name == "D":
        tools = {"calculate_total": FlakyTotal(10)}
    elif name == "E":
        budget = Budget(max_steps=1)
    elif name == "F":
        budget = Budget(max_tool_calls=1)
        tools = {"calculate_total": FlakyTotal(1)}
    elif name == "G":
        clock = FakeClock()

        def slow_total(**args):
            clock.now += 11.0
            return calculate_total(**args)

        tools = {"calculate_total": slow_total}
    elif name == "H":
        decisions = [total_call(), total_call(), total_call()]
    elif name == "I":
        tools = {"calculate_total": FlakyTotal(1)}
    elif name == "J":
        task = Task(4, 25000, needs_approval=True)
    kwargs = {"budget": budget, "tools": tools}
    if clock is not None:
        kwargs["clock"] = clock
    return run_agent(ScriptedPlanner(decisions), task, **kwargs)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", choices=list("ABCDEFGHIJ"))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    for name in ([args.case] if args.case else list("ABCDEFGHIJ")):
        result = scenario(name)
        if args.json:
            print(json.dumps(asdict(result), ensure_ascii=False))
        else:
            print(f"{name}: status={result.status.value}; reason={result.reason}")
            print(f"  steps={result.steps}; tool_calls={result.tool_calls}")
            print(f"  output={result.output}; partial_results={len(result.partial_results)}")


if __name__ == "__main__":
    main()
