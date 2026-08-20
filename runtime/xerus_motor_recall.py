from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MotorRecallProposal:
    ok: bool
    x: int = -1
    y: int = -1
    weight: float = 0.0
    successes: int = 0
    failures: int = 0
    error: str = ""


class XerusMotorRecall:
    def __init__(
        self,
        *,
        motor_learning,
        minimum_weight=0.30,
        minimum_successes=2,
    ):
        self.motor_learning = motor_learning
        self.minimum_weight = float(
            minimum_weight
        )
        self.minimum_successes = int(
            minimum_successes
        )

    def propose(
        self,
        *,
        screenshot_path,
        instruction,
        semantic_gist="",
    ):
        try:
            association = (
                self.motor_learning
                .recall_for_context(
                    screenshot_path=screenshot_path,
                    instruction=instruction,
                    semantic_gist=semantic_gist,
                )
            )
        except TypeError:
            association = (
                self.motor_learning
                .recall_for_context(
                    screenshot_path=screenshot_path,
                    semantic_gist=(
                        semantic_gist
                        or instruction
                    ),
                )
            )

        if association is None:
            return MotorRecallProposal(
                ok=False,
                error="no_association",
            )

        weight = float(
            getattr(
                association,
                "weight",
                0.0,
            )
        )

        successes = int(
            getattr(
                association,
                "successes",
                0,
            )
        )

        failures = int(
            getattr(
                association,
                "failures",
                0,
            )
        )

        base = dict(
            x=int(
                getattr(
                    association,
                    "last_x",
                    -1,
                )
            ),
            y=int(
                getattr(
                    association,
                    "last_y",
                    -1,
                )
            ),
            weight=weight,
            successes=successes,
            failures=failures,
        )

        if weight < self.minimum_weight:
            return MotorRecallProposal(
                ok=False,
                error="weak_association",
                **base,
            )

        if successes < self.minimum_successes:
            return MotorRecallProposal(
                ok=False,
                error="insufficient_successes",
                **base,
            )

        return MotorRecallProposal(
            ok=True,
            **base,
        )
