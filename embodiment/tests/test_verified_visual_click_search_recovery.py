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


class Region:
    def __init__(
        self,
        name,
        left,
        top,
    ):
        self.crop_path = name
        self.left = left
        self.top = top

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


class Cropper:
    def __init__(self):
        self.calls = []

    def crop_around(
        self,
        **kwargs,
    ):
        self.calls.append(
            kwargs
        )

        if len(self.calls) == 1:
            return Region(
                "tight.png",
                520,
                160,
            )

        return Region(
            "wide.png",
            280,
            0,
        )


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


class VisionWideRecovery:
    def __init__(self):
        self.paths = []

    def ask_image(
        self,
        path,
        question,
    ):
        self.paths.append(path)

        if path == "tight.png":
            answer = (
                '{"target_found":false,'
                '"label":"",'
                '"x":0,'
                '"y":0,'
                '"confidence":0.1,'
                '"reason":"not visible"}'
            )

        else:
            answer = (
                '{"target_found":true,'
                '"label":"Latest",'
                '"x":320,'
                '"y":220,'
                '"confidence":0.95,'
                '"reason":"visible in wider crop"}'
            )

        return VisionResult(
            ok=True,
            answer=answer,
        )


class VisionFullRecovery:
    def __init__(self):
        self.paths = []

    def ask_image(
        self,
        path,
        question,
    ):
        self.paths.append(path)

        if path in (
            "tight.png",
            "wide.png",
        ):
            answer = (
                '{"target_found":false,'
                '"label":"",'
                '"x":0,'
                '"y":0,'
                '"confidence":0.1,'
                '"reason":"not visible"}'
            )

        else:
            answer = (
                '{"target_found":true,'
                '"label":"Latest",'
                '"x":600,'
                '"y":220,'
                '"confidence":0.95,'
                '"reason":"visible full screen"}'
            )

        return VisionResult(
            ok=True,
            answer=answer,
        )


def build(
    monkeypatch,
    vision,
):
    monkeypatch.setattr(
        module,
        "ScreenFingerprint",
        Fingerprint,
    )

    cropper = Cropper()
    motor = Motor()

    controller = VerifiedVisualClick(
        bridge=Bridge(),
        motor=motor,
        vision=vision,
        motor_recall=FakeRecall(),
    )

    controller.region_cropper = cropper

    return (
        controller,
        cropper,
        motor,
    )


def test_tight_failure_widens_once(
    monkeypatch,
):
    vision = VisionWideRecovery()

    (
        controller,
        cropper,
        motor,
    ) = build(
        monkeypatch,
        vision,
    )

    result = controller.run(
        "click Latest"
    )

    assert result.ok is True

    assert vision.paths[:2] == [
        "tight.png",
        "wide.png",
    ]

    assert len(
        cropper.calls
    ) == 2

    assert (
        cropper.calls[1]["radius_x"]
        == 320
    )

    assert (
        cropper.calls[1]["radius_y"]
        == 240
    )

    #
    # Wide local (320,220)
    # + crop origin (280,0)
    # = absolute (600,220)
    #
    assert motor.clicks == [
        (
            600,
            220,
        )
    ]


def test_two_local_failures_use_full_screen(
    monkeypatch,
):
    vision = VisionFullRecovery()

    (
        controller,
        cropper,
        motor,
    ) = build(
        monkeypatch,
        vision,
    )

    result = controller.run(
        "click Latest"
    )

    assert result.ok is True

    assert vision.paths == [
        "tight.png",
        "wide.png",
        "before.png",
    ]

    assert len(
        cropper.calls
    ) == 2

    #
    # Full-screen target coordinates are absolute.
    #
    assert motor.clicks == [
        (
            600,
            220,
        )
    ]
