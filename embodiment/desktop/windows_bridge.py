from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence


@dataclass
class ActionResult:
    ok: bool
    capability: str
    target: str
    returncode: int
    stdout: str = ""
    stderr: str = ""

    def to_dict(self):
        return asdict(self)




@dataclass
class ScreenObservationResult:
    ok: bool
    capability: str = "screen.observe"
    provider: str = "nifdu.screen"
    application: str = ""
    window_title: str = ""
    process_id: int | None = None
    window_handle: int | None = None
    bounds: dict[str, int] | None = None
    screen_bounds: dict[str, int] | None = None
    screenshot_path: str = ""
    screenshot_format: str = "png"
    screenshot_bytes: int = 0
    returncode: int = 0
    stderr: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class WindowsBridge:
    SAFE_APPS = {
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "calc": "calc.exe",
        "explorer": "explorer.exe",
        "terminal": "wt.exe",
        "chrome":
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    }

    def _powershell(
        self,
        command: str,
    ) -> subprocess.CompletedProcess:

        exe = shutil.which(
            "powershell.exe"
        )

        if not exe:
            return subprocess.CompletedProcess(
                args=[],
                returncode=127,
                stdout="",
                stderr="powershell.exe unavailable",
            )

        return subprocess.run(
            [
                exe,
                "-NoProfile",
                "-Command",
                command,
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )

    def observe_screen(
        self,
    ) -> ScreenObservationResult:
        """
        Observe the real Windows desktop.

        The PowerShell side obtains foreground-window metadata and
        captures the full virtual desktop. PNG bytes cross the
        Windows/WSL boundary as base64 and are immediately decoded
        into a private local temporary file.

        No synthetic result is returned on capture failure.
        """

        command = r"""
$ErrorActionPreference = 'Stop'

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

if (-not ('NeuronScreen.NativeMethods' -as [type])) {
    Add-Type @'
using System;
using System.Runtime.InteropServices;
using System.Text;

namespace NeuronScreen {
    public static class NativeMethods {
        [StructLayout(LayoutKind.Sequential)]
        public struct RECT {
            public int Left;
            public int Top;
            public int Right;
            public int Bottom;
        }

        [DllImport("user32.dll")]
        public static extern IntPtr GetForegroundWindow();

        [DllImport("user32.dll", CharSet = CharSet.Unicode)]
        public static extern int GetWindowText(
            IntPtr hWnd,
            StringBuilder text,
            int count
        );

        [DllImport("user32.dll")]
        public static extern uint GetWindowThreadProcessId(
            IntPtr hWnd,
            out uint processId
        );

        [DllImport("user32.dll")]
        [return: MarshalAs(UnmanagedType.Bool)]
        public static extern bool GetWindowRect(
            IntPtr hWnd,
            out RECT rect
        );
    }
}
'@
}

$hwnd = [NeuronScreen.NativeMethods]::GetForegroundWindow()

$title = ''
$pidValue = 0
$application = ''
$left = 0
$top = 0
$right = 0
$bottom = 0

if ($hwnd -ne [IntPtr]::Zero) {
    $sb = New-Object System.Text.StringBuilder 4096
    [void][NeuronScreen.NativeMethods]::GetWindowText(
        $hwnd,
        $sb,
        $sb.Capacity
    )
    $title = $sb.ToString()

    [uint32]$foregroundPid = 0
    [void][NeuronScreen.NativeMethods]::GetWindowThreadProcessId(
        $hwnd,
        [ref]$foregroundPid
    )
    $pidValue = [int]$foregroundPid

    if ($pidValue -gt 0) {
        try {
            $application = (
                Get-Process -Id $pidValue -ErrorAction Stop
            ).ProcessName
        }
        catch {
            $application = ''
        }
    }

    $rect = New-Object NeuronScreen.NativeMethods+RECT

    if (
        [NeuronScreen.NativeMethods]::GetWindowRect(
            $hwnd,
            [ref]$rect
        )
    ) {
        $left = $rect.Left
        $top = $rect.Top
        $right = $rect.Right
        $bottom = $rect.Bottom
    }
}

$virtual = [System.Windows.Forms.SystemInformation]::VirtualScreen

if ($virtual.Width -le 0 -or $virtual.Height -le 0) {
    throw 'Windows virtual screen has invalid dimensions'
}

$bitmap = New-Object System.Drawing.Bitmap(
    $virtual.Width,
    $virtual.Height,
    [System.Drawing.Imaging.PixelFormat]::Format32bppArgb
)

$graphics = [System.Drawing.Graphics]::FromImage($bitmap)

try {
    $graphics.CopyFromScreen(
        $virtual.Left,
        $virtual.Top,
        0,
        0,
        $bitmap.Size,
        [System.Drawing.CopyPixelOperation]::SourceCopy
    )

    $stream = New-Object System.IO.MemoryStream

    try {
        $bitmap.Save(
            $stream,
            [System.Drawing.Imaging.ImageFormat]::Png
        )

        $pngBase64 = [Convert]::ToBase64String(
            $stream.ToArray()
        )
    }
    finally {
        $stream.Dispose()
    }
}
finally {
    $graphics.Dispose()
    $bitmap.Dispose()
}

$result = [ordered]@{
    ok = $true
    application = $application
    window_title = $title
    process_id = $pidValue
    window_handle = $hwnd.ToInt64()

    bounds = [ordered]@{
        left = $left
        top = $top
        right = $right
        bottom = $bottom
        width = [Math]::Max(0, $right - $left)
        height = [Math]::Max(0, $bottom - $top)
    }

    screen_bounds = [ordered]@{
        left = $virtual.Left
        top = $virtual.Top
        width = $virtual.Width
        height = $virtual.Height
    }

    screenshot_format = 'png'
    screenshot_base64 = $pngBase64
}

$result | ConvertTo-Json -Depth 8 -Compress
"""

        try:
            result = self._powershell(
                command
            )
        except subprocess.TimeoutExpired as exc:
            return ScreenObservationResult(
                ok=False,
                returncode=124,
                stderr=(
                    "screen observation timed out: "
                    + str(exc)
                ),
            )
        except Exception as exc:
            return ScreenObservationResult(
                ok=False,
                returncode=1,
                stderr=(
                    "screen observation failed: "
                    + str(exc)
                ),
            )

        if result.returncode != 0:
            return ScreenObservationResult(
                ok=False,
                returncode=result.returncode,
                stderr=(
                    result.stderr.strip()
                    or "PowerShell screen capture failed"
                ),
            )

        raw = result.stdout.strip()

        if not raw:
            return ScreenObservationResult(
                ok=False,
                returncode=1,
                stderr="PowerShell returned no screen observation",
            )

        try:
            payload = json.loads(raw)
        except Exception as exc:
            return ScreenObservationResult(
                ok=False,
                returncode=1,
                stderr=(
                    "invalid screen observation JSON: "
                    + str(exc)
                ),
            )

        encoded = str(
            payload.pop(
                "screenshot_base64",
                "",
            )
            or ""
        )

        if not encoded:
            return ScreenObservationResult(
                ok=False,
                returncode=1,
                stderr="screen capture contained no PNG payload",
            )

        try:
            png = base64.b64decode(
                encoded,
                validate=True,
            )
        except Exception as exc:
            return ScreenObservationResult(
                ok=False,
                returncode=1,
                stderr=(
                    "invalid screenshot payload: "
                    + str(exc)
                ),
            )

        if not png.startswith(
            b"\x89PNG\r\n\x1a\n"
        ):
            return ScreenObservationResult(
                ok=False,
                returncode=1,
                stderr="screen capture did not produce a PNG",
            )

        try:
            configured_dir = os.environ.get(
                "NEURON_SCREENSHOT_DIR",
                "/mnt/d/NeuronData/screenshots",
            )

            screen_dir = Path(
                configured_dir
            ).expanduser()

            try:
                screen_dir.mkdir(
                    parents=True,
                    exist_ok=True,
                )
            except Exception:
                #
                # Fail safely to Linux temporary storage if
                # D: is unavailable rather than losing capture.
                #
                screen_dir = Path(
                    tempfile.gettempdir()
                )

            handle = tempfile.NamedTemporaryFile(
                prefix="neuron-screen-",
                suffix=".png",
                dir=str(screen_dir),
                delete=False,
            )

            with handle:
                handle.write(png)

            screenshot_path = str(
                Path(handle.name).resolve()
            )
        except Exception as exc:
            return ScreenObservationResult(
                ok=False,
                returncode=1,
                stderr=(
                    "failed to persist screenshot: "
                    + str(exc)
                ),
            )

        def as_int(
            value,
            default=0,
        ):
            try:
                return int(value)
            except (
                TypeError,
                ValueError,
            ):
                return default

        bounds = payload.get(
            "bounds",
            {},
        )

        screen_bounds = payload.get(
            "screen_bounds",
            {},
        )

        return ScreenObservationResult(
            ok=True,
            application=str(
                payload.get(
                    "application",
                    "",
                )
                or ""
            ),
            window_title=str(
                payload.get(
                    "window_title",
                    "",
                )
                or ""
            ),
            process_id=(
                as_int(
                    payload.get(
                        "process_id",
                        0,
                    )
                )
                or None
            ),
            window_handle=(
                as_int(
                    payload.get(
                        "window_handle",
                        0,
                    )
                )
                or None
            ),
            bounds={
                "left":
                    as_int(bounds.get("left")),
                "top":
                    as_int(bounds.get("top")),
                "right":
                    as_int(bounds.get("right")),
                "bottom":
                    as_int(bounds.get("bottom")),
                "width":
                    as_int(bounds.get("width")),
                "height":
                    as_int(bounds.get("height")),
            },
            screen_bounds={
                "left":
                    as_int(screen_bounds.get("left")),
                "top":
                    as_int(screen_bounds.get("top")),
                "width":
                    as_int(screen_bounds.get("width")),
                "height":
                    as_int(screen_bounds.get("height")),
            },
            screenshot_path=screenshot_path,
            screenshot_format="png",
            screenshot_bytes=len(png),
            returncode=0,
            stderr="",
        )

    def launch_app(
        self,
        name: str,
    ) -> ActionResult:

        key = (
            name
            .strip()
            .lower()
        )

        target = self.SAFE_APPS.get(
            key
        )

        if not target:
            return ActionResult(
                ok=False,
                capability="desktop.launch_app",
                target=name,
                returncode=2,
                stderr=(
                    "application is not in "
                    "the current safe allowlist"
                ),
            )

        escaped = target.replace(
            "'",
            "''",
        )

        result = self._powershell(
            "$p = Start-Process "
            f"-FilePath '{escaped}' "
            "-PassThru; "
            "Write-Output "
            "('PID=' + $p.Id)"
        )

        return ActionResult(
            ok=result.returncode == 0,
            capability="desktop.launch_app",
            target=name,
            returncode=result.returncode,
            stdout=result.stdout.strip(),
            stderr=result.stderr.strip(),
        )

    def open_url(
        self,
        url: str,
    ) -> ActionResult:

        url = url.strip()

        if not (
            url.startswith("http://")
            or
            url.startswith("https://")
        ):
            return ActionResult(
                ok=False,
                capability="desktop.open_url",
                target=url,
                returncode=2,
                stderr=(
                    "only http/https URLs "
                    "are allowed"
                ),
            )

        escaped = url.replace(
            "'",
            "''",
        )

        result = self._powershell(
            "Start-Process "
            f"'{escaped}'"
        )

        return ActionResult(
            ok=result.returncode == 0,
            capability="desktop.open_url",
            target=url,
            returncode=result.returncode,
            stdout=result.stdout.strip(),
            stderr=result.stderr.strip(),
        )


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser()

    sub = parser.add_subparsers(
        dest="command",
        required=True,
    )

    p_app = sub.add_parser(
        "launch-app"
    )

    p_app.add_argument(
        "name"
    )

    p_url = sub.add_parser(
        "open-url"
    )

    p_url.add_argument(
        "url"
    )

    args = parser.parse_args(
        argv
    )

    bridge = WindowsBridge()

    if args.command == "launch-app":
        result = bridge.launch_app(
            args.name
        )
    else:
        result = bridge.open_url(
            args.url
        )

    print(
        json.dumps(
            result.to_dict(),
            indent=2,
        )
    )

    return (
        0
        if result.ok
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
