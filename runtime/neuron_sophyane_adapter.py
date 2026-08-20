from __future__ import annotations

from pathlib import Path
import os
import subprocess
from typing import Any


def execute_with_sophyane(
    *,
    instruction: str,
    workspace: Path,
    sophyane_executable: str,
    session_environment: dict[str, str],
) -> dict[str, Any]:
    """
    Thin Neuron -> Sophyane boundary.

    IMPORTANT:
      Neuron does NOT decompose coding work here.
      Neuron does NOT decide tools.
      Neuron does NOT implement repair loops.
      Neuron does NOT implement repository logic.

    The original user objective is delegated to Sophyane.
    Sophyane remains authoritative for software execution.
    """

    instruction = str(
        instruction or ""
    ).strip()

    if not instruction:
        return {
            "ok": False,
            "error": "instruction required",
        }

    env = os.environ.copy()

    env.update(
        session_environment
    )

    env["NEURON_ACTIVE"] = "1"
    env["NEURON_DELEGATED_TO_SOPHYANE"] = "1"

    try:
        completed = subprocess.run(
            [
                sophyane_executable,
                instruction,
            ],
            cwd=str(workspace),
            env=env,
            capture_output=True,
            text=True,
            timeout=1800,
            check=False,
        )

    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "error": (
                "Sophyane execution exceeded "
                "the Neuron delegation budget"
            ),
            "stdout": (
                exc.stdout or ""
            ),
            "stderr": (
                exc.stderr or ""
            ),
        }

    except Exception as exc:
        return {
            "ok": False,
            "error": (
                f"{type(exc).__name__}: {exc}"
            ),
        }

    stdout = (
        completed.stdout
        or ""
    )

    stderr = (
        completed.stderr
        or ""
    )

    # Bound returned evidence only.
    # Sophyane execution itself is not truncated.
    combined = (
        stdout
        + (
            "\n" if stdout and stderr else ""
        )
        + stderr
    )

    if len(combined) > 40000:
        combined = (
            combined[:28000]
            + "\n\n"
            "[NEURON: SOPHYANE OUTPUT BOUNDED]\n\n"
            + combined[-12000:]
        )

    failure_markers = (
        "goal_met=false",
        "stopped_reason=provider_unavailable",
        "all configured llm providers failed",
        "sophyane could not reach any working llm provider",
    )

    semantic_failure = any(
        marker in combined.casefold()
        for marker in failure_markers
    )

    ok = (
        completed.returncode == 0
        and not semantic_failure
    )

    return {
        "ok": ok,
        "exit_code":
            completed.returncode,
        "output":
            combined,
        "delegated_to":
            "sophyane",
    }
