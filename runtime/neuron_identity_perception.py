from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import re
import subprocess
import sys
import time
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EMB = ROOT / "embodiment"

for value in (
    str(ROOT),
    str(EMB),
):
    if value not in sys.path:
        sys.path.insert(0, value)


@dataclass(frozen=True)
class NativeIdentityResult:
    handled: bool
    ok: bool
    capability: str = ""
    answer: str = ""
    error: str = ""
    raw: dict[str, Any] | None = None


def _normalise(text: str) -> str:
    return " ".join(
        str(text or "")
        .strip()
        .casefold()
        .split()
    )


def classify_identity_perception(
    text: str,
) -> str:

    lower = _normalise(text)

    if not lower:
        return ""

    # --------------------------------------------------------
    # NEURON IDENTITY
    # --------------------------------------------------------

    identity_patterns = (
        r"\bneuron is this harness\b",
        r"\bis neuron this harness\b",
        r"\bare you neuron\b",
        r"\bwhat is neuron\b",
        r"\bwhat are you\b",
        r"\bwho are you\b",
    )

    if any(
        re.search(pattern, lower)
        for pattern in identity_patterns
    ):
        return "identity.describe"

    if (
        "neuron" in lower
        and "camera" in lower
        and any(
            marker in lower
            for marker in (
                "face",
                "expression",
                "see",
                "observe",
            )
        )
    ):
        return "identity.capabilities"

    # --------------------------------------------------------
    # CURRENT FACIAL EXPRESSION
    # --------------------------------------------------------

    face_expression_patterns = (
        r"\bam i smiling\b",
        r"\bam i smiling now\b",
        r"\bdo i look happy\b",
        r"\bwhat is my facial expression\b",
        r"\bwhat's my facial expression\b",
        r"\bwhat expression am i making\b",
        r"\bcan you see my face\b",
        r"\blook at my face\b",
        r"\bobserve my face\b",
    )

    if any(
        re.search(pattern, lower)
        for pattern in face_expression_patterns
    ):
        return "camera.expression"

    return ""


def _identity() -> NativeIdentityResult:
    return NativeIdentityResult(
        handled=True,
        ok=True,
        capability="identity.describe",
        answer=(
            "Yes. Neuron is this local agent harness and "
            "runtime. The selected Gemini, Qwen, or other "
            "LLM is only a replaceable reasoning backend. "
            "Neuron owns the security boundary, perception, "
            "desktop capabilities, session state, routing, "
            "and agent identity; Sophyane is an execution "
            "and engineering harness underneath Neuron."
        ),
    )


def _capabilities() -> NativeIdentityResult:
    return NativeIdentityResult(
        handled=True,
        ok=True,
        capability="identity.capabilities",
        answer=(
            "Neuron is the harness. Its perception layer can "
            "use grounded screen vision and microphone input. "
            "For a current facial-expression question, this "
            "runtime will attempt to open the Windows Camera "
            "preview, capture the real rendered camera pixels, "
            "and analyze them through Neuron's local vision "
            "service. If the camera or vision service is not "
            "available, Neuron will report that blocker rather "
            "than asking the text LLM to guess."
        ),
    )


def _powershell(
    command: str,
    *,
    timeout: float = 15.0,
) -> subprocess.CompletedProcess[str]:

    return subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            command,
        ],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def _open_camera() -> tuple[bool, str]:
    try:
        result = _powershell(
            r"""
$ErrorActionPreference = 'Stop'
Start-Process 'microsoft.windows.camera:'
""",
            timeout=10.0,
        )
    except Exception as exc:
        return False, str(exc)

    if result.returncode != 0:
        return (
            False,
            result.stderr.strip()
            or result.stdout.strip()
            or (
                "Windows Camera could not "
                f"be opened (rc={result.returncode})"
            ),
        )

    return True, ""


def _close_camera() -> None:
    # Only close via Alt+F4 when Camera appears foreground.
    # Never kill arbitrary camera-associated processes.
    try:
        _powershell(
            r"""
$ErrorActionPreference = 'SilentlyContinue'

Add-Type @'
using System;
using System.Runtime.InteropServices;
using System.Text;

public static class NeuronForegroundCamera {
    [DllImport("user32.dll")]
    public static extern IntPtr GetForegroundWindow();

    [DllImport(
        "user32.dll",
        CharSet = CharSet.Unicode
    )]
    public static extern int GetWindowText(
        IntPtr hWnd,
        StringBuilder text,
        int count
    );
}
'@

$h = [NeuronForegroundCamera]::GetForegroundWindow()
$sb = New-Object System.Text.StringBuilder 2048
[void][NeuronForegroundCamera]::GetWindowText(
    $h,
    $sb,
    $sb.Capacity
)

$title = $sb.ToString()

if ($title -match '(?i)camera') {
    $ws = New-Object -ComObject WScript.Shell
    $ws.SendKeys('%{F4}')
}
""",
            timeout=5.0,
        )
    except Exception:
        pass


def _camera_expression(
    question: str,
) -> NativeIdentityResult:

    try:
        from desktop.windows_bridge import (
            WindowsBridge,
        )

        from perception.vision_client import (
            VisionClient,
        )

    except Exception as exc:
        return NativeIdentityResult(
            handled=True,
            ok=False,
            capability="camera.expression",
            error=(
                "Neuron camera/vision dependencies "
                f"could not load: {exc}"
            ),
        )

    opened, error = _open_camera()

    if not opened:
        return NativeIdentityResult(
            handled=True,
            ok=False,
            capability="camera.expression",
            error=(
                "Windows Camera is unavailable: "
                + error
            ),
        )

    screenshot_path = ""

    try:
        # Camera application startup / permission / preview.
        time.sleep(3.0)

        observation = (
            WindowsBridge()
            .observe_screen()
        )

        if not observation.ok:
            return NativeIdentityResult(
                handled=True,
                ok=False,
                capability="camera.expression",
                error=(
                    observation.stderr
                    or (
                        "Neuron could not capture "
                        "the Camera preview."
                    )
                ),
                raw=observation.to_dict(),
            )

        screenshot_path = str(
            observation.screenshot_path
            or ""
        )

        active = (
            f"{observation.application} "
            f"{observation.window_title}"
        ).casefold()

        # Fail closed: don't analyze an unrelated desktop
        # screenshot as though it came from the camera.
        if "camera" not in active:
            return NativeIdentityResult(
                handled=True,
                ok=False,
                capability="camera.expression",
                error=(
                    "Windows Camera did not become "
                    "the grounded foreground window. "
                    "No facial-expression claim was made."
                ),
                raw=observation.to_dict(),
            )

        vision_question = (
            "Inspect ONLY the live camera-preview pixels "
            "visible in this screenshot. Determine whether "
            "a clearly visible person's facial expression "
            "currently shows a smile. "
            "Do not identify the person. "
            "Do not infer mood, personality, or emotion "
            "beyond the visible facial expression. "
            "If no face is clearly visible, say "
            "FACE_NOT_VISIBLE. If the expression cannot be "
            "determined reliably, say UNCERTAIN. "
            "Otherwise begin with SMILING or NOT_SMILING "
            "and give one short visual reason."
        )

        result = VisionClient(
            host="127.0.0.1",
            port=8769,
        ).ask_image(
            screenshot_path,
            vision_question,
        )

        if not result.ok:
            return NativeIdentityResult(
                handled=True,
                ok=False,
                capability="camera.expression",
                error=(
                    "Camera pixels were captured, but "
                    "Neuron's grounded vision service "
                    "could not analyze them: "
                    + (
                        result.error
                        or result.status
                        or "vision unavailable"
                    )
                ),
                raw=result.to_dict(),
            )

        answer = str(
            result.answer
            or ""
        ).strip()

        if not answer:
            return NativeIdentityResult(
                handled=True,
                ok=False,
                capability="camera.expression",
                error=(
                    "Vision returned no grounded "
                    "facial-expression result."
                ),
            )

        normalized = answer.casefold()

        if "face_not_visible" in normalized:
            user_answer = (
                "I opened the camera, but I cannot "
                "clearly see a face in the grounded "
                "camera preview."
            )

        elif "uncertain" in normalized:
            user_answer = (
                "I can see the camera preview, but "
                "I cannot determine reliably whether "
                "you are smiling from the current frame."
            )

        elif (
            "not_smiling" in normalized
            or "not smiling" in normalized
        ):
            user_answer = (
                "From the current grounded camera "
                "preview, you do not appear to be "
                "smiling. "
                + answer
            )

        elif "smiling" in normalized:
            user_answer = (
                "From the current grounded camera "
                "preview, you appear to be smiling. "
                + answer
            )

        else:
            # Keep the raw grounded result rather than
            # inventing a stronger interpretation.
            user_answer = (
                "From the current camera preview, "
                "Neuron's vision result is: "
                + answer
            )

        return NativeIdentityResult(
            handled=True,
            ok=True,
            capability="camera.expression",
            answer=user_answer,
            raw=result.to_dict(),
        )

    finally:
        _close_camera()

        # Facial imagery for this one-shot observation
        # is not retained by this front door.
        if screenshot_path:
            try:
                Path(
                    screenshot_path
                ).unlink()
            except OSError:
                pass


def handle_identity_perception(
    text: str,
) -> NativeIdentityResult:

    capability = (
        classify_identity_perception(
            text
        )
    )

    if not capability:
        return NativeIdentityResult(
            handled=False,
            ok=False,
        )

    if capability == "identity.describe":
        return _identity()

    if capability == "identity.capabilities":
        return _capabilities()

    if capability == "camera.expression":
        return _camera_expression(
            text
        )

    return NativeIdentityResult(
        handled=False,
        ok=False,
    )
