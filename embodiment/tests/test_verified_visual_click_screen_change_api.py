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


class Bridge:
    def __init__(
        self,
    ):
        self.count = 0

    def observe_screen(
        self,
    ):
        self.count += 1

        return Observation(
            screenshot_path=(
                "before.png"
                if self.count == 1
                else "after.png"
            )
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
                '"x":100,'
                '"y":120,'
                '"confidence":0.95,'
                '"reason":"visible"}'
            ),
        )


class Motor:
    def __init__(
        self,
    ):
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


class FP:
    def __init__(
        self,
        path,
    ):
        self.path = path


@dataclass
class Comparison:
    changed: bool
    distance: float


def test_production_uses_function_api(
    monkeypatch,
):
    calls = []

    def fingerprint(
        path,
    ):
        calls.append(
            (
                "fingerprint",
                path,
            )
        )

        return FP(
            path
        )

    def compare(
        previous,
        current,
        *,
        threshold,
    ):
        calls.append(
            (
                "compare",
                previous.path,
                current.path,
                threshold,
            )
        )

        return Comparison(
            changed=True,
            distance=0.25,
        )

    monkeypatch.setattr(
        module.screen_change,
        "fingerprint",
        fingerprint,
    )

    monkeypatch.setattr(
        module.screen_change,
        "compare",
        compare,
    )

    assert (
        module.ScreenFingerprint
        is module._ORIGINAL_SCREEN_FINGERPRINT
    )

    motor = Motor()

    controller = VerifiedVisualClick(
        bridge=Bridge(),
        motor=motor,
        vision=Vision(),
    )

    result = controller.run(
        "click Latest"
    )

    assert result.ok is True

    assert motor.clicks == [
        (
            100,
            120,
        )
    ]

    assert calls == [
        (
            "fingerprint",
            "before.png",
        ),
        (
            "fingerprint",
            "after.png",
        ),
        (
            "compare",
            "before.png",
            "after.png",
            controller.change_threshold,
        ),
    ]


class LegacyFP:
    paths = []

    @classmethod
    def from_png(
        cls,
        path,
    ):
        cls.paths.append(
            path
        )

        return cls()

    def compare(
        self,
        other,
        threshold,
    ):
        return Comparison(
            changed=True,
            distance=0.3,
        )


def test_legacy_test_seam_still_works(
    monkeypatch,
):
    LegacyFP.paths = []

    monkeypatch.setattr(
        module,
        "ScreenFingerprint",
        LegacyFP,
    )

    monkeypatch.setattr(
        module.screen_change,
        "fingerprint",
        lambda path: (
            (_ for _ in ())
            .throw(
                AssertionError(
                    "production fingerprint unexpectedly used"
                )
            )
        ),
    )

    controller = VerifiedVisualClick(
        bridge=Bridge(),
        motor=Motor(),
        vision=Vision(),
    )

    result = controller.run(
        "click Latest"
    )

    assert result.ok is True

    assert LegacyFP.paths == [
        "before.png",
        "after.png",
    ]
