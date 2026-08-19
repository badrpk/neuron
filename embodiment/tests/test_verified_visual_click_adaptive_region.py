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


@dataclass
class Recall:
    ok: bool = True
    x: int = 600
    y: int = 220
    weight: float = 0.95
    successes: int = 8
    failures: int = 0


class FakeRecall:
    def propose(
        self,
        **kwargs,
    ):
        return Recall()


class FakeRegion:
    crop_path = "crop.png"
    left = 520
    top = 160

    def to_absolute(
        self,
        *,
        local_x,
        local_y,
    ):
        return (
            self.left + local_x,
            self.top + local_y,
        )


class FakeCropper:
    def __init__(self):
        self.calls = []

    def crop_around(
        self,
        **kwargs,
    ):
        self.calls.append(
            kwargs
        )

        return FakeRegion()


class Bridge:
    def __init__(self):
        self.count = 0

    def observe_screen(self):
        self.count += 1

        return Observation(
            screenshot_path=(
                "before.png"
                if self.count == 1
                else "after.png"
            )
        )


class Motor:
    def click(
        self,
        *,
        x,
        y,
    ):
        return ClickResult(
            ok=True
        )


class Vision:
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
                '"x":80,'
                '"y":60,'
                '"confidence":0.95,'
                '"reason":"visible in crop"}'
            ),
        )


class Fingerprint:
    @staticmethod
    def from_png(path):
        return Fingerprint()

    def compare(
        self,
        other,
        threshold,
    ):
        class Result:
            changed = True
            distance = 0.2

        return Result()


def test_strong_memory_uses_tighter_crop(
    monkeypatch,
):
    monkeypatch.setattr(
        module,
        "ScreenFingerprint",
        Fingerprint,
    )

    cropper = FakeCropper()

    controller = VerifiedVisualClick(
        bridge=Bridge(),
        motor=Motor(),
        vision=Vision(),
        motor_recall=FakeRecall(),
    )

    controller.region_cropper = cropper

    result = controller.run(
        "click Latest"
    )

    assert result.ok is True

    assert len(
        cropper.calls
    ) == 1

    call = cropper.calls[0]

    assert call["radius_x"] == 80
    assert call["radius_y"] == 60
