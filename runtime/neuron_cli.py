#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys


TTY = sys.stdout.isatty()

R = "\033[0m" if TTY else ""
B = "\033[1m" if TTY else ""
D = "\033[2m" if TTY else ""
C = "\033[36m" if TTY else ""
G = "\033[32m" if TTY else ""
Y = "\033[33m" if TTY else ""
RED = "\033[31m" if TTY else ""
M = "\033[35m" if TTY else ""


def root() -> Path:
    candidates = []

    env = os.environ.get("NEURON_HOME", "").strip()
    if env:
        candidates.append(Path(env).expanduser())

    candidates += [
        Path.home() / "neuron-latest-test",
        Path.home() / ".local/share/neuron",
        Path.home() / "neuron",
    ]

    for p in candidates:
        if (
            p.is_dir()
            and (p / "runtime").is_dir()
            and (p / "CMakeLists.txt").is_file()
        ):
            return p.resolve()

    raise SystemExit(
        "Neuron installation not found. "
        "Set NEURON_HOME=/path/to/neuron."
    )


ROOT = root()
SECURITY = ROOT / "build/neuron_security_cli"

from neuron_semantic_runtime import (
    handle_semantic_turn,
    reset_semantic_session,
)

from neuron_provider_selection import (
    ProviderSelection,
    current_provider,
    select_startup_provider,
)

from neuron_identity_perception import (
    handle_identity_perception,
)

from neuron_reasoning_backend import (
    clear_session_history,
    run_neuron_chat,
    should_use_agentic_backend,
)

from neuron_native_frontdoor import (
    handle_native,
)


def command_output(args, cwd=None):
    try:
        result = subprocess.run(
            args,
            cwd=str(cwd) if cwd else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=8,
            check=False,
        )
    except Exception:
        return ""

    if result.returncode:
        return ""

    return result.stdout.strip()


def version():
    try:
        ver = (ROOT / "VERSION").read_text().strip()
    except Exception:
        ver = ""

    sha = command_output(
        ["git", "rev-parse", "--short", "HEAD"],
        ROOT,
    )

    if ver and sha:
        return f"{ver} · {sha}"

    return ver or sha or "development"


def find_sophyane():
    direct = shutil.which("sophyane")
    if direct:
        return direct

    choices = [
        Path.home() / "sophyane/.venv/bin/sophyane",
        Path.home() / ".local/bin/sophyane",
        Path.home()
        / ".local/share/sophyane/venv/bin/sophyane",
        Path.home()
        / "badrmart-benchmark/tools/"
        "sophyane-venv/bin/sophyane",
    ]

    for candidate in choices:
        if candidate.is_file() and os.access(
            candidate,
            os.X_OK,
        ):
            return str(candidate)

    return None


def safe_workspace():
    cwd = Path.cwd().resolve()
    value = str(cwd).replace("\\", "/").lower()

    unsafe = (
        value.endswith("/windows/system32")
        or value == "/mnt/c/windows"
        or value == "/mnt/c"
    )

    return ROOT if unsafe else cwd


def classify(text):
    if not SECURITY.is_file():
        return {
            "decision": "BLOCK",
            "risk": 1.0,
            "reason_codes": [
                "native_security_cli_missing"
            ],
        }

    try:
        result = subprocess.run(
            [str(SECURITY)],
            input=text,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=15,
            check=False,
        )
    except Exception as exc:
        return {
            "decision": "BLOCK",
            "risk": 1.0,
            "reason_codes": [
                f"security_failure:{type(exc).__name__}"
            ],
        }

    if result.returncode:
        return {
            "decision": "BLOCK",
            "risk": 1.0,
            "reason_codes": [
                f"security_exit_{result.returncode}"
            ],
        }

    try:
        data = json.loads(result.stdout)
        if not isinstance(data, dict):
            raise ValueError
        return data
    except Exception:
        return {
            "decision": "BLOCK",
            "risk": 1.0,
            "reason_codes": [
                "invalid_security_response"
            ],
        }


def security_line(result):
    decision = str(
        result.get("decision", "BLOCK")
    ).upper()

    style = {
        "ALLOW": G,
        "REQUIRE_REVIEW": Y,
        "ISOLATE": M,
        "BLOCK": RED,
    }.get(decision, RED)

    risk = result.get("risk", "?")

    print(
        f"{D}security{R} "
        f"{style}{decision}{R} "
        f"{D}risk={risk}{R}"
    )


def plan(text):
    sys.path.insert(0, str(ROOT))

    try:
        from runtime.sophyane_instruction_planner import (
            SophyaneInstructionPlanner,
        )

        value = SophyaneInstructionPlanner().plan(text)

        return {
            "ok": value.ok,
            "error": value.error,
            "steps": [
                {
                    "capability": step.capability,
                    "arguments": step.arguments,
                }
                for step in value.steps
            ],
        }
    except Exception as exc:
        return {
            "ok": False,
            "error": (
                f"{type(exc).__name__}: {exc}"
            ),
            "steps": [],
        }


def banner(
    workspace,
    session: ProviderSelection | None = None,
):
    agent = find_sophyane()

    if session is None:
        session = current_provider()

    print()
    print(
        f"{C}╭──────────────────────────────────────────────╮{R}"
    )
    print(
        f"{C}│{R}  {B}NEURON{R}"
        f"                                      "
        f"{C}│{R}"
    )
    print(
        f"{C}│{R}  {D}Biological Intelligence · Agent Runtime{R}"
        f"       {C}│{R}"
    )
    print(
        f"{C}╰──────────────────────────────────────────────╯{R}"
    )
    print()
    print(f" {D}version{R}    {version()}")
    print(f" {D}workspace{R}  {workspace}")

    print(
        f" {D}security{R}   "
        + (
            f"{G}native · ready{R}"
            if SECURITY.is_file()
            else f"{RED}missing{R}"
        )
    )

    print(
        f" {D}agent{R}      "
        + (
            f"{G}ready{R}"
            if agent
            else f"{Y}Sophyane not found{R}"
        )
    )

    print(
        f" {D}provider{R}   "
        f"{session.provider}"
    )

    print(
        f" {D}model{R}      "
        f"{session.model}"
    )

    print()
    print(
        f" {D}Give Neuron an instruction."
        f"  /help for commands."
        f"  Ctrl-D exits.{R}"
    )
    print()


def show_status(
    workspace,
    session: ProviderSelection | None = None,
):
    if session is None:
        session = current_provider()

    print()
    print(f"{B}Neuron runtime{R}")
    print(f"  version    {version()}")
    print(f"  root       {ROOT}")
    print(f"  workspace  {workspace}")
    print(f"  security   {SECURITY}")
    print(
        f"  agent      "
        f"{find_sophyane() or 'not found'}"
    )
    print(
        f"  provider   "
        f"{session.provider}"
    )
    print(
        f"  model      "
        f"{session.model}"
    )
    print()


def help_text():
    print()
    print(f"{B}Commands{R}")
    print("  /help             show commands")
    print("  /status           runtime status")
    print("  /pwd              current workspace")
    print("  /cd PATH          change workspace")
    print("  /plan TEXT        inspect Neuron plan")
    print("  /security TEXT    inspect security gate")
    print("  /model            switch local/cloud model")
    print("  /new              clear session conversation")
    print("  /clear            clear terminal")
    print("  /exit             exit Neuron")
    print()
    print(
        f"{D}Everything else is treated as an "
        f"instruction to Neuron.{R}"
    )
    print()


def execute(
    text,
    workspace,
    session: ProviderSelection | None = None,
):
    if session is None:
        session = current_provider()

    gate = classify(text)
    security_line(gate)

    decision = str(
        gate.get("decision", "BLOCK")
    ).upper()

    # Fail closed. Review and isolation never silently
    # become permission to execute.
    if decision != "ALLOW":
        reasons = gate.get("reason_codes") or []

        print(
            f"{Y if decision != 'BLOCK' else RED}"
            f"Neuron did not execute this instruction."
            f"{R}"
        )

        if reasons:
            print(
                f"{D}reason: "
                f"{', '.join(map(str, reasons))}{R}"
            )

        return 20


    # --------------------------------------------------------
    # NEURON_SEMANTIC_FRONTDOOR_V1
    #
    # Every allowed user request is interpreted by the selected
    # LLM against the live capability registry.
    #
    # No phrase router owns task selection anymore.
    # --------------------------------------------------------

    semantic = handle_semantic_turn(
        text=text,
        session=session,
        workspace=workspace,
        sophyane_executable=find_sophyane(),
    )

    print()

    if semantic.steps:
        print(
            f"{C}●{R} "
            f"{B}Neuron{R} "
            f"{D}capabilities: "
            f"{', '.join(semantic.steps)}{R}"
        )
        print()
    else:
        print(
            f"{G}●{R} "
            f"{B}Neuron{R}"
        )
        print()

    if semantic.answer:
        print(
            semantic.answer
        )

    if semantic.ok:
        print()
        print(
            f"{G}✓{R} "
            f"{D}completed{R}"
        )
    else:
        if semantic.error:
            print(
                f"{RED}✗{R} "
                f"{semantic.error}"
            )

    return semantic.code

    # --------------------------------------------------------
    # NEURON_NATIVE_FRONTDOOR_V2
    #
    # Local state, sensing and bounded desktop actions do not
    # require a generic LLM. Security has already authorized
    # the user's instruction above.
    # --------------------------------------------------------

    native = handle_native(
        text
    )

    if native.handled:
        print()
        print(
            f"{C}●{R} "
            f"{B}Neuron{R} "
            f"{D}{native.capability}{R}"
        )
        print()

        if native.answer:
            print(native.answer)

        if native.ok:
            print()
            print(
                f"{G}✓{R} "
                f"{D}native capability "
                f"completed{R}"
            )
            return 0

        if native.error:
            print()
            print(
                f"{RED}✗{R} "
                f"{D}{native.error}{R}"
            )

        # Never turn a grounded sensing/action failure
        # into an ungrounded cloud-model answer.
        return 23

    # --------------------------------------------------------
    # NEURON_HARNESS_IDENTITY_ROUTER_V1
    #
    # Neuron owns identity and embodied perception.
    # Ordinary conversation goes directly to the selected
    # reasoning worker with a Neuron system prompt.
    # Sophyane remains the agentic execution harness.
    # --------------------------------------------------------

    identity_result = (
        handle_identity_perception(
            text
        )
    )

    if identity_result.handled:
        print()
        print(
            f"{C}●{R} "
            f"{B}Neuron{R} "
            f"{D}{identity_result.capability}{R}"
        )
        print()

        if identity_result.answer:
            print(
                identity_result.answer
            )

        if identity_result.ok:
            print()
            print(
                f"{G}✓{R} "
                f"{D}grounded{R}"
            )
            return 0

        if identity_result.error:
            print(
                f"{RED}✗{R} "
                f"{identity_result.error}"
            )

        # Never convert failed physical perception
        # into a text-model guess.
        return 23

    if not should_use_agentic_backend(
        text
    ):
        chat_agent = find_sophyane()

        if not chat_agent:
            print(
                f"{RED}Reasoning backend "
                f"unavailable.{R}"
            )
            return 21

        print()
        print(
            f"{G}●{R} "
            f"{B}Neuron{R} "
            f"{D}thinking with "
            f"{session.model}…{R}"
        )
        print()

        chat = run_neuron_chat(
            instruction=text,
            session_environment=(
                session.environment()
            ),
            sophyane_executable=(
                chat_agent
            ),
        )

        if not chat.ok:
            if chat.answer:
                print(
                    chat.answer
                )

            print(
                f"{RED}✗{R} "
                f"{chat.error}"
            )

            return (
                chat.returncode
                or 24
            )

        print(
            chat.answer
        )

        print()
        print(
            f"{G}✓{R} "
            f"{D}completed{R}"
        )

        return 0

    sophyane = find_sophyane()

    if not sophyane:
        print(
            f"{Y}General agent backend unavailable.{R}"
        )
        print(
            json.dumps(
                plan(text),
                indent=2,
                sort_keys=True,
            )
        )
        return 21

    env = os.environ.copy()
    env["NEURON_ACTIVE"] = "1"
    env["NEURON_HOME"] = str(ROOT)
    env["PYTHONUNBUFFERED"] = "1"

    # Explicit Neuron startup selection is the
    # provider authority for this execution.
    env.update(
        session.environment()
    )

    print()
    print(
        f"{G}●{R} {B}Neuron{R} {D}working…{R}"
    )
    print()

    try:
        proc = subprocess.Popen(
            [sophyane, text],
            cwd=str(workspace),
            env=env,
            stdin=sys.stdin,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
    except OSError as exc:
        print(f"{RED}{exc}{R}")
        return 22

    assert proc.stdout is not None

    # NEURON_BACKEND_FAILURE_DETECTION_V1
    backend_lines = []

    try:
        for line in proc.stdout:
            backend_lines.append(line)

            # Hide Sophyane's identity banner. It is an
            # execution backend inside the Neuron session.
            if line.startswith("◆ Sophyane "):
                continue

            print(line, end="", flush=True)

        code = proc.wait()

        backend_text = "".join(
            backend_lines
        ).casefold()

        failure_markers = (
            "all configured llm providers failed",
            "sophyane could not reach any working llm provider",
            "goal_met=false",
            "stopped_reason=provider_unavailable",
            "provider unavailable:",
            "execution failed",
        )

        if (
            code == 0
            and any(
                marker in backend_text
                for marker in failure_markers
            )
        ):
            code = 24

    except KeyboardInterrupt:
        print(
            f"\n{Y}Cancelling current instruction…{R}"
        )

        try:
            proc.send_signal(signal.SIGINT)
            proc.wait(timeout=4)
        except Exception:
            proc.kill()
            proc.wait()

        return 130

    print()

    if code == 0:
        print(f"{G}✓{R} {D}completed{R}")
    else:
        print(
            f"{Y}!{R} {D}agent exit={code}{R}"
        )

    return code


def interactive():
    workspace = safe_workspace()

    if TTY:
        print("\033[2J\033[H", end="")

    session = select_startup_provider()

    if TTY:
        print("\033[2J\033[H", end="")

    banner(
        workspace,
        session,
    )

    while True:
        try:
            text = input(
                f"{C}{B}›{R} "
            ).strip()

        except EOFError:
            print()
            print(f"{D}Neuron session closed.{R}")
            return 0

        except KeyboardInterrupt:
            print()
            continue

        if not text:
            continue

        if text in {
            "/exit",
            "/quit",
            "exit",
            "quit",
        }:
            print(f"{D}Neuron session closed.{R}")
            return 0

        if text == "/help":
            help_text()
            continue

        if text == "/status":
            show_status(
                workspace,
                session,
            )
            continue

        if text == "/pwd":
            print(workspace)
            continue

        if text == "/new":
            clear_session_history()
            reset_semantic_session()

            print(
                f"{G}✓{R} "
                f"{D}new conversation session{R}"
            )
            continue

        if text == "/clear":
            if TTY:
                print("\033[2J\033[H", end="")
            banner(
                workspace,
                session,
            )
            continue

        if text == "/model":
            session = (
                select_startup_provider()
            )

            print()
            print(
                f"{G}✓{R} "
                f"{D}provider → "
                f"{session.label}{R}"
            )
            print()
            continue

        if text.startswith("/cd "):
            raw = text[4:].strip()

            target = Path(
                os.path.expandvars(
                    os.path.expanduser(raw)
                )
            )

            if not target.is_absolute():
                target = workspace / target

            target = target.resolve()

            if not target.is_dir():
                print(
                    f"{RED}Not a directory: "
                    f"{target}{R}"
                )
                continue

            workspace = target
            print(
                f"{D}workspace → {workspace}{R}"
            )
            continue

        if text.startswith("/security "):
            query = text[10:].strip()

            print(
                json.dumps(
                    classify(query),
                    indent=2,
                    sort_keys=True,
                )
            )
            continue

        if text.startswith("/plan "):
            query = text[6:].strip()

            print(
                json.dumps(
                    plan(query),
                    indent=2,
                    sort_keys=True,
                )
            )
            continue

        print()
        execute(
            text,
            workspace,
            session,
        )
        print()


def main():
    parser = argparse.ArgumentParser(
        prog="neuron",
        add_help=False,
    )

    parser.add_argument(
        "-h",
        "--help",
        action="store_true",
    )
    parser.add_argument(
        "--version",
        action="store_true",
    )
    parser.add_argument(
        "--status",
        action="store_true",
    )
    parser.add_argument(
        "instruction",
        nargs="*",
    )

    args = parser.parse_args()
    workspace = safe_workspace()

    if args.version:
        print(f"Neuron {version()}")
        return 0

    if args.status:
        show_status(
            workspace,
            current_provider(),
        )
        return 0

    if args.help:
        banner(
            workspace,
            current_provider(),
        )
        help_text()
        return 0

    if args.instruction:
        text = " ".join(args.instruction).strip()

        session = (
            select_startup_provider()
            if sys.stdin.isatty()
            else current_provider()
        )

        banner(
            workspace,
            session,
        )

        return execute(
            text,
            workspace,
            session,
        )

    return interactive()


if __name__ == "__main__":
    raise SystemExit(main())
