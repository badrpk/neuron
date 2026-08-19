from __future__ import annotations

import math
import random
import time

from avatar.state import AvatarState, clamp


class AvatarController:
    def __init__(self) -> None:
        self.state = AvatarState()

        now = time.monotonic()

        self._next_blink = now + random.uniform(2.5, 5.5)
        self._blink_until = 0.0

        self._next_wink = now + random.uniform(18.0, 35.0)
        self._wink_until = 0.0
        self._wink_eye = None

        self._target_gaze_x = 0.0
        self._target_gaze_y = 0.0

        self._last_tick = now

    def set_face_target(
        self,
        center_x: float,
        center_y: float,
        frame_width: float,
        frame_height: float,
    ) -> None:

        if frame_width <= 0 or frame_height <= 0:
            return

        nx = (center_x / frame_width) * 2.0 - 1.0
        ny = (center_y / frame_height) * 2.0 - 1.0

        self._target_gaze_x = clamp(nx, -1.0, 1.0)
        self._target_gaze_y = clamp(ny, -1.0, 1.0)

        self.state.face_present = True
        self.state.attention = 1.0
        self.state.expression = "attentive"

    def clear_face_target(self) -> None:
        self.state.face_present = False
        self.state.attention = 0.15

        self._target_gaze_x = 0.0
        self._target_gaze_y = 0.0

        if not self.state.speaking:
            self.state.expression = "idle"

    def set_speaking(
        self,
        speaking: bool,
        amplitude: float = 0.0,
    ) -> None:

        self.state.speaking = bool(speaking)

        if speaking:
            self.state.mouth_open = clamp(
                0.15 + amplitude * 1.3,
                0.05,
                0.95,
            )

            self.state.smile = max(
                self.state.smile,
                0.16,
            )

            self.state.expression = "speaking"

        else:
            self.state.mouth_open = 0.0

            if self.state.face_present:
                self.state.expression = "attentive"
            else:
                self.state.expression = "idle"

    def smile(self, amount: float = 0.6) -> None:
        self.state.smile = clamp(
            amount,
            0.0,
            1.0,
        )

    def tick(self) -> AvatarState:
        now = time.monotonic()

        dt = max(
            0.001,
            min(
                0.1,
                now - self._last_tick,
            ),
        )

        self._last_tick = now

        #
        # Smooth gaze.
        #

        smoothing = 1.0 - math.exp(
            -8.0 * dt
        )

        self.state.gaze_x += (
            self._target_gaze_x
            - self.state.gaze_x
        ) * smoothing

        self.state.gaze_y += (
            self._target_gaze_y
            - self.state.gaze_y
        ) * smoothing

        #
        # Head follows gaze more slowly.
        #

        head_smoothing = 1.0 - math.exp(
            -3.5 * dt
        )

        target_yaw = (
            self._target_gaze_x
            * 0.45
        )

        target_pitch = (
            self._target_gaze_y
            * 0.25
        )

        self.state.head_yaw += (
            target_yaw
            - self.state.head_yaw
        ) * head_smoothing

        self.state.head_pitch += (
            target_pitch
            - self.state.head_pitch
        ) * head_smoothing

        #
        # Natural blink.
        #

        if (
            now >= self._next_blink
            and
            now >= self._blink_until
        ):

            self._blink_until = (
                now
                + random.uniform(
                    0.09,
                    0.16,
                )
            )

            self._next_blink = (
                now
                + random.uniform(
                    2.4,
                    5.8,
                )
            )

        blinking = (
            now < self._blink_until
        )

        #
        # Occasional wink.
        #

        if (
            now >= self._next_wink
            and
            now >= self._wink_until
            and
            not blinking
        ):

            self._wink_until = (
                now + 0.22
            )

            self._wink_eye = random.choice(
                ("left", "right")
            )

            self._next_wink = (
                now
                + random.uniform(
                    20.0,
                    45.0,
                )
            )

        winking = (
            now < self._wink_until
        )

        if blinking:
            self.state.eyelid_left = 1.0
            self.state.eyelid_right = 1.0

        elif winking:

            if self._wink_eye == "left":
                self.state.eyelid_left = 1.0
                self.state.eyelid_right = 0.0
            else:
                self.state.eyelid_left = 0.0
                self.state.eyelid_right = 1.0

        else:
            self.state.eyelid_left = 0.0
            self.state.eyelid_right = 0.0

        return self.state.normalized()
