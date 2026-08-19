from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ListenResult:
    ok: bool
    text: str = ""
    confidence: float = 0.0
    provider: str = "windows.speech-recognition"
    error: str = ""

    def to_dict(self):
        return asdict(self)


class WindowsListener:
    def listen_once(
        self,
        *,
        timeout_seconds: int = 15,
    ) -> ListenResult:
        timeout_seconds = max(
            1,
            int(timeout_seconds),
        )

        powershell = r'''
$ErrorActionPreference = "Stop"

try {
    Add-Type -AssemblyName System.Speech

    $recognizer = New-Object `
        System.Speech.Recognition.SpeechRecognitionEngine

    $recognizer.SetInputToDefaultAudioDevice()

    $grammar = New-Object `
        System.Speech.Recognition.DictationGrammar

    $recognizer.LoadGrammar($grammar)

    $timeout = [TimeSpan]::FromSeconds(
        [int]$env:NEURON_LISTEN_TIMEOUT
    )

    $result = $recognizer.Recognize($timeout)

    if ($null -eq $result) {
        Write-Output (
            '{"ok":false,"status":"timeout"}'
        )

        $recognizer.Dispose()
        exit 0
    }

    $obj = @{
        ok = $true
        text = $result.Text
        confidence = [double]$result.Confidence
    }

    $obj |
        ConvertTo-Json -Compress

    $recognizer.Dispose()

    exit 0
}
catch {
    $message = $_.Exception.Message

    $obj = @{
        ok = $false
        status = "error"
        error = $message
    }

    $obj |
        ConvertTo-Json -Compress

    exit 12
}
'''

        env = {
            **__import__("os").environ,
            "NEURON_LISTEN_TIMEOUT":
                str(timeout_seconds),
        }

        try:
            completed = subprocess.run(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    powershell,
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
                check=False,
            )

        except Exception as exc:
            return ListenResult(
                ok=False,
                error=str(exc),
            )

        raw = (
            completed.stdout
            or ""
        ).strip()

        if not raw:
            return ListenResult(
                ok=False,
                error=(
                    completed.stderr.strip()
                    or "no recognition response"
                ),
            )

        try:
            data = json.loads(
                raw.splitlines()[-1]
            )

        except Exception as exc:
            return ListenResult(
                ok=False,
                error=(
                    "invalid recognition output: "
                    + str(exc)
                    + " raw="
                    + raw[:500]
                ),
            )

        if data.get("ok") is not True:
            return ListenResult(
                ok=False,
                error=str(
                    data.get(
                        "error",
                        data.get(
                            "status",
                            "recognition failed",
                        ),
                    )
                ),
            )

        return ListenResult(
            ok=True,
            text=str(
                data.get(
                    "text",
                    "",
                )
                or ""
            ).strip(),
            confidence=float(
                data.get(
                    "confidence",
                    0.0,
                )
                or 0.0
            ),
        )
