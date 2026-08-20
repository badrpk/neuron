from __future__ import annotations

from dataclasses import dataclass, field

from runtime.natural_instruction_router import (
    NaturalInstructionRouter,
)


@dataclass(frozen=True)
class PlanStep:
    capability: str
    arguments: dict = field(default_factory=dict)


@dataclass(frozen=True)
class InstructionPlan:
    ok: bool
    steps: tuple[PlanStep, ...] = ()
    error: str = ""


class SophyaneInstructionPlanner:
    ALLOWED_CAPABILITIES = frozenset({
        "desktop.open_url",
        "screen.visual_question",
        "visual_memory.retrieve",
    })

    def __init__(self):
        self.router = NaturalInstructionRouter()

    def plan(self, instruction):
        route = self.router.plan(instruction)

        if route.intent == "recall_visual_memory":
            return InstructionPlan(
                ok=True,
                steps=(
                    PlanStep(
                        "visual_memory.retrieve",
                        {"query": route.instruction},
                    ),
                ),
            )

        if route.intent == "open_url":
            return InstructionPlan(
                ok=True,
                steps=(
                    PlanStep(
                        "desktop.open_url",
                        {"url": route.url},
                    ),
                ),
            )

        if route.intent == "observe_screen":
            return InstructionPlan(
                ok=True,
                steps=(
                    PlanStep(
                        "screen.visual_question",
                        {"question": route.instruction},
                    ),
                ),
            )

        if route.intent == "open_and_observe":
            return InstructionPlan(
                ok=True,
                steps=(
                    PlanStep(
                        "desktop.open_url",
                        {"url": route.url},
                    ),
                    PlanStep(
                        "screen.visual_question",
                        {"question": route.instruction},
                    ),
                ),
            )

        return InstructionPlan(
            ok=False,
            error="unresolved_instruction",
        )
