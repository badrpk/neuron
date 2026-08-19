import hashlib

import perception.perceptual_context as module


class ResultWithDigest:
    digest = "abc123"


def test_module_function_api(
    monkeypatch,
):
    monkeypatch.setattr(
        module.screen_change,
        "fingerprint_screen",
        lambda path: ResultWithDigest(),
        raising=False,
    )

    builder = (
        module.PerceptualContextBuilder()
    )

    result = builder.pixel_digest(
        "/tmp/anything.png"
    )

    assert result == "abc123"


def test_no_from_png_assumption(
    monkeypatch,
):
    class FakeFingerprint:
        def __init__(
            self,
            path,
        ):
            self.samples = (
                1,
                2,
                3,
            )

    for name in (
        "fingerprint_screen",
        "fingerprint_png",
        "build_fingerprint",
        "screen_fingerprint",
        "fingerprint",
    ):
        monkeypatch.delattr(
            module.screen_change,
            name,
            raising=False,
        )

    monkeypatch.setattr(
        module.screen_change,
        "ScreenFingerprint",
        FakeFingerprint,
        raising=False,
    )

    result = (
        module.PerceptualContextBuilder
        .pixel_digest(
            "/tmp/anything.png"
        )
    )

    expected = hashlib.sha256(
        repr(
            (1, 2, 3)
        ).encode(
            "utf-8"
        )
    ).hexdigest()[:20]

    assert result == expected
