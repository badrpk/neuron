from dataclasses import dataclass

import runtime.verified_visual_click as module
from runtime.verified_visual_click import (
    VerifiedVisualClick,
)


@dataclass
class Observation:
    screenshot_path: str


@dataclass
class VisionResult:
    ok: bool
    answer: str
    error: str = ""


@dataclass
class ClickResult:
    ok: bool
    error: str = ""


class FakeBridge:
    def __init__(self):
        self.calls = 0

    def observe_screen(self):
        self.calls += 1

        return Observation(
            screenshot_path=(
                "before.png"
                if self.calls == 1
                else "after.png"
            )
        )


class FakeMotor:
    def __init__(self):
        self.clicks = []

    def click(self, *, x, y):
        self.clicks.append(
            (x, y)
        )

        return ClickResult(
            ok=True
        )


class FakeVision:
    def ask_image(
        self,
        path,
        question,
    ):
        return VisionResult(
            ok=True,
            answer=(
                '{"target_found":true,'
                '"label":"Latest",'
                '"x":500,'
                '"y":200,'
                '"confidence":0.91,'
                '"reason":"visible button"}'
            ),
        )


class FakeFingerprint:
    @staticmethod
    def from_png(path):
        return FakeFingerprint()

    def compare(
        self,
        other,
        threshold,
    ):
        class Result:
            changed = True
            distance = 0.2

        return Result()


def test_grounded_click_verified(
    monkeypatch,
):
    monkeypatch.setattr(
        module,
        "ScreenFingerprint",
        FakeFingerprint,
    )

    motor = FakeMotor()

    controller = VerifiedVisualClick(
        bridge=FakeBridge(),
        motor=motor,
        vision=FakeVision(),
    )

    result = controller.run(
        "click Latest"
    )

    assert result.ok is True

    assert motor.clicks == [
        (500, 200)
    ]


def test_low_confidence_target_never_clicks():
    class WeakVision:
        def ask_image(
            self,
            path,
            question,
        ):
            return VisionResult(
                ok=True,
                answer=(
                    '{"target_found":true,'
                    '"label":"maybe",'
                    '"x":500,'
                    '"y":200,'
                    '"confidence":0.1,'
                    '"reason":"uncertain"}'
                ),
            )

    motor = FakeMotor()

    controller = VerifiedVisualClick(
        bridge=FakeBridge(),
        motor=motor,
        vision=WeakVision(),
    )

    result = controller.run(
        "click Latest"
    )

    assert result.ok is False
    assert motor.clicks == []
