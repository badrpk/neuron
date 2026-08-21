"""Read-only evidence contract for Neuron local intelligence.

Evidence is information, not authority.

READ != TRUST != PERSIST != EXECUTE != PROPAGATE
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EvidenceItem:
    source: str
    kind: str

    content: dict[
        str,
        Any,
    ]

    confidence: float

    provenance: str

    permission: str = "READ"


@dataclass(frozen=True)
class EvidenceBundle:
    query: str

    items: tuple[
        EvidenceItem,
        ...
    ]

    complete: bool

    confidence: float

    reason: str


def bounded_bundle(
    *,
    query: str,
    items: list[EvidenceItem],
    limit: int = 8,
) -> EvidenceBundle:

    bounded = tuple(
        items[:max(
            0,
            int(limit),
        )]
    )

    confidence = max(
        (
            float(item.confidence)
            for item in bounded
        ),
        default=0.0,
    )

    return EvidenceBundle(
        query=str(query),
        items=bounded,
        complete=bool(bounded),
        confidence=confidence,
        reason=(
            "evidence_available"
            if bounded
            else "no_read_side_evidence"
        ),
    )
