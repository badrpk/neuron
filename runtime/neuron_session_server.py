from __future__ import annotations

import threading


class StateStore:
    ALLOWED = {
        "state",
        "visual_state",
        "message",
    }

    def __init__(self):
        self._lock = threading.RLock()
        self._state = {
            "state": "sleeping",
            "visual_state": "sleeping",
            "message": "",
            "version": 0,
        }

    def get(self):
        with self._lock:
            return dict(self._state)

    def update(self, **values):
        with self._lock:
            for key, value in values.items():
                if key in self.ALLOWED:
                    self._state[key] = value

            self._state["version"] += 1

            return dict(self._state)
