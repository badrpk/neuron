from runtime.closed_loop_perceptual_planner import (
    ClosedLoopPerceptualPlanner,
)


class FakeOpenResult:
    def to_dict(self):
        return {
            "ok": True,
            "capability":
                "desktop.open_url",
        }


class FakeBridge:
    def __init__(self):
        self.urls = []

    def open_url(
        self,
        url,
    ):
        self.urls.append(
            url
        )

        return FakeOpenResult()


def test_open_then_observe():
    bridge = FakeBridge()

    seen = []

    def vision(payload):
        seen.append(
            payload["question"]
        )

        return {
            "ok": True,
            "answer":
                "A rendered news page is visible.",
        }

    planner = (
        ClosedLoopPerceptualPlanner(
            bridge=bridge,
            visual_question=vision,
            max_steps=4,
        )
    )

    result = planner.run(
        (
            "Open Dawn and tell me "
            "what you see"
        )
    )

    assert result.ok is True
    assert result.completed is True

    assert (
        bridge.urls
        == [
            "https://www.dawn.com"
        ]
    )

    assert len(
        result.evidence
    ) == 2

    assert (
        result.evidence[0].capability
        == "desktop.open_url"
    )

    assert (
        result.evidence[1].capability
        == "screen.visual_question"
    )


def test_visual_only_request():
    bridge = FakeBridge()

    planner = (
        ClosedLoopPerceptualPlanner(
            bridge=bridge,
            visual_question=lambda payload: {
                "ok": True,
                "answer":
                    "A terminal is visible.",
            },
        )
    )

    result = planner.run(
        "What do you see?"
    )

    assert result.ok is True

    assert (
        result.steps_used
        == 1
    )


def test_failed_vision_stops():
    bridge = FakeBridge()

    calls = {
        "count": 0,
    }

    def vision(payload):
        calls["count"] += 1

        return {
            "ok": False,
            "answer": "",
        }

    planner = (
        ClosedLoopPerceptualPlanner(
            bridge=bridge,
            visual_question=vision,
            max_steps=10,
        )
    )

    result = planner.run(
        "What do you see?"
    )

    assert result.ok is False

    assert calls["count"] == 1


def test_step_budget_is_bounded():
    planner = (
        ClosedLoopPerceptualPlanner(
            bridge=FakeBridge(),
            visual_question=lambda payload: {
                "ok": True,
                "answer": "visible",
            },
            max_steps=2,
        )
    )

    result = planner.run(
        "Open Dawn and describe it"
    )

    assert (
        result.steps_used
        <= 2
    )
