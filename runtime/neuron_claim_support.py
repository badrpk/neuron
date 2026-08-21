"""Conservative deterministic claim/evidence support checks.

Evidence states are distinct:

    RETRIEVED != CITED != SUPPORTED

Local support requires full topical/material token coverage.

Negation is treated as semantic polarity, not as topical evidence.

Example:

    claim:
        deployment is not approved

    evidence:
        deployment is approved

Topical material:
        deployment approved

matches completely, while polarity differs.

Therefore:
        CONTRADICTED

No provider, network, execution, persistence, write, or propagation
authority exists here.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
import re
from typing import Any


class ClaimSupportState(
    str,
    Enum,
):
    SUPPORTED = "SUPPORTED"
    AMBIGUOUS = "AMBIGUOUS"
    CONTRADICTED = "CONTRADICTED"
    UNSUPPORTED = "UNSUPPORTED"


@dataclass(frozen=True)
class ClaimSupportDecision:
    state: ClaimSupportState
    score: float
    reason: str


_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "been",
        "being",
        "but",
        "by",
        "did",
        "do",
        "does",
        "for",
        "from",
        "had",
        "has",
        "have",
        "he",
        "her",
        "hers",
        "him",
        "his",
        "i",
        "in",
        "is",
        "it",
        "its",
        "me",
        "my",
        "of",
        "on",
        "or",
        "our",
        "ours",
        "she",
        "that",
        "the",
        "their",
        "theirs",
        "them",
        "they",
        "this",
        "to",
        "use",
        "used",
        "using",
        "was",
        "we",
        "were",
        "what",
        "which",
        "who",
        "with",
        "you",
        "your",
    }
)


_NEGATIONS = frozenset(
    {
        "not",
        "never",
        "no",
        "none",
        "without",
    }
)


def _tokens(
    value: str,
) -> tuple[str, ...]:

    raw = re.findall(
        r"[a-z0-9]+"
        r"(?:[._:/-][a-z0-9]+)*",
        str(
            value
            or ""
        ).casefold(),
    )

    return tuple(
        token
        for token in raw
        if token not in _STOPWORDS
    )


def _flatten_strings(
    value: Any,
) -> tuple[str, ...]:

    result: list[str] = []

    def visit(
        item: Any,
    ) -> None:

        if isinstance(
            item,
            str,
        ):
            text = item.strip()

            if text:
                result.append(
                    text
                )

            return

        if isinstance(
            item,
            dict,
        ):
            for child in item.values():
                visit(
                    child
                )

            return

        if isinstance(
            item,
            (
                list,
                tuple,
            ),
        ):
            for child in item:
                visit(
                    child
                )

            return

        if item is not None:
            try:
                rendered = json.dumps(
                    item,
                    ensure_ascii=False,
                    default=str,
                )

            except Exception:
                rendered = str(
                    item
                )

            if rendered:
                result.append(
                    rendered
                )

    visit(
        value
    )

    return tuple(
        result
    )


def evidence_text(
    content: dict[str, Any],
) -> str:
    return "\n".join(
        _flatten_strings(
            content
        )
    ).strip()


def evaluate_claim_support(
    *,
    claim: str,
    evidence_content: dict[str, Any],
) -> ClaimSupportDecision:

    claim_all = set(
        _tokens(
            claim
        )
    )

    evidence_all = set(
        _tokens(
            evidence_text(
                evidence_content
            )
        )
    )

    claim_negated = bool(
        claim_all
        & _NEGATIONS
    )

    evidence_negated = bool(
        evidence_all
        & _NEGATIONS
    )

    #
    # Negation is polarity rather than topical material.
    #
    claim_material = (
        claim_all
        - _NEGATIONS
    )

    evidence_material = (
        evidence_all
        - _NEGATIONS
    )

    if not claim_material:
        return ClaimSupportDecision(
            state=(
                ClaimSupportState.UNSUPPORTED
            ),
            score=0.0,
            reason="claim_has_no_material_tokens",
        )

    if not evidence_material:
        return ClaimSupportDecision(
            state=(
                ClaimSupportState.UNSUPPORTED
            ),
            score=0.0,
            reason="evidence_has_no_material_tokens",
        )

    overlap = (
        claim_material
        & evidence_material
    )

    coverage = (
        len(
            overlap
        )
        / len(
            claim_material
        )
    )

    #
    # Full/strong topical alignment plus opposite explicit
    # polarity is a contradiction.
    #
    if (
        coverage >= 0.70
        and claim_negated
        != evidence_negated
    ):
        return ClaimSupportDecision(
            state=(
                ClaimSupportState.CONTRADICTED
            ),
            score=coverage,
            reason="negation_polarity_conflict",
        )

    #
    # Strict local support:
    #
    # every material claim token must occur in evidence and
    # polarity must agree.
    #
    if (
        coverage >= 1.0
        and claim_negated
        == evidence_negated
    ):
        return ClaimSupportDecision(
            state=(
                ClaimSupportState.SUPPORTED
            ),
            score=coverage,
            reason=(
                "all_material_claim_tokens_present"
                "_and_polarity_agrees"
            ),
        )

    if coverage >= 0.70:
        return ClaimSupportDecision(
            state=(
                ClaimSupportState.AMBIGUOUS
            ),
            score=coverage,
            reason=(
                "strong_partial_support_requires_verification"
            ),
        )

    return ClaimSupportDecision(
        state=(
            ClaimSupportState.UNSUPPORTED
        ),
        score=coverage,
        reason=(
            "insufficient_claim_evidence_overlap"
        ),
    )
