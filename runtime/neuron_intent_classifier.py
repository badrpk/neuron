"""Conservative pre-planner task classification for Neuron.

This module has no execution authority.

It may recognize a task class, but recognition never grants:
READ, TRUST, PERSIST, EXECUTE, or PROPAGATE authority.

Phase A deliberately recognizes only deterministic tasks with
high structural confidence. Everything else falls through to the
existing semantic runtime.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re


class Intent(str, Enum):
    DETERMINISTIC = "deterministic"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class IntentDecision:
    intent: Intent
    confidence: float
    reason: str


_NUMBER = r"(?:\d+(?:\.\d+)?)"


def _normalized(text: str) -> str:
    return " ".join(
        str(text)
        .strip()
        .lower()
        .split()
    )


def classify_intent(
    text: str,
) -> IntentDecision:
    """Return only high-confidence deterministic classification.

    Important:
    This is not a general semantic router.

    Anything outside the small deterministic contract remains UNKNOWN
    and proceeds through Neuron's existing semantic planner.
    """

    value = _normalized(
        text
    )

    if not value:
        return IntentDecision(
            intent=Intent.UNKNOWN,
            confidence=0.0,
            reason="empty_input",
        )

    #
    # Explicit arithmetic expression.
    #
    if re.fullmatch(
        rf"\s*{_NUMBER}"
        rf"\s*[+\-*/]\s*"
        rf"{_NUMBER}\s*[?]?\s*",
        value,
    ):
        return IntentDecision(
            intent=Intent.DETERMINISTIC,
            confidence=0.99,
            reason="explicit_binary_arithmetic",
        )

    #
    # Percentage phrasing:
    # "What is 20 percent of 100?"
    #
    if re.search(
        rf"\b{_NUMBER}\s+"
        r"(?:percent|%)\s+of\s+"
        rf"{_NUMBER}\b",
        value,
    ):
        return IntentDecision(
            intent=Intent.DETERMINISTIC,
            confidence=0.98,
            reason="explicit_percentage",
        )

    #
    # Exception-set construction:
    #
    #   all but 9 run away
    #   all except 3 fly away
    #
    # This structure has exact deterministic semantics:
    # the exception count remains.
    #
    if re.search(
        rf"\ball\s+(?:but|except)\s+{_NUMBER}\b",
        value,
    ):
        return IntentDecision(
            intent=Intent.DETERMINISTIC,
            confidence=0.98,
            reason="exception_cardinality",
        )

    #
    # Explicit sequential arithmetic:
    # "Start at 10. Add 5, then multiply by 2."
    #
    if (
        re.search(
            rf"\bstart\s+(?:at|with)\s+{_NUMBER}\b",
            value,
        )
        and re.search(
            rf"\b(?:add|subtract|multiply|divide)\b",
            value,
        )
    ):
        return IntentDecision(
            intent=Intent.DETERMINISTIC,
            confidence=0.97,
            reason="explicit_arithmetic_sequence",
        )

    return IntentDecision(
        intent=Intent.UNKNOWN,
        confidence=0.0,
        reason="not_high_confidence_deterministic",
    )
