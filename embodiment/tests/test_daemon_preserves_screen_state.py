from __future__ import annotations

import json

from runtime.embodiment_daemon import EmbodimentRuntime


class FakeAvatarResult:
    def to_dict(self):
        return {
            "state": "idle",
        }


class FakeAvatar:
    def tick(self):
        return FakeAvatarResult()


class FakePresence:
    identity_state = "unknown"
    owner_verified = False

    def to_dict(self):
        return {
            "present": False,
            "frame_width": None,
            "frame_height": None,
        }


def test_daemon_preserves_independent_screen_state(
    tmp_path,
):
    state_path = (
        tmp_path
        / "state.json"
    )

    events_path = (
        tmp_path
        / "events.jsonl"
    )

    original_screen = {
        "grounded": True,
        "provider": "nifdu.screen",
        "application": "powershell",
        "window_title": "Neuron Screen Test",
        "screenshot_path": "/tmp/neuron-screen-test.png",
        "screenshot_format": "png",
        "screenshot_bytes": 123456,
    }

    state_path.write_text(
        json.dumps(
            {
                "screen":
                    original_screen,

                "external_future_field": {
                    "preserve_me": True,
                },
            }
        )
    )

    runtime = EmbodimentRuntime(
        state_path,
        events_path,
    )

    runtime.avatar = FakeAvatar()
    runtime.presence = FakePresence()

    runtime.write_state()

    result = json.loads(
        state_path.read_text()
    )

    #
    # Independently owned state survives.
    #

    assert result["screen"] == original_screen

    assert (
        result["external_future_field"]
        ==
        {
            "preserve_me": True,
        }
    )

    #
    # Daemon-owned fields are still authoritative.
    #

    assert (
        result["schema"]
        ==
        "neuron.embodiment.state.v1"
    )

    assert "timestamp" in result
    assert "pid" in result

    assert result["presence"] == {
        "present": False,
        "frame_width": None,
        "frame_height": None,
    }

    assert result["avatar"] == {
        "state": "idle",
    }

    assert (
        result["desktop"]["routine_actions_enabled"]
        is True
    )


def test_daemon_overwrites_stale_daemon_owned_values(
    tmp_path,
):
    state_path = (
        tmp_path
        / "state.json"
    )

    events_path = (
        tmp_path
        / "events.jsonl"
    )

    state_path.write_text(
        json.dumps(
            {
                "schema":
                    "stale",

                "pid":
                    -1,

                "desktop": {
                    "routine_actions_enabled":
                        False,
                },

                "screen": {
                    "grounded":
                        True,
                },
            }
        )
    )

    runtime = EmbodimentRuntime(
        state_path,
        events_path,
    )

    runtime.avatar = FakeAvatar()
    runtime.presence = FakePresence()

    runtime.write_state()

    result = json.loads(
        state_path.read_text()
    )

    assert (
        result["schema"]
        ==
        "neuron.embodiment.state.v1"
    )

    assert result["pid"] != -1

    assert (
        result["desktop"]["routine_actions_enabled"]
        is True
    )

    assert result["screen"] == {
        "grounded": True,
    }
