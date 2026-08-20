from __future__ import annotations

from dataclasses import dataclass

import perception.screen_change as screen_change
from perception.visual_region import PNGRegionCropper
from perception.visual_targeting import VisualTargeting


ScreenFingerprint = screen_change.ScreenFingerprint
_ORIGINAL_SCREEN_FINGERPRINT = ScreenFingerprint


@dataclass(frozen=True)
class VerifiedClickResult:
    ok: bool
    target_label: str = ""
    x: int = -1
    y: int = -1
    target_confidence: float = 0.0
    changed: bool = False
    change_distance: float = 0.0
    error: str = ""


class VerifiedVisualClick:
    def __init__(
        self,
        *,
        bridge,
        motor,
        vision,
        motor_recall=None,
        minimum_confidence=0.55,
        change_threshold=0.08,
    ):
        self.bridge = bridge
        self.motor = motor
        self.vision = vision
        self.motor_recall = motor_recall

        self.targeting = VisualTargeting(
            minimum_confidence=minimum_confidence
        )

        self.minimum_confidence = float(
            minimum_confidence
        )

        self.change_threshold = float(
            change_threshold
        )

        self.region_cropper = (
            PNGRegionCropper()
        )

    def _target(
        self,
        path,
        instruction,
    ):
        response = self.vision.ask_image(
            path,
            self.targeting.targeting_question(
                instruction
            ),
        )

        if not getattr(
            response,
            "ok",
            False,
        ):
            return None

        return self.targeting.parse(
            getattr(
                response,
                "answer",
                "",
            )
        )

    @staticmethod
    def _strong_recall(recall):
        return (
            bool(
                getattr(
                    recall,
                    "ok",
                    False,
                )
            )
            and float(
                getattr(
                    recall,
                    "weight",
                    0.0,
                )
            ) >= 0.75
            and int(
                getattr(
                    recall,
                    "successes",
                    0,
                )
            ) >= 3
        )

    def _crop(
        self,
        screenshot,
        recall,
        *,
        wide=False,
    ):
        if wide:
            rx, ry = 320, 240
        elif self._strong_recall(recall):
            rx, ry = 80, 60
        else:
            rx, ry = 160, 120

        return self.region_cropper.crop_around(
            screenshot_path=screenshot,
            x=int(recall.x),
            y=int(recall.y),
            radius_x=rx,
            radius_y=ry,
        )

    def _compare(self, before, after):
        #
        # Preserve the historical class seam used by tests.
        #
        if (
            ScreenFingerprint
            is not _ORIGINAL_SCREEN_FINGERPRINT
        ):
            previous = (
                ScreenFingerprint.from_png(
                    before
                )
            )

            current = (
                ScreenFingerprint.from_png(
                    after
                )
            )

            return previous.compare(
                current,
                self.change_threshold,
            )

        previous = screen_change.fingerprint(
            before
        )

        current = screen_change.fingerprint(
            after
        )

        return screen_change.compare(
            previous,
            current,
            threshold=self.change_threshold,
        )

    def run(self, instruction):
        instruction = str(
            instruction or ""
        ).strip()

        if not instruction:
            return VerifiedClickResult(
                False,
                error="empty_instruction",
            )

        before = self.bridge.observe_screen()

        screenshot = str(
            getattr(
                before,
                "screenshot_path",
                "",
            )
        )

        if not screenshot:
            return VerifiedClickResult(
                False,
                error="screen_observation_failed",
            )

        recall = None
        region = None
        target = None

        if self.motor_recall is not None:
            recall = self.motor_recall.propose(
                screenshot_path=screenshot,
                instruction=instruction,
                semantic_gist=instruction,
            )

        if recall is not None and getattr(
            recall,
            "ok",
            False,
        ):
            region = self._crop(
                screenshot,
                recall,
            )

            target = self._target(
                region.crop_path,
                instruction,
            )

            if not (
                target
                and target.ok
            ):
                region = self._crop(
                    screenshot,
                    recall,
                    wide=True,
                )

                target = self._target(
                    region.crop_path,
                    instruction,
                )

            if not (
                target
                and target.ok
            ):
                region = None
                target = self._target(
                    screenshot,
                    instruction,
                )

        else:
            target = self._target(
                screenshot,
                instruction,
            )

        if not (
            target
            and target.ok
            and target.confidence
                >= self.minimum_confidence
        ):
            return VerifiedClickResult(
                False,
                target_label=(
                    target.label
                    if target else ""
                ),
                target_confidence=(
                    target.confidence
                    if target else 0.0
                ),
                error="target_not_grounded",
            )

        if region is not None:
            x, y = region.to_absolute(
                local_x=target.x,
                local_y=target.y,
            )
        else:
            x, y = target.x, target.y

        click = self.motor.click(
            x=int(x),
            y=int(y),
        )

        if not getattr(
            click,
            "ok",
            False,
        ):
            return VerifiedClickResult(
                False,
                target_label=target.label,
                x=int(x),
                y=int(y),
                target_confidence=(
                    target.confidence
                ),
                error=str(
                    getattr(
                        click,
                        "error",
                        "click_failed",
                    )
                ),
            )

        after = self.bridge.observe_screen()

        after_path = str(
            getattr(
                after,
                "screenshot_path",
                "",
            )
        )

        comparison = self._compare(
            screenshot,
            after_path,
        )

        return VerifiedClickResult(
            ok=bool(
                getattr(
                    comparison,
                    "changed",
                    False,
                )
            ),
            target_label=target.label,
            x=int(x),
            y=int(y),
            target_confidence=(
                target.confidence
            ),
            changed=bool(
                getattr(
                    comparison,
                    "changed",
                    False,
                )
            ),
            change_distance=float(
                getattr(
                    comparison,
                    "distance",
                    0.0,
                )
            ),
            error=(
                ""
                if getattr(
                    comparison,
                    "changed",
                    False,
                )
                else "screen_unchanged"
            ),
        )
