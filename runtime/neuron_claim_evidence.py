"""Deterministic claim/evidence verification for Neuron B2.

This module grants no execution, persistence, or propagation authority.

READ evidence may support a claim, but only an explicit deterministic
verification result may mark that claim structurally supported.

READ != TRUST != PERSIST != EXECUTE != PROPAGATE
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from neuron_evidence_contract import (
    EvidenceBundle,
)

from neuron_claim_support import (
    ClaimSupportState,
    evaluate_claim_support,
)


#
# Evidence kinds in this set may establish factual support.
#
# Sophyane semantic_plan / semantic_ledger are intentionally absent.
# They describe interpretation/relevance, not factual truth.
#
SUPPORT_CAPABLE_KINDS = frozenset(
    {
        "memory_recall",
    }
)


@dataclass(frozen=True)
class GroundedClaim:
    text: str
    evidence_ids: tuple[int, ...]


@dataclass(frozen=True)
class GroundedAnswer:
    answer: str
    claims: tuple[GroundedClaim, ...]
    uncertainty: tuple[str, ...] = ()


@dataclass(frozen=True)
class ClaimEvidenceDecision:
    valid: bool
    supported_claims: int
    ambiguous_claims: int
    unsupported_claims: int
    contradicted_claims: int
    reason: str


def support_capable_indices(
    bundle: EvidenceBundle,
) -> tuple[int, ...]:
    result = []

    for index, item in enumerate(
        bundle.items
    ):
        if (
            item.permission == "READ"
            and bool(
                str(
                    item.provenance
                    or ""
                ).strip()
            )
            and item.kind
            in SUPPORT_CAPABLE_KINDS
        ):
            result.append(
                index
            )

    return tuple(
        result
    )


def has_support_capable_evidence(
    bundle: EvidenceBundle,
) -> bool:
    return bool(
        support_capable_indices(
            bundle
        )
    )


def verify_grounded_answer(
    *,
    candidate: GroundedAnswer,
    bundle: EvidenceBundle,
) -> ClaimEvidenceDecision:
    """
    Structural verifier.

    This deliberately does NOT ask an LLM whether a claim is true.

    It establishes:
      * every material claim cites evidence;
      * every cited ID exists;
      * every cited item remains READ;
      * every cited item has provenance;
      * every cited evidence type is support-capable.

    Semantic entailment is not inferred from retrieval confidence.
    """

    answer = str(
        candidate.answer
        or ""
    ).strip()

    if not answer:
        return ClaimEvidenceDecision(
            valid=False,
            supported_claims=0,
            ambiguous_claims=0,
            unsupported_claims=1,
            contradicted_claims=0,
            reason="empty_answer",
        )

    if not candidate.claims:
        return ClaimEvidenceDecision(
            valid=False,
            supported_claims=0,
            ambiguous_claims=0,
            unsupported_claims=1,
            contradicted_claims=0,
            reason="no_claims",
        )

    supported = 0
    ambiguous = 0
    unsupported = 0
    contradicted = 0

    size = len(
        bundle.items
    )

    for claim in candidate.claims:
        text = str(
            claim.text
            or ""
        ).strip()

        if not text:
            unsupported += 1
            continue

        if not claim.evidence_ids:
            unsupported += 1
            continue

        claim_ok = True
        claim_ambiguous = False
        claim_contradicted = False
        claim_unsupported = False

        for evidence_id in claim.evidence_ids:
            if (
                not isinstance(
                    evidence_id,
                    int,
                )
                or isinstance(
                    evidence_id,
                    bool,
                )
                or evidence_id < 0
                or evidence_id >= size
            ):
                claim_unsupported = True
                claim_ok = False
                break

            item = bundle.items[
                evidence_id
            ]

            if item.permission != "READ":
                claim_unsupported = True
                claim_ok = False
                break

            if not str(
                item.provenance
                or ""
            ).strip():
                claim_unsupported = True
                claim_ok = False
                break

            if (
                item.kind
                not in SUPPORT_CAPABLE_KINDS
            ):
                claim_unsupported = True
                claim_ok = False
                break

            #
            # Adapter errors can never support a claim.
            #
            if item.kind == "adapter_error":
                claim_unsupported = True
                claim_ok = False
                break

            support = evaluate_claim_support(
                claim=text,
                evidence_content=item.content,
            )

            if (
                support.state
                is ClaimSupportState.CONTRADICTED
            ):
                claim_contradicted = True
                claim_ok = False
                break

            if (
                support.state
                is ClaimSupportState.AMBIGUOUS
            ):
                claim_ambiguous = True
                claim_ok = False
                break

            if (
                support.state
                is ClaimSupportState.UNSUPPORTED
            ):
                claim_unsupported = True
                claim_ok = False
                break

            if (
                support.state
                is not ClaimSupportState.SUPPORTED
            ):
                claim_unsupported = True
                claim_ok = False
                break

        if claim_contradicted:
            contradicted += 1

        elif claim_unsupported:
            unsupported += 1

        elif claim_ambiguous:
            ambiguous += 1

        elif claim_ok:
            supported += 1

        else:
            unsupported += 1

    valid = (
        supported > 0
        and ambiguous == 0
        and unsupported == 0
        and contradicted == 0
    )

    if valid:
        reason = (
            "all_claims_structurally_supported"
        )

    elif contradicted > 0:
        reason = (
            "claim_evidence_contradicted"
        )

    elif unsupported > 0:
        reason = (
            "claim_evidence_unsupported"
        )

    elif ambiguous > 0:
        reason = (
            "claim_evidence_ambiguous"
        )

    else:
        reason = (
            "claim_evidence_verification_failed"
        )

    return ClaimEvidenceDecision(
        valid=valid,
        supported_claims=supported,
        ambiguous_claims=ambiguous,
        unsupported_claims=unsupported,
        contradicted_claims=contradicted,
        reason=reason,
    )
