from dataclasses import dataclass

from runtime.grounded_motor_capability import (
    GroundedMotorCapability,
)


@dataclass
class Result:
    ok: bool
    target_label: str = "Latest"
    x: int = 500
    y: int = 200
    target_confidence: float = 0.9
    changed: bool = True
    change_distance: float = 0.15
    error: str = ""


class FakeVerifiedClick:
    def __init__(self):
        self.instructions = []

    def run(
        self,
        instruction,
    ):
        self.instructions.append(
            instruction
        )

        return Result(
            ok=True
        )


def test_planner_passes_semantic_target_only():
    verified = FakeVerifiedClick()

    cap = GroundedMotorCapability(
        verified_click=verified
    )

    result = cap.click_target(
        "click the Latest tab"
    )

    assert result.ok is True

    assert verified.instructions == [
        "click the Latest tab"
    ]


def test_empty_instruction_rejected():
    cap = GroundedMotorCapability(
        verified_click=FakeVerifiedClick()
    )

    result = cap.click_target(
        ""
    )

    assert result.ok is False


def test_result_preserves_verified_coordinate():
    cap = GroundedMotorCapability(
        verified_click=FakeVerifiedClick()
    )

    result = cap.click_target(
        "click Latest"
    )

    assert result.x == 500
    assert result.y == 200
    assert result.rendered_change is True
