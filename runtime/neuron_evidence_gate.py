"""Evidence acceptance gate for Neuron local intelligence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EvidenceDecision:
    adequate: bool

    confidence: float

    reason: str

    escalate: bool


def evaluate_local_evidence(
    *,
    handled: bool,
    complete: bool,
    confidence: float,
    answer: str | None,
    evidence: tuple[
        dict[str, Any],
        ...
    ],
) -> EvidenceDecision:
    """
    Phase-A acceptance is deliberately strict.

    A local deterministic result is accepted only when:

      * the substrate explicitly handled it;
      * computation is complete;
      * confidence >= 0.95;
      * a non-empty answer exists;
      * at least one evidence record exists.

    Anything else falls through. This gate grants no execution
    or propagation permission.
    """

    if not handled:
        return EvidenceDecision(
            adequate=False,
            confidence=0.0,
            reason="not_handled",
            escalate=False,
        )

    if not complete:
        return EvidenceDecision(
            adequate=False,
            confidence=confidence,
            reason="incomplete",
            escalate=False,
        )

    if confidence < 0.95:
        return EvidenceDecision(
            adequate=False,
            confidence=confidence,
            reason="confidence_below_phase_a_threshold",
            escalate=False,
        )

    if (
        answer is None
        or not str(
            answer
        ).strip()
    ):
        return EvidenceDecision(
            adequate=False,
            confidence=confidence,
            reason="empty_answer",
            escalate=False,
        )

    if not evidence:
        return EvidenceDecision(
            adequate=False,
            confidence=confidence,
            reason="missing_evidence",
            escalate=False,
        )

    return EvidenceDecision(
        adequate=True,
        confidence=confidence,
        reason="deterministic_evidence_complete",
        escalate=False,
    )
