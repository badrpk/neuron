from __future__ import annotations

import ast
import importlib
import pathlib

import pytest

from neuron_claim_evidence import (
    ClaimEvidenceDecision,
    GroundedAnswer,
    GroundedClaim,
)

from neuron_grounded_evidence_gate import (
    GroundedDisposition,
    evaluate_external_grounded_verification,
)

from neuron_grounded_verifier import (
    ExternalClaimDecision,
    ExternalClaimVerdict,
    ExternalGroundedVerification,
)

from neuron_local_intelligence import (
    gather_local_intelligence,
)

from neuron_evidence_gate import (
    evaluate_local_evidence,
)


ROOT = (
    pathlib.Path(__file__)
    .resolve()
    .parents[2]
)

RUNTIME = ROOT / "runtime"


# Every Phase-A/B2 module must remain importable.
#
# Keeping the module names explicit also makes repository
# ownership of the new B2 surface visible to test-gap audits.
B2_MODULES = (
    "neuron_b2_request_eligibility",
    "neuron_claim_evidence",
    "neuron_claim_support",
    "neuron_deterministic_reasoning",
    "neuron_evidence_contract",
    "neuron_evidence_gate",
    "neuron_grounded_evidence_gate",
    "neuron_grounded_synthesis",
    "neuron_grounded_verifier",
    "neuron_intent_classifier",
    "neuron_local_intelligence",
    "neuron_sophyane_read_adapter",
    "neuron_xerus_read_adapter",
)


READ_GROUNDING_FILES = (
    "neuron_b2_request_eligibility.py",
    "neuron_claim_evidence.py",
    "neuron_claim_support.py",
    "neuron_deterministic_reasoning.py",
    "neuron_evidence_contract.py",
    "neuron_evidence_gate.py",
    "neuron_grounded_evidence_gate.py",
    "neuron_grounded_synthesis.py",
    "neuron_grounded_verifier.py",
    "neuron_intent_classifier.py",
    "neuron_local_intelligence.py",
    "neuron_sophyane_read_adapter.py",
    "neuron_xerus_read_adapter.py",
)


def _candidate() -> GroundedAnswer:
    return GroundedAnswer(
        answer="Grounded candidate.",
        claims=(
            GroundedClaim(
                text="Grounded candidate.",
                evidence_ids=(0,),
            ),
        ),
        uncertainty=(),
    )


def _ambiguous_local() -> ClaimEvidenceDecision:
    return ClaimEvidenceDecision(
        valid=False,
        supported_claims=0,
        ambiguous_claims=1,
        unsupported_claims=0,
        contradicted_claims=0,
        reason="claim_evidence_ambiguous",
    )


def _external(
    verdict: ExternalClaimVerdict,
) -> ExternalGroundedVerification:
    return ExternalGroundedVerification(
        ok=True,
        decisions=(
            ExternalClaimDecision(
                claim_index=0,
                verdict=verdict,
                evidence_ids=(0,),
                reason="pytest",
            ),
        ),
        error="",
    )


def _parse_runtime() -> tuple[ast.Module, ast.AST]:
    path = (
        RUNTIME /
        "neuron_semantic_runtime.py"
    )

    tree = ast.parse(
        path.read_text(
            encoding="utf-8"
        )
    )

    target = next(
        node
        for node in tree.body
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        )
        and node.name == "handle_semantic_turn"
    )

    return tree, target


def test_all_b2_modules_import():
    for name in B2_MODULES:
        module = importlib.import_module(
            name
        )

        assert module is not None


@pytest.mark.parametrize(
    ("question", "expected"),
    (
        (
            (
                "A farmer has 17 sheep. "
                "All but 9 run away. "
                "He then buys 4 more sheep."
            ),
            "13",
        ),
        (
            "What is 20 percent of 100?",
            "20",
        ),
        (
            (
                "Start at 10. "
                "Add 5, then multiply by 2."
            ),
            "30",
        ),
    ),
)
def test_phase_a_deterministic_reasoning(
    question,
    expected,
):
    result = gather_local_intelligence(
        question
    )

    gate = evaluate_local_evidence(
        handled=result.handled,
        complete=result.complete,
        confidence=result.confidence,
        answer=result.answer,
        evidence=result.evidence,
    )

    assert result.handled
    assert result.answer == expected
    assert gate.adequate


def test_external_verifier_dataclass_contract():
    from dataclasses import fields

    external_fields = tuple(
        field.name
        for field in fields(
            ExternalGroundedVerification
        )
    )

    claim_fields = tuple(
        field.name
        for field in fields(
            ExternalClaimDecision
        )
    )

    assert external_fields == (
        "ok",
        "decisions",
        "error",
    )

    assert "reason" not in external_fields

    assert claim_fields == (
        "claim_index",
        "verdict",
        "evidence_ids",
        "reason",
    )


def test_supported_external_verification_accepts():
    gate = (
        evaluate_external_grounded_verification(
            candidate=_candidate(),
            verification=_ambiguous_local(),
            external=_external(
                ExternalClaimVerdict.SUPPORTED
            ),
        )
    )

    assert (
        gate.disposition
        is GroundedDisposition.ACCEPT
    )

    assert gate.answer


@pytest.mark.parametrize(
    "verdict",
    (
        ExternalClaimVerdict.CONTRADICTED,
        ExternalClaimVerdict.INSUFFICIENT,
    ),
)
def test_non_supported_external_verdict_rejects(
    verdict,
):
    gate = (
        evaluate_external_grounded_verification(
            candidate=_candidate(),
            verification=_ambiguous_local(),
            external=_external(
                verdict
            ),
        )
    )

    assert (
        gate.disposition
        is GroundedDisposition.REJECT
    )

    assert not gate.answer


def test_external_provider_failure_fails_closed():
    external = ExternalGroundedVerification(
        ok=False,
        decisions=(),
        error="provider_failed",
    )

    gate = (
        evaluate_external_grounded_verification(
            candidate=_candidate(),
            verification=_ambiguous_local(),
            external=external,
        )
    )

    assert (
        gate.disposition
        is GroundedDisposition.REJECT
    )

    assert not gate.answer


def test_empty_external_decisions_fail_closed():
    external = ExternalGroundedVerification(
        ok=True,
        decisions=(),
        error="",
    )

    gate = (
        evaluate_external_grounded_verification(
            candidate=_candidate(),
            verification=_ambiguous_local(),
            external=external,
        )
    )

    assert (
        gate.disposition
        is GroundedDisposition.REJECT
    )

    assert not gate.answer


def test_external_claim_count_mismatch_fails_closed():
    external = ExternalGroundedVerification(
        ok=True,
        decisions=(
            ExternalClaimDecision(
                claim_index=0,
                verdict=(
                    ExternalClaimVerdict.SUPPORTED
                ),
                evidence_ids=(0,),
                reason="first",
            ),
            ExternalClaimDecision(
                claim_index=0,
                verdict=(
                    ExternalClaimVerdict.SUPPORTED
                ),
                evidence_ids=(0,),
                reason="duplicate",
            ),
        ),
        error="",
    )

    gate = (
        evaluate_external_grounded_verification(
            candidate=_candidate(),
            verification=_ambiguous_local(),
            external=external,
        )
    )

    assert (
        gate.disposition
        is GroundedDisposition.REJECT
    )

    assert not gate.answer


def test_runtime_b2_order_precedes_capability_execution():
    _, target = _parse_runtime()

    wanted = {
        "gather_local_intelligence",
        "evaluate_b2_request_eligibility",
        "gather_read_only_evidence",
        "synthesize_grounded_answer",
        "verify_grounded_answer",
        "evaluate_grounded_answer",
        "run_ambiguous_grounded_verification",
        "evaluate_external_grounded_verification",
        "_execute_plan",
    }

    rows = []

    for node in ast.walk(target):
        if not isinstance(
            node,
            ast.Call,
        ):
            continue

        if isinstance(
            node.func,
            ast.Name,
        ):
            name = node.func.id

        elif isinstance(
            node.func,
            ast.Attribute,
        ):
            name = node.func.attr

        else:
            continue

        if name in wanted:
            rows.append(
                (
                    node.lineno,
                    name,
                )
            )

    first = {}

    for line, name in sorted(rows):
        first.setdefault(
            name,
            line,
        )

    required = (
        "gather_local_intelligence",
        "evaluate_b2_request_eligibility",
        "gather_read_only_evidence",
        "synthesize_grounded_answer",
        "verify_grounded_answer",
        "evaluate_grounded_answer",
        "run_ambiguous_grounded_verification",
        "evaluate_external_grounded_verification",
        "_execute_plan",
    )

    for name in required:
        assert name in first

    for left, right in zip(
        required,
        required[1:],
    ):
        assert (
            first[left]
            <
            first[right]
        )


def test_external_verifier_is_invoked_only_for_ambiguity():
    _, target = _parse_runtime()

    parents = {}

    for node in ast.walk(target):
        for child in ast.iter_child_nodes(
            node
        ):
            parents[child] = node

    calls = []

    for node in ast.walk(target):
        if (
            isinstance(node, ast.Call)
            and isinstance(
                node.func,
                ast.Name,
            )
            and node.func.id
            == "run_ambiguous_grounded_verification"
        ):
            calls.append(node)

    assert len(calls) == 1

    current = calls[0]
    enclosing_if = None

    while current in parents:
        current = parents[current]

        if isinstance(
            current,
            ast.If,
        ):
            enclosing_if = current
            break

    assert enclosing_if is not None

    condition = ast.unparse(
        enclosing_if.test
    )

    for marker in (
        "GroundedDisposition.VERIFY",
        "ambiguous_claims",
        "unsupported_claims",
        "contradicted_claims",
    ):
        assert marker in condition


def test_b2_read_grounding_modules_have_no_network_or_process_authority():
    forbidden = {
        "subprocess",
        "socket",
        "urllib",
        "requests",
        "httpx",
    }

    violations = []

    for filename in READ_GROUNDING_FILES:
        path = RUNTIME / filename

        tree = ast.parse(
            path.read_text(
                encoding="utf-8"
            )
        )

        for node in ast.walk(tree):
            if isinstance(
                node,
                ast.Import,
            ):
                names = [
                    alias.name
                    for alias in node.names
                ]

            elif isinstance(
                node,
                ast.ImportFrom,
            ):
                names = (
                    [node.module]
                    if node.module
                    else []
                )

            else:
                continue

            for name in names:
                if (
                    name.split(".")[0]
                    in forbidden
                ):
                    violations.append(
                        (
                            filename,
                            node.lineno,
                            name,
                        )
                    )

    assert not violations


def test_gemini_transport_owned_by_quality_provider():
    verifier_path = (
        RUNTIME /
        "neuron_grounded_verifier.py"
    )

    quality_path = (
        RUNTIME /
        "neuron_quality_escalation.py"
    )

    verifier = ast.parse(
        verifier_path.read_text(
            encoding="utf-8"
        )
    )

    quality = ast.parse(
        quality_path.read_text(
            encoding="utf-8"
        )
    )

    verifier_functions = {
        node.name
        for node in verifier.body
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        )
    }

    quality_functions = {
        node.name
        for node in quality.body
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        )
    }

    assert (
        "verify_grounded_evidence_with_gemini"
        not in verifier_functions
    )

    assert (
        "verify_grounded_evidence_with_gemini"
        in quality_functions
    )
