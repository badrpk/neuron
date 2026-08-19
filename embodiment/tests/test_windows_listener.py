from audio.windows_listener import (
    ListenResult,
)


def test_listen_result_roundtrip():
    value = ListenResult(
        ok=True,
        text="open dawn",
        confidence=0.8,
    )

    data = value.to_dict()

    assert data["ok"] is True
    assert data["text"] == "open dawn"
    assert data["confidence"] == 0.8


def test_empty_failed_result():
    value = ListenResult(
        ok=False,
        error="timeout",
    )

    assert value.ok is False
    assert value.error == "timeout"
