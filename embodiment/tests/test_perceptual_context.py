import perception.perceptual_context as module

from perception.perceptual_context import (
    PerceptualContextBuilder,
)


class FakeFingerprint:
    digest = "abcdef1234567890"

    @staticmethod
    def from_png(path):
        return FakeFingerprint()


def test_filename_does_not_affect_context(
    monkeypatch,
):
    monkeypatch.setattr(
        module,
        "ScreenFingerprint",
        FakeFingerprint,
    )

    builder = (
        PerceptualContextBuilder()
    )

    a = builder.build(
        screenshot_path="/tmp/a.png",
        semantic_gist=(
            "Dawn homepage with navigation "
            "and top news stories"
        ),
    )

    b = builder.build(
        screenshot_path="/tmp/completely-new-name.png",
        semantic_gist=(
            "Dawn homepage with navigation "
            "and top news stories"
        ),
    )

    assert (
        a.context_key
        == b.context_key
    )


def test_semantic_change_changes_context(
    monkeypatch,
):
    monkeypatch.setattr(
        module,
        "ScreenFingerprint",
        FakeFingerprint,
    )

    builder = (
        PerceptualContextBuilder()
    )

    a = builder.build(
        screenshot_path="/tmp/a.png",
        semantic_gist="Dawn homepage",
    )

    b = builder.build(
        screenshot_path="/tmp/a.png",
        semantic_gist="GitHub repository page",
    )

    assert (
        a.context_key
        != b.context_key
    )


def test_normalization_stable():
    builder = (
        PerceptualContextBuilder()
    )

    assert (
        builder.normalize_semantic(
            "  DAWN   Homepage!! "
        )
        ==
        "dawn homepage"
    )
