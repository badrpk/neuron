from __future__ import annotations

from dataclasses import dataclass, field

from runtime.sophyane_instruction_planner import (
    SophyaneInstructionPlanner,
)


@dataclass(frozen=True)
class Evidence:
    capability: str
    result: dict


@dataclass(frozen=True)
class ClosedLoopResult:
    ok: bool
    completed: bool
    steps_used: int
    evidence: tuple[Evidence, ...] = field(
        default_factory=tuple
    )
    error: str = ""


class ClosedLoopPerceptualPlanner:
    def __init__(
        self,
        *,
        bridge,
        visual_question,
        max_steps=4,
        planner=None,
    ):
        self.bridge = bridge
        self.visual_question = visual_question
        self.max_steps = max(1, int(max_steps))
        self.planner = (
            planner
            or SophyaneInstructionPlanner()
        )

    @staticmethod
    def _dict(value):
        if isinstance(value, dict):
            return value

        fn = getattr(value, "to_dict", None)

        if callable(fn):
            return fn()

        return {
            "ok": bool(
                getattr(value, "ok", False)
            )
        }

    def run(self, instruction):
        plan = self.planner.plan(instruction)

        if not plan.ok:
            return ClosedLoopResult(
                False,
                False,
                0,
                error=plan.error,
            )

        evidence = []

        for step in plan.steps[:self.max_steps]:
            if step.capability == "desktop.open_url":
                value = self.bridge.open_url(
                    step.arguments["url"]
                )
                result = self._dict(value)

            elif step.capability == "screen.visual_question":
                result = self._dict(
                    self.visual_question(
                        {
                            "question":
                                step.arguments[
                                    "question"
                                ]
                        }
                    )
                )

            else:
                return ClosedLoopResult(
                    False,
                    False,
                    len(evidence),
                    tuple(evidence),
                    "unsupported_capability",
                )

            evidence.append(
                Evidence(
                    step.capability,
                    result,
                )
            )

            if not result.get("ok", False):
                return ClosedLoopResult(
                    False,
                    False,
                    len(evidence),
                    tuple(evidence),
                    "step_failed",
                )

        completed = (
            len(evidence)
            == len(plan.steps)
        )

        return ClosedLoopResult(
            ok=completed,
            completed=completed,
            steps_used=len(evidence),
            evidence=tuple(evidence),
            error="" if completed else "step_budget_exhausted",
        )
