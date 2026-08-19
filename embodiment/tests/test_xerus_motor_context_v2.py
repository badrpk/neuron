import integration.xerus_motor_learning as module

from integration.xerus_motor_learning import (
    XerusMotorLearning,
)


class FakeContext:
    context_key = "same-perceptual-context"


class FakeBuilder:
    def build(
        self,
        *,
        screenshot_path,
        semantic_gist,
    ):
        return FakeContext()


def test_different_filenames_can_reinforce_same_context(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(
        module,
        "PerceptualContextBuilder",
        FakeBuilder,
    )

    memory = XerusMotorLearning(
        root=str(tmp_path)
    )

    first = memory.record(
        screenshot_path="/tmp/first.png",
        target_instruction="click Latest",
        semantic_gist=(
            "Latest navigation tab on Dawn"
        ),
        x=500,
        y=200,
        success=True,
    )

    second = memory.record(
        screenshot_path="/tmp/another-file.png",
        target_instruction="click Latest",
        semantic_gist=(
            "Latest navigation tab on Dawn"
        ),
        x=500,
        y=200,
        success=True,
    )

    assert (
        second.successes
        == 2
    )

    assert (
        second.weight
        > first.weight
    )


def test_context_still_persists(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(
        module,
        "PerceptualContextBuilder",
        FakeBuilder,
    )

    first = XerusMotorLearning(
        root=str(tmp_path)
    )

    first.record(
        screenshot_path="/tmp/a.png",
        target_instruction="click Latest",
        semantic_gist="Dawn Latest tab",
        x=500,
        y=200,
        success=True,
    )

    restarted = XerusMotorLearning(
        root=str(tmp_path)
    )

    rows = restarted.strongest(
        target_instruction="click Latest"
    )

    assert rows
    assert rows[0].successes == 1
