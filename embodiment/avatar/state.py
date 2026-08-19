from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(value)))


@dataclass
class AvatarState:
    gaze_x: float = 0.0
    gaze_y: float = 0.0

    eyelid_left: float = 0.0
    eyelid_right: float = 0.0

    brow: float = 0.0
    smile: float = 0.12
    mouth_open: float = 0.0

    head_yaw: float = 0.0
    head_pitch: float = 0.0

    attention: float = 0.0

    face_present: bool = False
    speaking: bool = False
    expression: str = "idle"

    def normalized(self) -> "AvatarState":
        self.gaze_x = clamp(self.gaze_x, -1.0, 1.0)
        self.gaze_y = clamp(self.gaze_y, -1.0, 1.0)

        self.eyelid_left = clamp(self.eyelid_left, 0.0, 1.0)
        self.eyelid_right = clamp(self.eyelid_right, 0.0, 1.0)

        self.brow = clamp(self.brow, -1.0, 1.0)
        self.smile = clamp(self.smile, 0.0, 1.0)
        self.mouth_open = clamp(self.mouth_open, 0.0, 1.0)

        self.head_yaw = clamp(self.head_yaw, -1.0, 1.0)
        self.head_pitch = clamp(self.head_pitch, -1.0, 1.0)

        self.attention = clamp(self.attention, 0.0, 1.0)

        return self

    def to_dict(self) -> dict[str, Any]:
        self.normalized()
        return asdict(self)
