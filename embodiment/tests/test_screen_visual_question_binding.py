from __future__ import annotations

from desktop.windows_bridge import (
    WindowsBridge,
)
from integration.bindings import (
    bind_local_capabilities,
)
from perception.vision_client import (
    VisionClient,
    VisionQuestionResult,
)
from semantic.registry import (
    build_default_registry,
)


class FakeScreenResult:
    def to_dict(self):
        return {
            "ok":
                True,

            "capability":
                "screen.observe",

            "provider":
                "nifdu.screen",

            "application":
                "powershell",

            "window_title":
                "Neuron Test",

            "process_id":
                123,

            "window_handle":
                456,

            "bounds":
                {
                    "left": 0,
                    "top": 0,
                    "right": 100,
                    "bottom": 100,
                    "width": 100,
                    "height": 100,
                },

            "screen_bounds":
                {
                    "left": 0,
                    "top": 0,
                    "width": 1920,
                    "height": 1080,
                },

            "screenshot_path":
                "/tmp/fresh-neuron-screen.png",

            "screenshot_format":
                "png",

            "screenshot_bytes":
                999,
        }


def test_visual_question_is_bound():
    registry = bind_local_capabilities(
        build_default_registry()
    )

    cap = registry.get(
        "screen.visual_question"
    )

    assert cap is not None
    assert cap.provider == "neuron.vision"
    assert cap.executor is not None


def test_visual_question_requires_question():
    registry = bind_local_capabilities(
        build_default_registry()
    )

    cap = registry.get(
        "screen.visual_question"
    )

    result = cap.executor({})

    assert result["ok"] is False
    assert result["status"] == "invalid_question"


def test_visual_question_uses_fresh_capture(
    monkeypatch,
):
    observed = {
        "called": 0,
    }

    asked = {}

    def fake_observe(self):
        observed["called"] += 1
        return FakeScreenResult()

    def fake_ask(
        self,
        image_path,
        question,
    ):
        asked["image_path"] = image_path
        asked["question"] = question

        return VisionQuestionResult(
            ok=True,
            question=question,
            answer="A terminal is visible.",
            screenshot_path=image_path,
            model_endpoint=(
                "http://127.0.0.1:8769"
                "/v1/chat/completions"
            ),
            status="grounded_visual_answer",
        )

    monkeypatch.setattr(
        WindowsBridge,
        "observe_screen",
        fake_observe,
    )

    monkeypatch.setattr(
        VisionClient,
        "ask_image",
        fake_ask,
    )

    registry = bind_local_capabilities(
        build_default_registry()
    )

    cap = registry.get(
        "screen.visual_question"
    )

    result = cap.executor(
        {
            "question":
                "What is visible?"
        }
    )

    assert observed["called"] == 1

    assert (
        asked["image_path"]
        == "/tmp/fresh-neuron-screen.png"
    )

    assert (
        asked["question"]
        == "What is visible?"
    )

    assert result["ok"] is True

    assert (
        result["answer"]
        == "A terminal is visible."
    )


def test_visual_question_refuses_capture_failure(
    monkeypatch,
):
    class Failure:
        def to_dict(self):
            return {
                "ok": False,
                "provider": "nifdu.screen",
                "stderr": "capture failed",
            }

    monkeypatch.setattr(
        WindowsBridge,
        "observe_screen",
        lambda self: Failure(),
    )

    called = {
        "vision": False,
    }

    def forbidden(
        self,
        image_path,
        question,
    ):
        called["vision"] = True
        raise AssertionError(
            "vision must not run without grounded capture"
        )

    monkeypatch.setattr(
        VisionClient,
        "ask_image",
        forbidden,
    )

    registry = bind_local_capabilities(
        build_default_registry()
    )

    cap = registry.get(
        "screen.visual_question"
    )

    result = cap.executor(
        {
            "question":
                "What is visible?"
        }
    )

    assert result["ok"] is False

    assert (
        result["status"]
        == "screen_observation_failed"
    )

    assert called["vision"] is False


def test_grounded_visual_answer_enters_sophyane_memory_v5(
    monkeypatch,
    tmp_path,
):
    import integration.bindings as bindings

    from perception.vision_client import (
        VisionQuestionResult,
    )

    from semantic.registry import (
        build_default_registry,
    )

    screenshot = tmp_path / "visual-v5.png"

    screenshot.write_bytes(
        b"\x89PNG\r\n\x1a\nvisual"
    )

    class Screen:
        def to_dict(self):
            return {
                "ok": True,
                "application": "Browser",
                "window_title": "Dawn",
                "screenshot_path": str(
                    screenshot
                ),
                "screenshot_bytes": (
                    screenshot.stat().st_size
                ),
                "captured_at": 500.0,
            }

    monkeypatch.setattr(
        bindings.WindowsBridge,
        "observe_screen",
        lambda self: Screen(),
    )

    monkeypatch.setattr(
        bindings.VisionClient,
        "ask_image",
        lambda self, image_path, question:
            VisionQuestionResult(
                ok=True,
                question=question,
                answer=(
                    "A rendered news page is visible."
                ),
                screenshot_path=image_path,
                status="grounded_visual_answer",
            ),
    )

    seen = {}

    class Chunk:
        id = "v5-chunk"

    class Embedder:
        description = "test/384d"

    class Store:
        embedder = Embedder()

    class Memory:
        def __init__(self):
            self.store = Store()

        def latest_visual_chunks(
            self,
            limit=1,
        ):
            return []

        def remember(
            self,
            observation,
        ):
            seen["value"] = observation
            return Chunk()

    monkeypatch.setattr(
        bindings,
        "SophyaneVisualMemory",
        Memory,
    )

    registry = (
        bindings.bind_local_capabilities(
            build_default_registry()
        )
    )

    result = registry.get(
        "screen.visual_question"
    ).executor(
        {
            "question":
                "What do you see?"
        }
    )

    assert result["ok"] is True

    assert (
        result[
            "sophyane_visual_memory"
        ]["chunk_id"]
        == "v5-chunk"
    )

    assert (
        seen["value"].description
        == "A rendered news page is visible."
    )
