from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class PlanStep:
    capability: str

    arguments: dict[str, Any] = field(
        default_factory=dict
    )

    reason: str = ""

    confidence: float = 0.0

    depends_on: list[int] = field(
        default_factory=list
    )


@dataclass
class SemanticPlan:
    interpretation: str

    steps: list[PlanStep] = field(
        default_factory=list
    )

    reply: str | None = None

    clarification_needed: bool = False

    clarification_question: str | None = None

    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
