from dataclasses import dataclass, field
from enum import Enum
from math import isfinite


class Status(str, Enum):
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    BUDGET_EXHAUSTED = "budget_exhausted"


@dataclass(frozen=True)
class Task:
    quantity: int | None
    unit_price: int | None
    needs_approval: bool = False
    approved: bool = False


@dataclass(frozen=True)
class Budget:
    max_steps: int = 4
    max_tool_calls: int = 3
    max_seconds: float = 90.0
    max_retries: int = 1
    max_same_call: int = 2

    def __post_init__(self):
        for name in ("max_steps", "max_tool_calls", "max_same_call"):
            value = getattr(self, name)
            if type(value) is not int or value < 1:
                raise ValueError(f"{name} must be a positive integer")
        if type(self.max_retries) is not int or self.max_retries < 0:
            raise ValueError("max_retries must be a non-negative integer")
        if (type(self.max_seconds) not in (int, float)
                or not isfinite(self.max_seconds) or self.max_seconds <= 0):
            raise ValueError("max_seconds must be positive and finite")


@dataclass(frozen=True)
class Decision:
    kind: str
    tool: str = ""
    args: dict = field(default_factory=dict)
    candidate: dict = field(default_factory=dict)


@dataclass
class RunResult:
    status: Status
    reason: str
    steps: int
    tool_calls: int
    output: dict | None
    partial_results: list
    trace: list
    next_action: str


def validate_final(task, candidate, evidence):
    if (type(candidate) is not dict
            or set(candidate) != {"total", "currency"}
            or type(candidate["total"]) is not int
            or candidate["currency"] != "VND"):
        return False
    expected_args = {"quantity": task.quantity, "unit_price": task.unit_price}
    return (candidate["total"] == task.quantity * task.unit_price
            and any(item["tool"] == "calculate_total"
                    and item["args"] == expected_args
                    and item["data"] == candidate for item in evidence))
