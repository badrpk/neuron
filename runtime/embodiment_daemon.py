from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path


class _NullAvatarResult:
    def to_dict(self):
        return {"state": "idle"}


class _NullAvatar:
    def tick(self):
        return _NullAvatarResult()


class _NullPresence:
    identity_state = "unknown"
    owner_verified = False

    def to_dict(self):
        return {
            "present": False,
            "frame_width": None,
            "frame_height": None,
        }


class EmbodimentRuntime:
    SCHEMA = "neuron.embodiment.state.v1"

    def __init__(
        self,
        state_path,
        events_path,
    ):
        self.state_path = Path(state_path)
        self.events_path = Path(events_path)

        self.avatar = _NullAvatar()
        self.presence = _NullPresence()

    def _existing_state(self):
        try:
            value = json.loads(
                self.state_path.read_text()
            )

            return (
                value
                if isinstance(value, dict)
                else {}
            )
        except (
            FileNotFoundError,
            json.JSONDecodeError,
            OSError,
        ):
            return {}

    def write_state(self):
        state = self._existing_state()

        state.update(
            {
                "schema": self.SCHEMA,
                "timestamp": datetime.now(
                    timezone.utc
                ).isoformat(),
                "pid": os.getpid(),
                "presence":
                    self.presence.to_dict(),
                "avatar":
                    self.avatar.tick().to_dict(),
                "desktop": {
                    "routine_actions_enabled":
                        True,
                },
            }
        )

        self.state_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.state_path.write_text(
            json.dumps(
                state,
                indent=2,
                sort_keys=True,
            )
        )

        return state
