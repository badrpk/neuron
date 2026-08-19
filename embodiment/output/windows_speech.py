from __future__ import annotations

import subprocess
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class SpeechResult:
    ok: bool
    text: str
    provider: str = "windows.speech"
    engine: str = ""
    error: str = ""

    def to_dict(self):
        return asdict(self)


class WindowsSpeech:
    """
    Speak Unicode text through the Windows host.

    Text is transported over stdin instead of environment
    variables so WSL -> Windows process boundaries do not
    lose the payload.
    """

    def speak(
        self,
        text: str,
    ) -> SpeechResult:
        text = str(
            text or ""
        ).strip()

        if not text:
            return SpeechResult(
                ok=False,
                text="",
                error="speech text is empty",
            )

        powershell = r'''
$ErrorActionPreference = "Stop"

$text = [Console]::In.ReadToEnd()

if ([string]::IsNullOrWhiteSpace($text)) {
    Write-Error "No speech text received on stdin"
    exit 11
}

try {
    Add-Type -AssemblyName System.Speech

    $voice = New-Object `
        System.Speech.Synthesis.SpeechSynthesizer

    $voice.SetOutputToDefaultAudioDevice()

    $voice.Speak($text)

    $voice.Dispose()

    Write-Output "ENGINE=System.Speech"
    exit 0
}
catch {
    try {
        $voice = New-Object -ComObject SAPI.SpVoice

        [void]$voice.Speak($text)

        Write-Output "ENGINE=SAPI.SpVoice"
        exit 0
    }
    catch {
        Write-Error $_
        exit 12
    }
}
'''

        try:
            completed = subprocess.run(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    powershell,
                ],
                input=text,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )

        except Exception as exc:
            return SpeechResult(
                ok=False,
                text=text,
                error=str(exc),
            )

        stdout = (
            completed.stdout
            or ""
        ).strip()

        stderr = (
            completed.stderr
            or ""
        ).strip()

        engine = ""

        for line in stdout.splitlines():
            if line.startswith(
                "ENGINE="
            ):
                engine = line.split(
                    "=",
                    1,
                )[1].strip()

        if completed.returncode != 0:
            return SpeechResult(
                ok=False,
                text=text,
                engine=engine,
                error=(
                    stderr
                    or stdout
                    or (
                        "Windows speech failed "
                        f"with rc={completed.returncode}"
                    )
                ),
            )

        return SpeechResult(
            ok=True,
            text=text,
            engine=engine,
        )
