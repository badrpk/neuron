"""Conservative answer-only eligibility gate for Neuron B2.

B2 is an evidence-answer path.

It does not:
- execute;
- select capabilities;
- authorize capabilities;
- persist;
- propagate.

Potential action, current-state, sensor, filesystem, or mixed
answer+action requests remain with the semantic capability planner.

READ != TRUST != PERSIST != EXECUTE != PROPAGATE
"""

from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class B2EligibilityDecision:
    eligible: bool
    confidence: float
    reason: str


def _normalized(
    text: str,
) -> str:
    return " ".join(
        str(
            text
            or ""
        )
        .strip()
        .casefold()
        .split()
    )


_ACTION_PATTERNS = (
    r"\bopen\b",
    r"\bdelete\b",
    r"\bremove\b",
    r"\brename\b",
    r"\bmove\b",
    r"\bcopy\b",
    r"\bsend\b",
    r"\bforward\b",
    r"\bclick\b",
    r"\btap\b",
    r"\bpress\b",
    r"\brun\b",
    r"\bexecute\b",
    r"\bdeploy\b",
    r"\binstall\b",
    r"\bbuild\b",
    r"\blaunch\b",
    r"\bstart\b",
    r"\bstop\b",
    r"\bwrite\b",
    r"\bedit\b",
    r"\bchange\b",
    r"\bupdate\b",
    r"\bupload\b",
    r"\bdownload\b",
    r"\bshow\s+me\b",
    r"\binspect\s+(?:the\s+)?current\b",
    r"\bcheck\s+(?:the\s+)?current\b",
    r"\bcurrent\s+screen\b",
    r"\bscreenshot\b",
    r"\bcamera\b",
    r"\bmicrophone\b",
    r"\bfilesystem\b",
    r"\bfile\s+from\b",
)


_RECALL_MARKERS = (
    "previous",
    "previously",
    "last time",
    "yesterday",
    "earlier",
    "stored",
    "remember",
    "remembered",
    "memory",
    "decision",
    "decide",
    "preference",
    "preferred",
    "used",
)


_ANSWER_SHAPES = (
    r"^(?:what|which|who|where|when|why|how)\b",
    r"^tell\s+me\b",
    r"^summari[sz]e\b",
    r"^describe\b",
    r"^explain\b",
)


def evaluate_b2_request_eligibility(
    text: str,
) -> B2EligibilityDecision:

    value = _normalized(
        text
    )

    if not value:
        return B2EligibilityDecision(
            eligible=False,
            confidence=1.0,
            reason="empty_request",
        )

    for pattern in _ACTION_PATTERNS:
        if re.search(
            pattern,
            value,
        ):
            return B2EligibilityDecision(
                eligible=False,
                confidence=0.99,
                reason=(
                    "possible_capability_or_action_request"
                ),
            )

    if not any(
        marker in value
        for marker in _RECALL_MARKERS
    ):
        return B2EligibilityDecision(
            eligible=False,
            confidence=0.95,
            reason="not_memory_answer_request",
        )

    if not any(
        re.search(
            pattern,
            value,
        )
        for pattern in _ANSWER_SHAPES
    ):
        return B2EligibilityDecision(
            eligible=False,
            confidence=0.95,
            reason="not_conservative_answer_shape",
        )

    return B2EligibilityDecision(
        eligible=True,
        confidence=0.98,
        reason="answer_only_memory_request",
    )
