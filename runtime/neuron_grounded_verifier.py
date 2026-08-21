"""Bounded external verification contract for Neuron B2.1.

This module has no network or provider ownership.

It receives:
- an already-created GroundedAnswer;
- the SAME bounded numbered READ EvidenceBundle;
- a deterministic ClaimEvidenceDecision;
- an injected verifier call.

Only AMBIGUOUS claims may be sent for stronger verification.

The external verifier may return only:

    SUPPORTED
    CONTRADICTED
    INSUFFICIENT

The external model does not grant execution, persistence,
propagation, or capability authority.

READ != TRUST != PERSIST != EXECUTE != PROPAGATE
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
from typing import Callable

from neuron_claim_evidence import (
    ClaimEvidenceDecision,
    GroundedAnswer,
    SUPPORT_CAPABLE_KINDS,
)

from neuron_claim_support import (
    ClaimSupportState,
    evaluate_claim_support,
)

from neuron_evidence_contract import (
    EvidenceBundle,
)


class ExternalClaimVerdict(
    str,
    Enum,
):
    SUPPORTED = "SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    INSUFFICIENT = "INSUFFICIENT"


@dataclass(frozen=True)
class ExternalClaimDecision:
    claim_index: int
    verdict: ExternalClaimVerdict
    evidence_ids: tuple[int, ...]
    reason: str


@dataclass(frozen=True)
class ExternalGroundedVerification:
    ok: bool
    decisions: tuple[
        ExternalClaimDecision,
        ...
    ] = ()
    error: str = ""


def _local_claim_state(
    *,
    candidate: GroundedAnswer,
    bundle: EvidenceBundle,
    claim_index: int,
) -> ClaimSupportState:
    claim = candidate.claims[
        claim_index
    ]

    text = str(
        claim.text
        or ""
    ).strip()

    if (
        not text
        or not claim.evidence_ids
    ):
        return ClaimSupportState.UNSUPPORTED

    state = ClaimSupportState.SUPPORTED

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
            or evidence_id >= len(
                bundle.items
            )
        ):
            return ClaimSupportState.UNSUPPORTED

        item = bundle.items[
            evidence_id
        ]

        if item.permission != "READ":
            return ClaimSupportState.UNSUPPORTED

        if not str(
            item.provenance
            or ""
        ).strip():
            return ClaimSupportState.UNSUPPORTED

        if (
            item.kind
            not in SUPPORT_CAPABLE_KINDS
        ):
            return ClaimSupportState.UNSUPPORTED

        if item.kind == "adapter_error":
            return ClaimSupportState.UNSUPPORTED

        support = evaluate_claim_support(
            claim=text,
            evidence_content=item.content,
        )

        if (
            support.state
            is ClaimSupportState.CONTRADICTED
        ):
            return ClaimSupportState.CONTRADICTED

        if (
            support.state
            is ClaimSupportState.UNSUPPORTED
        ):
            return ClaimSupportState.UNSUPPORTED

        if (
            support.state
            is ClaimSupportState.AMBIGUOUS
        ):
            state = ClaimSupportState.AMBIGUOUS

    return state


def ambiguous_claim_indices(
    *,
    candidate: GroundedAnswer,
    bundle: EvidenceBundle,
) -> tuple[int, ...]:
    result = []

    for index in range(
        len(
            candidate.claims
        )
    ):
        state = _local_claim_state(
            candidate=candidate,
            bundle=bundle,
            claim_index=index,
        )

        if (
            state
            is ClaimSupportState.AMBIGUOUS
        ):
            result.append(
                index
            )

    return tuple(
        result
    )


def build_grounded_verifier_prompt(
    *,
    request: str,
    candidate: GroundedAnswer,
    bundle: EvidenceBundle,
    ambiguous_indices: tuple[int, ...],
) -> str:
    evidence_rows = []

    for index, item in enumerate(
        bundle.items
    ):
        evidence_rows.append(
            {
                "id":
                    index,

                "source":
                    item.source,

                "kind":
                    item.kind,

                "permission":
                    item.permission,

                "provenance":
                    item.provenance,

                "retrieval_confidence":
                    item.confidence,

                "content":
                    item.content,
            }
        )

    claim_rows = []

    for index in ambiguous_indices:
        claim = candidate.claims[
            index
        ]

        claim_rows.append(
            {
                "claim_index":
                    index,

                "text":
                    claim.text,

                "allowed_evidence_ids":
                    list(
                        claim.evidence_ids
                    ),
            }
        )

    payload = {
        "original_request":
            str(
                request
                or ""
            ).strip(),

        "candidate_answer":
            candidate.answer,

        "ambiguous_claims":
            claim_rows,

        "numbered_read_evidence":
            evidence_rows,
    }

    return (
        "VERIFY ONLY THE AMBIGUOUS CLAIMS BELOW.\n\n"
        + json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            default=str,
        )
        + "\n\n"
        "Return strict JSON only."
    )


def parse_external_verification(
    *,
    raw: str,
    candidate: GroundedAnswer,
    ambiguous_indices: tuple[int, ...],
) -> ExternalGroundedVerification:
    value = str(
        raw
        or ""
    ).strip()

    if not value:
        return ExternalGroundedVerification(
            ok=False,
            error="empty_verifier_response",
        )

    try:
        data = json.loads(
            value
        )

    except json.JSONDecodeError:
        start = value.find(
            "{"
        )

        end = value.rfind(
            "}"
        )

        if (
            start < 0
            or end < start
        ):
            return ExternalGroundedVerification(
                ok=False,
                error="verifier_response_not_json",
            )

        try:
            data = json.loads(
                value[
                    start:
                    end + 1
                ]
            )

        except Exception:
            return ExternalGroundedVerification(
                ok=False,
                error="verifier_response_invalid_json",
            )

    if not isinstance(
        data,
        dict,
    ):
        return ExternalGroundedVerification(
            ok=False,
            error="verifier_root_not_object",
        )

    raw_decisions = data.get(
        "claims"
    )

    if not isinstance(
        raw_decisions,
        list,
    ):
        return ExternalGroundedVerification(
            ok=False,
            error="verifier_claims_not_array",
        )

    expected = set(
        ambiguous_indices
    )

    seen = set()
    decisions = []

    for item in raw_decisions:
        if not isinstance(
            item,
            dict,
        ):
            return ExternalGroundedVerification(
                ok=False,
                error="verifier_claim_not_object",
            )

        claim_index = item.get(
            "claim_index"
        )

        if (
            not isinstance(
                claim_index,
                int,
            )
            or isinstance(
                claim_index,
                bool,
            )
            or claim_index
            not in expected
            or claim_index
            in seen
        ):
            return ExternalGroundedVerification(
                ok=False,
                error="invalid_or_duplicate_claim_index",
            )

        seen.add(
            claim_index
        )

        raw_verdict = str(
            item.get(
                "verdict"
            )
            or ""
        ).strip().upper()

        try:
            verdict = ExternalClaimVerdict(
                raw_verdict
            )

        except ValueError:
            return ExternalGroundedVerification(
                ok=False,
                error="invalid_verifier_verdict",
            )

        ids = item.get(
            "evidence_ids"
        )

        if not isinstance(
            ids,
            list,
        ):
            return ExternalGroundedVerification(
                ok=False,
                error="verifier_evidence_ids_not_array",
            )

        normalized_ids = []

        allowed = set(
            candidate.claims[
                claim_index
            ].evidence_ids
        )

        for evidence_id in ids:
            if (
                not isinstance(
                    evidence_id,
                    int,
                )
                or isinstance(
                    evidence_id,
                    bool,
                )
                or evidence_id
                not in allowed
            ):
                return ExternalGroundedVerification(
                    ok=False,
                    error=(
                        "verifier_used_unallowed_evidence_id"
                    ),
                )

            normalized_ids.append(
                evidence_id
            )

        #
        # SUPPORTED / CONTRADICTED must point to actual
        # evidence already cited by the candidate.
        #
        if (
            verdict
            in {
                ExternalClaimVerdict.SUPPORTED,
                ExternalClaimVerdict.CONTRADICTED,
            }
            and not normalized_ids
        ):
            return ExternalGroundedVerification(
                ok=False,
                error="verdict_missing_evidence_ids",
            )

        reason = str(
            item.get(
                "reason"
            )
            or ""
        ).strip()

        decisions.append(
            ExternalClaimDecision(
                claim_index=claim_index,
                verdict=verdict,
                evidence_ids=tuple(
                    normalized_ids
                ),
                reason=reason,
            )
        )

    if seen != expected:
        return ExternalGroundedVerification(
            ok=False,
            error="verifier_did_not_cover_all_ambiguous_claims",
        )

    return ExternalGroundedVerification(
        ok=True,
        decisions=tuple(
            sorted(
                decisions,
                key=lambda item:
                    item.claim_index,
            )
        ),
        error="",
    )


def run_ambiguous_grounded_verification(
    *,
    request: str,
    candidate: GroundedAnswer,
    bundle: EvidenceBundle,
    local_verification: ClaimEvidenceDecision,
    verifier_call: Callable[..., object],
) -> ExternalGroundedVerification:
    """
    Invoke an injected bounded verifier.

    This function itself owns no provider/network authority.
    """

    if (
        local_verification.contradicted_claims
        > 0
        or local_verification.unsupported_claims
        > 0
    ):
        return ExternalGroundedVerification(
            ok=False,
            error=(
                "local_reject_state_not_verifiable"
            ),
        )

    if (
        local_verification.ambiguous_claims
        <= 0
    ):
        return ExternalGroundedVerification(
            ok=False,
            error="no_ambiguous_claims",
        )

    indices = ambiguous_claim_indices(
        candidate=candidate,
        bundle=bundle,
    )

    if (
        not indices
        or len(indices)
        != local_verification.ambiguous_claims
    ):
        return ExternalGroundedVerification(
            ok=False,
            error=(
                "ambiguous_claim_accounting_mismatch"
            ),
        )

    prompt = build_grounded_verifier_prompt(
        request=request,
        candidate=candidate,
        bundle=bundle,
        ambiguous_indices=indices,
    )

    result = verifier_call(
        instruction=request,
        verifier_prompt=prompt,
    )

    if not bool(
        getattr(
            result,
            "ok",
            False,
        )
    ):
        return ExternalGroundedVerification(
            ok=False,
            error=(
                str(
                    getattr(
                        result,
                        "error",
                        "",
                    )
                    or "verifier_provider_failed"
                )
            ),
        )

    return parse_external_verification(
        raw=str(
            getattr(
                result,
                "answer",
                "",
            )
            or ""
        ),
        candidate=candidate,
        ambiguous_indices=indices,
    )
