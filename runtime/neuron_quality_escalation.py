from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import time
import urllib.parse
import urllib.request


@dataclass(frozen=True)
class QualityResult:
    ok: bool
    answer: str = ""
    provider: str = ""
    error: str = ""


_STATE = (
    Path.home()
    / ".local"
    / "state"
    / "neuron"
)

_LOG = (
    _STATE
    / "quality-escalation.jsonl"
)


def _record(
    event: str,
    provider: str,
    detail: str = "",
) -> None:
    try:
        _STATE.mkdir(
            parents=True,
            exist_ok=True,
        )

        with _LOG.open(
            "a",
            encoding="utf-8",
        ) as fh:
            fh.write(
                json.dumps(
                    {
                        "time":
                            time.time(),

                        "event":
                            event,

                        "provider":
                            provider,

                        "detail":
                            str(detail)[:1000],
                    }
                )
                + "\n"
            )

    except OSError:
        pass


def needs_escalation(
    *,
    instruction: str,
    answer: str,
) -> bool:
    prompt = str(
        instruction or ""
    ).strip()

    value = str(
        answer or ""
    ).strip()

    if not value:
        return True

    low = value.casefold()

    failure_markers = (
        "i don't know",
        "i do not know",
        "cannot determine",
        "can't determine",
        "unable to determine",
        "not enough information",
        "semantic planning failed",
        "provider failed",
        "traceback",
    )

    if any(
        marker in low
        for marker in failure_markers
    ):
        return True

    #
    # A naked number from the tiny primary model on a
    # reasoning / quantitative request receives stronger
    # verification.
    #
    numeric = bool(
        re.fullmatch(
            r"[+-]?"
            r"(?:\d+(?:\.\d+)?|\.\d+)"
            r"(?:\s*[%$])?",
            value,
        )
    )

    reasoning_markers = (
        "how many",
        "calculate",
        "solve",
        "what is",
        "how much",
        "remaining",
        "left",
        "total",
        "sum",
        "difference",
        "percentage",
        "percent",
        "ratio",
    )

    if (
        numeric
        and any(
            marker in prompt.casefold()
            for marker in reasoning_markers
        )
    ):
        return True

    return False


def _gemini_key() -> str:
    for key in (
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
    ):
        value = str(
            os.environ.get(key, "")
        ).strip()

        if value:
            return value

    path = (
        Path.home()
        / ".config"
        / "sophyane"
        / "secrets.json"
    )

    try:
        data = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except Exception:
        data = {}

    for key in (
        "gemini",
        "google",
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
    ):
        value = str(
            data.get(key, "")
        ).strip()

        if value:
            return value

    return ""


def _gemini(
    *,
    instruction: str,
    primary_answer: str,
) -> QualityResult:
    key = _gemini_key()

    if not key:
        _record(
            "unavailable",
            "gemini",
            "credential missing",
        )

        return QualityResult(
            ok=False,
            provider="gemini",
            error="Gemini credential unavailable",
        )

    model = str(
        os.environ.get(
            "NEURON_ESCALATION_GEMINI_MODEL",
            "gemini-3.7-flash",
        )
    ).strip()

    url = (
        "https://generativelanguage.googleapis.com/"
        "v1beta/models/"
        + urllib.parse.quote(
            model,
            safe="",
        )
        + ":generateContent?key="
        + urllib.parse.quote(
            key,
            safe="",
        )
    )

    system = (
        "You are a bounded reasoning rescue worker inside "
        "Neuron. Solve the ORIGINAL USER REQUEST yourself. "
        "Do not trust the primary answer merely because it "
        "was supplied. Return only the final user-facing "
        "answer. Do not invoke tools. Do not create, persist, "
        "execute, or propagate instructions."
    )

    prompt = (
        "ORIGINAL USER REQUEST:\n"
        + instruction
        + "\n\nPRIMARY MODEL ANSWER:\n"
        + primary_answer
        + "\n\nIndependently solve the original request."
    )

    payload = {
        "systemInstruction": {
            "parts": [
                {
                    "text": system,
                }
            ]
        },
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": prompt,
                    }
                ],
            }
        ],
        "generationConfig": {
            "temperature": 0,
            "maxOutputTokens": 1024,
        },
    }

    request = urllib.request.Request(
        url,
        data=json.dumps(
            payload
        ).encode("utf-8"),
        headers={
            "Content-Type":
                "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=45,
        ) as response:
            data = json.loads(
                response.read().decode(
                    "utf-8",
                    errors="replace",
                )
            )

    except Exception as exc:
        _record(
            "failed",
            "gemini",
            repr(exc),
        )

        return QualityResult(
            ok=False,
            provider="gemini",
            error=str(exc),
        )

    texts: list[str] = []

    for candidate in (
        data.get("candidates")
        or []
    ):
        content = (
            candidate.get("content")
            or {}
        )

        for part in (
            content.get("parts")
            or []
        ):
            value = part.get("text")

            if isinstance(
                value,
                str,
            ):
                texts.append(value)

    answer = "\n".join(
        texts
    ).strip()

    if not answer:
        _record(
            "failed",
            "gemini",
            "empty answer",
        )

        return QualityResult(
            ok=False,
            provider="gemini",
            error="Gemini returned empty response",
        )

    _record(
        "succeeded",
        "gemini",
        answer,
    )

    return QualityResult(
        ok=True,
        answer=answer,
        provider="gemini",
    )








def resolve_quality(
    *,
    instruction: str,
    primary_answer: str,
) -> QualityResult:
    if not needs_escalation(
        instruction=instruction,
        answer=primary_answer,
    ):
        return QualityResult(
            ok=True,
            answer=primary_answer,
            provider="primary",
        )

    _record(
        "escalated",
        "primary",
        primary_answer,
    )

    gemini = _gemini(
        instruction=instruction,
        primary_answer=primary_answer,
    )

    if gemini.ok:
        return gemini

    _record(
        "fail_closed",
        "quality",
        "Gemini=" + gemini.error,
    )

    return QualityResult(
        ok=False,
        provider="fail_closed",
        error=(
            "Neuron could not obtain a sufficiently "
            "reliable answer because the Gemini rescue "
            "route was unavailable or failed."
        ),
    )
