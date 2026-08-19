from __future__ import annotations

import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

from output.windows_speech import (
    WindowsSpeech,
)


@dataclass(frozen=True)
class PresentationResult:
    ok: bool
    text: str
    text_path: str
    visible: bool
    spoken: bool
    speech_engine: str = ""
    error: str = ""

    def to_dict(self):
        return asdict(self)


class PerceptualPresenter:
    def __init__(
        self,
        *,
        output_root: str = (
            "/mnt/d/NeuronData/output"
        ),
    ) -> None:
        self.output_root = (
            Path(output_root)
            .expanduser()
            .resolve()
        )

        self.output_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.speech = (
            WindowsSpeech()
        )

    def _show_notepad(
        self,
        path: Path,
    ) -> tuple[bool, str]:
        try:
            win_path = (
                subprocess.check_output(
                    [
                        "wslpath",
                        "-w",
                        str(path),
                    ],
                    text=True,
                )
                .strip()
            )

            command = (
                "Start-Process "
                "notepad.exe "
                "-ArgumentList @("
                + repr(win_path)
                + ")"
            )

            result = subprocess.run(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    command,
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                return (
                    False,
                    (
                        result.stderr.strip()
                        or result.stdout.strip()
                        or (
                            "notepad launch failed "
                            f"with rc={result.returncode}"
                        )
                    ),
                )

            return True, ""

        except Exception as exc:
            return False, str(exc)

    def present(
        self,
        text: str,
        *,
        filename: str = (
            "neuron-perception.txt"
        ),
        open_visible: bool = True,
        speak: bool = True,
    ) -> PresentationResult:
        text = str(
            text or ""
        ).strip()

        if not text:
            return PresentationResult(
                ok=False,
                text="",
                text_path="",
                visible=False,
                spoken=False,
                error=(
                    "perceptual output is empty"
                ),
            )

        path = (
            self.output_root
            / filename
        )

        path.write_text(
            text + "\n",
            encoding="utf-8",
        )

        visible = (
            not open_visible
        )

        spoken = (
            not speak
        )

        speech_engine = ""
        errors = []

        if open_visible:
            visible, error = (
                self._show_notepad(
                    path
                )
            )

            if error:
                errors.append(error)

        if speak:
            result = self.speech.speak(
                text
            )

            spoken = result.ok
            speech_engine = (
                result.engine
            )

            if not result.ok:
                errors.append(
                    result.error
                )

        return PresentationResult(
            ok=(
                visible
                and spoken
            ),
            text=text,
            text_path=str(path),
            visible=visible,
            spoken=spoken,
            speech_engine=speech_engine,
            error="; ".join(
                error
                for error in errors
                if error
            ),
        )
