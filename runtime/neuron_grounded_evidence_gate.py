"""Final local gate for B2 grounded synthesis.

Disposition contract:

    all material claims SUPPORTED
        -> ACCEPT

    no unsupported/contradicted claims,
    but one or more AMBIGUOUS claims
        -> VERIFY

    any CONTRADICTED claim
        -> REJECT

    any UNSUPPORTED claim
        -> REJECT

VERIFY is not TRUST.

It is only permission to invoke a bounded evidence verifier
in a later phase.

READ != TRUST != PERSIST != EXECUTE != PROPAGATE
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from neuron_claim_evidence import (
    ClaimEvidenceDecision,
    GroundedAnswer,
)


class GroundedDisposition(
    str,
    Enum,
):
    ACCEPT = "ACCEPT"
    VERIFY = "VERIFY"
    REJECT = "REJECT"


@dataclass(frozen=True)
class GroundedGateDecision:
    disposition: GroundedDisposition
    answer: str
    confidence: float
    reason: str


def evaluate_grounded_answer(
    *,
    candidate: GroundedAnswer | None,
    verification: ClaimEvidenceDecision | None,
) -> GroundedGateDecision:

    if (
        candidate is None
        or verification is None
    ):
        return GroundedGateDecision(
            disposition=(
                GroundedDisposition.REJECT
            ),
            answer="",
            confidence=0.0,
            reason=(
                "missing_candidate_or_verification"
            ),
        )

    answer = str(
        candidate.answer
        or ""
    ).strip()

    if not answer:
        return GroundedGateDecision(
            disposition=(
                GroundedDisposition.REJECT
            ),
            answer="",
            confidence=0.0,
            reason="empty_candidate_answer",
        )

    #
    # REJECT has precedence over VERIFY.
    #
    # Contradiction must never be rescued merely because
    # another claim is ambiguous.
    #
    if (
        verification.contradicted_claims
        > 0
    ):
        return GroundedGateDecision(
            disposition=(
                GroundedDisposition.REJECT
            ),
            answer="",
            confidence=0.0,
            reason="contradicted_material_claim",
        )

    #
    # Genuine unsupported material must also fail closed.
    #
    if (
        verification.unsupported_claims
        > 0
    ):
        return GroundedGateDecision(
            disposition=(
                GroundedDisposition.REJECT
            ),
            answer="",
            confidence=0.0,
            reason="unsupported_material_claim",
        )

    #
    # Explicit model uncertainty also requires verification,
    # but only when there is no contradiction or unsupported
    # material.
    #
    if candidate.uncertainty:
        return GroundedGateDecision(
            disposition=(
                GroundedDisposition.VERIFY
            ),
            answer=answer,
            confidence=0.70,
            reason=(
                "candidate_contains_uncertainty"
            ),
        )

    #
    # B2.0.2:
    #
    # AMBIGUOUS is preserved independently from unsupported.
    #
    # It may be sent to a bounded verifier later, but cannot
    # receive local TRUST.
    #
    if (
        verification.ambiguous_claims
        > 0
    ):
        return GroundedGateDecision(
            disposition=(
                GroundedDisposition.VERIFY
            ),
            answer=answer,
            confidence=0.65,
            reason="ambiguous_claim_support",
        )

    #
    # Local ACCEPT requires the claim verifier's strict
    # all-supported result.
    #
    if verification.valid:
        return GroundedGateDecision(
            disposition=(
                GroundedDisposition.ACCEPT
            ),
            answer=answer,
            confidence=0.90,
            reason="structurally_grounded",
        )

    return GroundedGateDecision(
        disposition=(
            GroundedDisposition.REJECT
        ),
        answer="",
        confidence=0.0,
        reason=(
            verification.reason
            or "claim_evidence_verification_failed"
        ),
    )


def evaluate_external_grounded_verification(
    *,
    candidate: GroundedAnswer | None,
    verification: ClaimEvidenceDecision | None,
    external,
) -> GroundedGateDecision:
    """Deterministically consume a B2.1 external verifier result.

    The external model does not directly grant TRUST.

    ACCEPT occurs only when:
      * the local state contains ambiguity only;
      * the external response passed structural validation;
      * every ambiguous claim was judged SUPPORTED.

    CONTRADICTED / INSUFFICIENT / malformed / unavailable
    all fail closed.
    """

    if (
        candidate is None
        or verification is None
        or external is None
    ):
        return GroundedGateDecision(
            disposition=(
                GroundedDisposition.REJECT
            ),
            answer="",
            confidence=0.0,
            reason=(
                "missing_external_verification_state"
            ),
        )

    if (
        verification.contradicted_claims
        > 0
        or verification.unsupported_claims
        > 0
    ):
        return GroundedGateDecision(
            disposition=(
                GroundedDisposition.REJECT
            ),
            answer="",
            confidence=0.0,
            reason=(
                "local_reject_precedes_external_verifier"
            ),
        )

    if (
        verification.ambiguous_claims
        <= 0
    ):
        return GroundedGateDecision(
            disposition=(
                GroundedDisposition.REJECT
            ),
            answer="",
            confidence=0.0,
            reason="no_ambiguous_claims_to_verify",
        )

    if not bool(
        getattr(
            external,
            "ok",
            False,
        )
    ):
        return GroundedGateDecision(
            disposition=(
                GroundedDisposition.REJECT
            ),
            answer="",
            confidence=0.0,
            reason=(
                "external_verifier_failed:"
                + str(
                    getattr(
                        external,
                        "error",
                        "",
                    )
                    or "unknown"
                )
            ),
        )

    decisions = tuple(
        getattr(
            external,
            "decisions",
            (),
        )
        or ()
    )

    if (
        len(decisions)
        != verification.ambiguous_claims
    ):
        return GroundedGateDecision(
            disposition=(
                GroundedDisposition.REJECT
            ),
            answer="",
            confidence=0.0,
            reason=(
                "external_verifier_claim_count_mismatch"
            ),
        )

    verdict_values = tuple(
        str(
            getattr(
                item,
                "verdict",
                "",
            )
            .value
            if hasattr(
                getattr(
                    item,
                    "verdict",
                    "",
                ),
                "value",
            )
            else getattr(
                item,
                "verdict",
                "",
            )
        ).strip().upper()
        for item in decisions
    )

    if (
        "CONTRADICTED"
        in verdict_values
    ):
        return GroundedGateDecision(
            disposition=(
                GroundedDisposition.REJECT
            ),
            answer="",
            confidence=0.0,
            reason=(
                "external_verifier_contradicted_claim"
            ),
        )

    if (
        "INSUFFICIENT"
        in verdict_values
    ):
        return GroundedGateDecision(
            disposition=(
                GroundedDisposition.REJECT
            ),
            answer="",
            confidence=0.0,
            reason=(
                "external_verifier_insufficient_evidence"
            ),
        )

    if (
        not verdict_values
        or any(
            value != "SUPPORTED"
            for value in verdict_values
        )
    ):
        return GroundedGateDecision(
            disposition=(
                GroundedDisposition.REJECT
            ),
            answer="",
            confidence=0.0,
            reason=(
                "external_verifier_unknown_verdict"
            ),
        )

    answer = str(
        candidate.answer
        or ""
    ).strip()

    if not answer:
        return GroundedGateDecision(
            disposition=(
                GroundedDisposition.REJECT
            ),
            answer="",
            confidence=0.0,
            reason="empty_candidate_answer",
        )

    return GroundedGateDecision(
        disposition=(
            GroundedDisposition.ACCEPT
        ),
        answer=answer,
        confidence=0.82,
        reason=(
            "ambiguous_claims_externally_supported"
        ),
    )
