from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GroundedMotorResult:
    ok: bool
    target_label: str = ""
    x: int = -1
    y: int = -1
    target_confidence: float = 0.0
    rendered_change: bool = False
    change_distance: float = 0.0
    error: str = ""


class GroundedMotorCapability:
    def __init__(self, *, verified_click):
        self.verified_click = verified_click

    def click_target(self, instruction):
        instruction = str(
            instruction or ""
        ).strip()

        if not instruction:
            return GroundedMotorResult(
                ok=False,
                error="empty_instruction",
            )

        value = self.verified_click.run(
            instruction
        )

        return GroundedMotorResult(
            ok=bool(
                getattr(value, "ok", False)
            ),
            target_label=str(
                getattr(
                    value,
                    "target_label",
                    "",
                )
            ),
            x=int(
                getattr(value, "x", -1)
            ),
            y=int(
                getattr(value, "y", -1)
            ),
            target_confidence=float(
                getattr(
                    value,
                    "target_confidence",
                    0.0,
                )
            ),
            rendered_change=bool(
                getattr(
                    value,
                    "changed",
                    False,
                )
            ),
            change_distance=float(
                getattr(
                    value,
                    "change_distance",
                    0.0,
                )
            ),
            error=str(
                getattr(value, "error", "")
            ),
        )
