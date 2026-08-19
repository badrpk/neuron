from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class PresenceState:
    camera_available: bool = False
    microphone_available: bool = False

    scene_visible: bool = False
    face_present: bool = False

    face_count: int = 0

    primary_face_center_x: float | None = None
    primary_face_center_y: float | None = None

    frame_width: int | None = None
    frame_height: int | None = None

    identity_state: str = "unknown"
    active_speaker: bool = False

    owner_verified: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
