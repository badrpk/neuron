from __future__ import annotations

import base64
import json
import subprocess
from pathlib import Path

from desktop.windows_bridge import WindowsBridge
from integration.bindings import bind_local_capabilities
from semantic.registry import build_default_registry


PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAAB"
    "CAQAAAC1HAwCAAAAC0lEQVR42mP8/x8"
    "AAusB9Wl2nAAAAABJRU5ErkJggg=="
)


def test_screen_observe_is_bound():
    registry = bind_local_capabilities(
        build_default_registry()
    )

    capability = registry.get(
        "screen.observe"
    )

    assert capability is not None
    assert capability.provider == "nifdu.screen"
    assert capability.executor is not None


def test_windows_screen_observation_decodes_real_png_contract(
    monkeypatch,
):
    bridge = WindowsBridge()

    payload = {
        "ok": True,
        "application": "notepad",
        "window_title": "example.txt - Notepad",
        "process_id": 4321,
        "window_handle": 123456,
        "bounds": {
            "left": 10,
            "top": 20,
            "right": 810,
            "bottom": 620,
            "width": 800,
            "height": 600,
        },
        "screen_bounds": {
            "left": 0,
            "top": 0,
            "width": 1920,
            "height": 1080,
        },
        "screenshot_format": "png",
        "screenshot_base64": base64.b64encode(
            PNG_1X1
        ).decode("ascii"),
    }

    def fake_powershell(command):
        assert "GetForegroundWindow" in command
        assert "CopyFromScreen" in command

        return subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=json.dumps(payload),
            stderr="",
        )

    monkeypatch.setattr(
        bridge,
        "_powershell",
        fake_powershell,
    )

    result = bridge.observe_screen()

    assert result.ok is True
    assert result.capability == "screen.observe"
    assert result.provider == "nifdu.screen"
    assert result.application == "notepad"
    assert result.window_title == "example.txt - Notepad"
    assert result.process_id == 4321
    assert result.window_handle == 123456
    assert result.bounds["width"] == 800
    assert result.screen_bounds["width"] == 1920
    assert result.screenshot_bytes == len(PNG_1X1)

    screenshot = Path(
        result.screenshot_path
    )

    try:
        assert screenshot.exists()
        assert screenshot.read_bytes() == PNG_1X1
    finally:
        screenshot.unlink(
            missing_ok=True
        )


def test_screen_observe_binding_returns_grounded_result(
    monkeypatch,
):
    registry = bind_local_capabilities(
        build_default_registry()
    )

    capability = registry.get(
        "screen.observe"
    )

    class FakeResult:
        def to_dict(self):
            return {
                "ok": True,
                "capability": "screen.observe",
                "provider": "nifdu.screen",
                "application": "chrome",
                "window_title": "Neuron",
                "screenshot_path": "/tmp/example.png",
            }

    def fake_observe(self):
        return FakeResult()

    monkeypatch.setattr(
        WindowsBridge,
        "observe_screen",
        fake_observe,
    )

    output = capability.executor({})

    assert output["ok"] is True
    assert output["provider"] == "nifdu.screen"
    assert output["application"] == "chrome"


def test_screen_observe_failure_is_not_faked(
    monkeypatch,
):
    bridge = WindowsBridge()

    def fake_powershell(command):
        return subprocess.CompletedProcess(
            args=[],
            returncode=1,
            stdout="",
            stderr="capture failed",
        )

    monkeypatch.setattr(
        bridge,
        "_powershell",
        fake_powershell,
    )

    result = bridge.observe_screen()

    assert result.ok is False
    assert result.screenshot_path == ""
    assert "capture failed" in result.stderr
