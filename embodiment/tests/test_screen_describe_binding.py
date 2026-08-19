from __future__ import annotations

import json
from pathlib import Path

import integration.bindings as bindings
from desktop.windows_bridge import WindowsBridge
from semantic.registry import build_default_registry


def test_screen_describe_is_bound():
    registry = bindings.bind_local_capabilities(
        build_default_registry()
    )

    capability = registry.get(
        "screen.describe"
    )

    assert capability is not None
    assert capability.provider == "nifdu.screen"
    assert capability.executor is not None


def test_screen_observe_persists_grounded_state(
    monkeypatch,
    tmp_path,
):
    state_path = (
        tmp_path
        / "state.json"
    )

    monkeypatch.setattr(
        bindings,
        "STATE_PATH",
        state_path,
    )

    class FakeResult:
        def to_dict(self):
            return {
                "ok":
                    True,

                "capability":
                    "screen.observe",

                "provider":
                    "nifdu.screen",

                "application":
                    "chrome",

                "window_title":
                    "Neuron Test",

                "process_id":
                    123,

                "window_handle":
                    456,

                "bounds":
                    {
                        "left": 10,
                        "top": 20,
                        "right": 1010,
                        "bottom": 720,
                        "width": 1000,
                        "height": 700,
                    },

                "screen_bounds":
                    {
                        "left": 0,
                        "top": 0,
                        "width": 1920,
                        "height": 1080,
                    },

                "screenshot_path":
                    "/tmp/neuron-test.png",

                "screenshot_format":
                    "png",

                "screenshot_bytes":
                    999,
            }

    monkeypatch.setattr(
        WindowsBridge,
        "observe_screen",
        lambda self: FakeResult(),
    )

    registry = bindings.bind_local_capabilities(
        build_default_registry()
    )

    observe = registry.get(
        "screen.observe"
    )

    output = observe.executor(
        {}
    )

    assert output["ok"] is True
    assert output["screen_state"]["grounded"] is True

    state = json.loads(
        state_path.read_text()
    )

    assert (
        state["screen"]["application"]
        == "chrome"
    )

    assert (
        state["screen"]["window_title"]
        == "Neuron Test"
    )

    assert (
        state["screen"]["screenshot_path"]
        == "/tmp/neuron-test.png"
    )


def test_screen_describe_uses_persisted_grounded_state(
    monkeypatch,
    tmp_path,
):
    state_path = (
        tmp_path
        / "state.json"
    )

    monkeypatch.setattr(
        bindings,
        "STATE_PATH",
        state_path,
    )

    state_path.write_text(
        json.dumps(
            {
                "screen": {
                    "grounded":
                        True,

                    "provider":
                        "nifdu.screen",

                    "application":
                        "powershell",

                    "window_title":
                        "badrpk@Badar: ~/nifdu",

                    "screen_bounds":
                        {
                            "left": 0,
                            "top": 0,
                            "width": 1536,
                            "height": 864,
                        },

                    "screenshot_path":
                        "/tmp/neuron-screen.png",

                    "screenshot_bytes":
                        164290,
                }
            }
        )
    )

    registry = bindings.bind_local_capabilities(
        build_default_registry()
    )

    describe = registry.get(
        "screen.describe"
    )

    result = describe.executor(
        {}
    )

    assert result["ok"] is True
    assert result["grounded"] is True
    assert result["provider"] == "nifdu.screen"

    assert (
        "powershell"
        in result["description"]
    )

    assert (
        "1536 by 864"
        in result["description"]
    )

    assert (
        result["screenshot_path"]
        == "/tmp/neuron-screen.png"
    )


def test_screen_describe_refuses_ungrounded_state(
    monkeypatch,
    tmp_path,
):
    state_path = (
        tmp_path
        / "state.json"
    )

    monkeypatch.setattr(
        bindings,
        "STATE_PATH",
        state_path,
    )

    state_path.write_text(
        json.dumps(
            {
                "screen": {
                    "grounded":
                        False,

                    "last_error":
                        "capture failed",
                }
            }
        )
    )

    registry = bindings.bind_local_capabilities(
        build_default_registry()
    )

    describe = registry.get(
        "screen.describe"
    )

    result = describe.executor(
        {}
    )

    assert result["ok"] is False

    assert (
        result["status"]
        == "no_grounded_screen_observation"
    )

    assert result["description"] == ""
