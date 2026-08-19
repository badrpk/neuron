from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class MotorResult:
    ok: bool
    capability: str
    action: str
    error: str = ""

    def to_dict(self):
        return asdict(self)


class WindowsMotor:
    """
    Small bounded motor surface for the Windows host.

    No arbitrary PowerShell is accepted from callers.
    """

    def _run(
        self,
        script: str,
        *,
        capability: str,
        action: str,
    ) -> MotorResult:
        try:
            completed = subprocess.run(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    script,
                ],
                capture_output=True,
                text=True,
                check=False,
            )
        except Exception as exc:
            return MotorResult(
                ok=False,
                capability=capability,
                action=action,
                error=str(exc),
            )

        if completed.returncode != 0:
            return MotorResult(
                ok=False,
                capability=capability,
                action=action,
                error=(
                    completed.stderr.strip()
                    or completed.stdout.strip()
                    or (
                        "motor command failed "
                        f"rc={completed.returncode}"
                    )
                ),
            )

        return MotorResult(
            ok=True,
            capability=capability,
            action=action,
        )

    def scroll(
        self,
        *,
        direction: str,
        amount: int = 5,
    ) -> MotorResult:
        direction = str(direction).lower().strip()

        if direction not in {
            "up",
            "down",
        }:
            return MotorResult(
                ok=False,
                capability="desktop.scroll",
                action=direction,
                error="invalid scroll direction",
            )

        amount = max(
            1,
            min(
                int(amount),
                20,
            ),
        )

        key = (
            "{PGDN}"
            if direction == "down"
            else "{PGUP}"
        )

        script = f'''
$ws = New-Object -ComObject WScript.Shell

for ($i = 0; $i -lt {amount}; $i++) {{
    $ws.SendKeys("{key}")
    Start-Sleep -Milliseconds 120
}}
'''

        return self._run(
            script,
            capability="desktop.scroll",
            action=f"{direction}:{amount}",
        )

    def back(self) -> MotorResult:
        script = r'''
$ws = New-Object -ComObject WScript.Shell
$ws.SendKeys("%{LEFT}")
'''

        return self._run(
            script,
            capability="desktop.back",
            action="back",
        )

    def focus_browser(
        self,
    ) -> MotorResult:
        script = r'''
$ws = New-Object -ComObject WScript.Shell

$proc = Get-Process chrome `
    -ErrorAction SilentlyContinue |
    Where-Object {
        $_.MainWindowTitle
    } |
    Select-Object -First 1

if ($null -eq $proc) {
    exit 4
}

[void]$ws.AppActivate(
    $proc.Id
)
'''

        return self._run(
            script,
            capability="desktop.focus",
            action="browser",
        )

    def click(
        self,
        *,
        x: int,
        y: int,
    ) -> MotorResult:
        x = int(x)
        y = int(y)

        if (
            x < 0
            or y < 0
            or x > 10000
            or y > 10000
        ):
            return MotorResult(
                ok=False,
                capability="desktop.click",
                action=f"{x},{y}",
                error="click coordinate out of bounds",
            )

        script = f'''
Add-Type @"
using System;
using System.Runtime.InteropServices;

public static class NeuronMouse {{
    [DllImport("user32.dll")]
    public static extern bool SetCursorPos(
        int X,
        int Y
    );

    [DllImport(
        "user32.dll",
        CallingConvention =
            CallingConvention.StdCall
    )]
    public static extern void mouse_event(
        uint dwFlags,
        uint dx,
        uint dy,
        uint dwData,
        UIntPtr dwExtraInfo
    );
}}
"@

[NeuronMouse]::SetCursorPos(
    {x},
    {y}
) | Out-Null

Start-Sleep -Milliseconds 100

[NeuronMouse]::mouse_event(
    0x0002,
    0,
    0,
    0,
    [UIntPtr]::Zero
)

[NeuronMouse]::mouse_event(
    0x0004,
    0,
    0,
    0,
    [UIntPtr]::Zero
)
'''

        return self._run(
            script,
            capability="desktop.click",
            action=f"{x},{y}",
        )
