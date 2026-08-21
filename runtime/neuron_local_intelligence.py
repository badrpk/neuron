"""Read/transform-only local intelligence substrate.

Phase A contains only deterministic reasoning.

Later Sophyane/Xerus adapters must return evidence through this
boundary rather than obtaining security or execution authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from neuron_deterministic_reasoning import (
    solve_deterministically,
)
from neuron_intent_classifier import (
    Intent,
    classify_intent,
)

from neuron_evidence_contract import (
    EvidenceBundle,
    bounded_bundle,
)

from neuron_sophyane_read_adapter import (
    gather_sophyane_evidence,
)

from neuron_xerus_read_adapter import (
    gather_xerus_evidence,
)


@dataclass(frozen=True)
class LocalIntelligenceResult:
    handled: bool

    intent: str

    answer: str | None

    confidence: float

    complete: bool

    evidence: tuple[
        dict[str, Any],
        ...
    ]

    reason: str


def gather_local_intelligence(
    text: str,
) -> LocalIntelligenceResult:
    decision = classify_intent(
        text
    )

    if (
        decision.intent
        is not Intent.DETERMINISTIC
    ):
        return LocalIntelligenceResult(
            handled=False,
            intent=decision.intent.value,
            answer=None,
            confidence=decision.confidence,
            complete=False,
            evidence=(),
            reason=decision.reason,
        )

    result = solve_deterministically(
        text
    )

    if not result.solved:
        return LocalIntelligenceResult(
            handled=False,
            intent=decision.intent.value,
            answer=None,
            confidence=0.0,
            complete=False,
            evidence=(),
            reason=result.reason,
        )

    return LocalIntelligenceResult(
        handled=True,
        intent=decision.intent.value,
        answer=result.answer,
        confidence=min(
            decision.confidence,
            result.confidence,
        ),
        complete=True,
        evidence=result.evidence,
        reason=result.reason,
    )

def gather_read_only_evidence(
    text: str,
) -> EvidenceBundle:
    """Collect bounded BADRPK evidence without upgrading authority."""

    query = str(
        text
        or ""
    ).strip()

    if not query:
        return bounded_bundle(
            query=query,
            items=[],
            limit=8,
        )

    items = []

    items.extend(
        gather_sophyane_evidence(
            query
        )
    )

    items.extend(
        gather_xerus_evidence(
            query,
            limit=4,
        )
    )

    #
    # Adapter failures are diagnostics, not trustworthy evidence.
    #
    usable = [
        item
        for item in items
        if (
            item.kind
            != "adapter_error"
            and item.confidence > 0.0
            and item.permission == "READ"
        )
    ]

    return bounded_bundle(
        query=query,
        items=usable,
        limit=8,
    )
