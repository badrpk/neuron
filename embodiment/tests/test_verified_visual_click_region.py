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


class FakeRecall:
    def propose(
        self,
        **kwargs,
    ):
        return Recall()


class FakeRegion:
    crop_path = "crop.png"

    left = 400
    top = 100

    def to_absolute(
        self,
        *,
        local_x,
        local_y,
    ):
        return (
            self.left
            + local_x,
            self.top
            + local_y,
        )


class FakeCropper:
    def crop_around(
        self,
        **kwargs,
    ):
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
    def __init__(self):
        self.clicks = []

    def click(
        self,
        *,
        x,
        y,
    ):
        self.clicks.append(
            (
                x,
                y,
            )
        )

        return ClickResult(
            ok=True
        )


class Vision:
    def __init__(self):
        self.paths = []

    def ask_image(
        self,
        path,
        question,
    ):
        self.paths.append(
            path
        )

        return VisionResult(
            ok=True,
            answer=(
                '{"target_found":true,'
                '"label":"Latest",'
                '"x":50,'
                '"y":40,'
                '"confidence":0.9,'
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
            distance = 0.20

        return Result()


def test_memory_region_is_visually_rechecked(
    monkeypatch,
):
    monkeypatch.setattr(
        module,
        "ScreenFingerprint",
        Fingerprint,
    )

    motor = Motor()
    vision = Vision()

    controller = VerifiedVisualClick(
        bridge=Bridge(),
        motor=motor,
        vision=vision,
        motor_recall=FakeRecall(),
    )

    controller.region_cropper = (
        FakeCropper()
    )

    result = controller.run(
        "click Latest"
    )

    assert result.ok is True

    #
    # Vision was run against the CURRENT local crop.
    #
    assert vision.paths[0] == (
        "crop.png"
    )

    #
    # Gemma's local (50,40) gets translated through
    # crop origin (400,100).
    #
    assert motor.clicks == [
        (
            450,
            140,
        )
    ]

    assert result.x == 450
    assert result.y == 140
