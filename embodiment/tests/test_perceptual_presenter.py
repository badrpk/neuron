from __future__ import annotations

from output.perceptual_presenter import (
    PerceptualPresenter,
)

from output.windows_speech import (
    SpeechResult,
)


def test_presenter_rejects_empty_text(
    tmp_path,
):
    presenter = (
        PerceptualPresenter(
            output_root=str(
                tmp_path
            )
        )
    )

    result = presenter.present(
        "",
        open_visible=False,
        speak=False,
    )

    assert result.ok is False


def test_presenter_writes_exact_text(
    tmp_path,
):
    presenter = (
        PerceptualPresenter(
            output_root=str(
                tmp_path
            )
        )
    )

    text = (
        "Neuron sees a rendered webpage."
    )

    result = presenter.present(
        text,
        filename="test.txt",
        open_visible=False,
        speak=False,
    )

    assert result.ok is True
    assert result.text == text

    saved = (
        tmp_path
        / "test.txt"
    ).read_text(
        encoding="utf-8"
    )

    assert saved.strip() == text


def test_presenter_uses_exact_same_text_for_speech(
    monkeypatch,
    tmp_path,
):
    presenter = (
        PerceptualPresenter(
            output_root=str(
                tmp_path
            )
        )
    )

    captured = {}

    def fake_speak(text):
        captured[
            "text"
        ] = text

        return SpeechResult(
            ok=True,
            text=text,
            engine="test",
        )

    monkeypatch.setattr(
        presenter.speech,
        "speak",
        fake_speak,
    )

    text = (
        "This exact percept must "
        "be written and spoken."
    )

    result = presenter.present(
        text,
        filename="same.txt",
        open_visible=False,
        speak=True,
    )

    assert result.ok is True
    assert result.spoken is True

    assert (
        captured["text"]
        == text
    )

    assert (
        (tmp_path / "same.txt")
        .read_text(
            encoding="utf-8"
        )
        .strip()
        == text
    )


def test_speech_failure_makes_presentation_fail(
    monkeypatch,
    tmp_path,
):
    presenter = (
        PerceptualPresenter(
            output_root=str(
                tmp_path
            )
        )
    )

    monkeypatch.setattr(
        presenter.speech,
        "speak",
        lambda text:
            SpeechResult(
                ok=False,
                text=text,
                error="speaker failed",
            ),
    )

    result = presenter.present(
        "hello",
        open_visible=False,
        speak=True,
    )

    assert result.ok is False
    assert result.spoken is False
    assert (
        "speaker failed"
        in result.error
    )
