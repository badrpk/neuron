from __future__ import annotations

import ast
import pathlib


ROOT = (
    pathlib.Path(__file__)
    .resolve()
    .parents[2]
)

RUNTIME = (
    ROOT /
    "runtime" /
    "neuron_semantic_runtime.py"
)


def _handler():
    tree = ast.parse(
        RUNTIME.read_text(
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


def _call_name(node):
    if not isinstance(
        node,
        ast.Call,
    ):
        return None

    if isinstance(
        node.func,
        ast.Name,
    ):
        return node.func.id

    if isinstance(
        node.func,
        ast.Attribute,
    ):
        return node.func.attr

    return None


def test_semantic_runtime_has_exact_bounded_repair_structure():
    _, target = _handler()

    reasoner_calls = [
        node
        for node in ast.walk(target)
        if (
            isinstance(node, ast.Call)
            and _call_name(node)
            == "_semantic_plan_with_reasoner"
        )
    ]

    validator_calls = [
        node
        for node in ast.walk(target)
        if (
            isinstance(node, ast.Call)
            and _call_name(node)
            == "validate_plan"
        )
    ]

    assert len(reasoner_calls) == 3
    assert len(validator_calls) == 2


def test_first_generation_failure_gets_only_one_repair():
    _, target = _handler()

    outer_try = next(
        node
        for node in target.body
        if (
            isinstance(node, ast.Try)
            and any(
                isinstance(child, ast.Call)
                and _call_name(child)
                == "_semantic_plan_with_reasoner"
                for child in ast.walk(
                    ast.Module(
                        body=node.body,
                        type_ignores=[],
                    )
                )
            )
            and any(
                isinstance(handler.type, ast.Name)
                and handler.type.id == "Exception"
                for handler in node.handlers
                if handler.type is not None
            )
        )
    )

    assert len(
        outer_try.handlers
    ) == 1

    first_handler = (
        outer_try.handlers[0]
    )

    # Count only reasoner calls belonging directly to the
    # first-generation recovery body. Do not recursively count
    # calls contained inside nested exception handlers.
    direct_repair_calls = []

    for statement in first_handler.body:
        if isinstance(
            statement,
            ast.Try,
        ):
            for child in ast.walk(
                ast.Module(
                    body=statement.body,
                    type_ignores=[],
                )
            ):
                if (
                    isinstance(child, ast.Call)
                    and _call_name(child)
                    == "_semantic_plan_with_reasoner"
                ):
                    direct_repair_calls.append(
                        child
                    )

    assert len(
        direct_repair_calls
    ) == 1

    nested_handlers = [
        child
        for statement in first_handler.body
        if isinstance(statement, ast.Try)
        for child in statement.handlers
    ]

    assert len(
        nested_handlers
    ) == 1

    failure_text = ast.unparse(
        nested_handlers[0]
    )

    assert (
        "semantic planning failed through "
        "Switchyard reasoner"
        in failure_text
    )



def test_validation_failure_gets_only_one_repair():
    _, target = _handler()

    matching = []

    for handler in ast.walk(target):
        if not isinstance(
            handler,
            ast.ExceptHandler,
        ):
            continue

        if handler.type is None:
            continue

        if (
            ast.unparse(handler.type)
            == "PlanValidationError"
        ):
            matching.append(
                handler
            )

    assert len(matching) == 1

    handler = matching[0]

    reasoner_calls = [
        node
        for node in ast.walk(handler)
        if (
            isinstance(node, ast.Call)
            and _call_name(node)
            == "_semantic_plan_with_reasoner"
        )
    ]

    validator_calls = [
        node
        for node in ast.walk(handler)
        if (
            isinstance(node, ast.Call)
            and _call_name(node)
            == "validate_plan"
        )
    ]

    assert len(reasoner_calls) == 1
    assert len(validator_calls) == 1


def test_repair_prompt_forbids_reply_as_capability():
    _, target = _handler()

    texts = []

    for node in ast.walk(target):
        if (
            isinstance(node, ast.Call)
            and _call_name(node)
            == "_semantic_plan_with_reasoner"
        ):
            texts.append(
                ast.unparse(node)
            )

    combined = "\n".join(
        texts
    )

    assert (
        "top-level reply field is NOT a capability"
        in combined
    )

    assert (
        "Never emit capability='reply'"
        in combined
    )


def test_repair_preserves_direct_answer_vs_capability_modes():
    _, target = _handler()

    text = ast.unparse(
        target
    )

    assert "DIRECT-ANSWER MODE" in text
    assert "CAPABILITY MODE" in text

    assert "Set steps=[]" in text

    assert (
        "Set reply=null whenever steps is non-empty"
        in text
    )


def test_repaired_plan_still_uses_normal_validator():
    _, target = _handler()

    text = ast.unparse(
        target
    )

    assert (
        "plan = validate_plan("
        in text
    )

    assert (
        "repaired_raw_plan"
        in text
    )

    assert (
        "step_provenance_resolver=resolve_step"
        in text
        or
        "step_provenance_resolver=(resolve_step)"
        in text
    )


def test_repair_failure_returns_code_26():
    _, target = _handler()

    matches = []

    for node in ast.walk(target):
        if not isinstance(
            node,
            ast.Return,
        ):
            continue

        if node.value is None:
            continue

        text = ast.unparse(
            node.value
        )

        if (
            "after one bounded repair attempt"
            in text
        ):
            matches.append(
                text
            )

    assert len(matches) == 1

    assert "code=26" in matches[0]


def test_generation_repair_failure_returns_code_25():
    _, target = _handler()

    matches = []

    for node in ast.walk(target):
        if not isinstance(
            node,
            ast.Return,
        ):
            continue

        if node.value is None:
            continue

        text = ast.unparse(
            node.value
        )

        if (
            "semantic planning failed through "
            "Switchyard reasoner"
            in text
        ):
            matches.append(
                text
            )

    assert len(matches) == 1

    assert "code=25" in matches[0]


def test_execution_occurs_only_after_validation_and_repair():
    _, target = _handler()

    calls = []

    for node in ast.walk(target):
        if not isinstance(
            node,
            ast.Call,
        ):
            continue

        name = _call_name(
            node
        )

        if name in {
            "_semantic_plan_with_reasoner",
            "validate_plan",
            "_execute_plan",
        }:
            calls.append(
                (
                    node.lineno,
                    name,
                )
            )

    calls.sort()

    execution_lines = [
        line
        for line, name
        in calls
        if name == "_execute_plan"
    ]

    validation_lines = [
        line
        for line, name
        in calls
        if name == "validate_plan"
    ]

    assert len(execution_lines) == 1
    assert validation_lines

    assert (
        max(validation_lines)
        <
        execution_lines[0]
    )


def test_model_cannot_relax_security_during_repair():
    _, target = _handler()

    repair_handler = next(
        node
        for node in ast.walk(target)
        if (
            isinstance(
                node,
                ast.ExceptHandler,
            )
            and node.type is not None
            and ast.unparse(node.type)
            == "PlanValidationError"
        )
    )

    reasoner_calls = [
        node
        for node in ast.walk(
            repair_handler
        )
        if (
            isinstance(node, ast.Call)
            and _call_name(node)
            == "_semantic_plan_with_reasoner"
        )
    ]

    validator_calls = [
        node
        for node in ast.walk(
            repair_handler
        )
        if (
            isinstance(node, ast.Call)
            and _call_name(node)
            == "validate_plan"
        )
    ]

    execute_calls = [
        node
        for node in ast.walk(
            repair_handler
        )
        if (
            isinstance(node, ast.Call)
            and _call_name(node)
            == "_execute_plan"
        )
    ]

    assert len(reasoner_calls) == 1
    assert len(validator_calls) == 1
    assert not execute_calls

    validator = validator_calls[0]

    keyword_names = {
        keyword.arg
        for keyword in validator.keywords
        if keyword.arg is not None
    }

    assert "provenance" in keyword_names

    assert (
        "step_provenance_resolver"
        in keyword_names
    )

    provenance_keyword = next(
        keyword
        for keyword in validator.keywords
        if keyword.arg == "provenance"
    )

    resolver_keyword = next(
        keyword
        for keyword in validator.keywords
        if (
            keyword.arg
            == "step_provenance_resolver"
        )
    )

    assert (
        "fallback_dict"
        in ast.unparse(
            provenance_keyword.value
        )
    )

    assert (
        "resolve_step"
        in ast.unparse(
            resolver_keyword.value
        )
    )



def test_repair_dependency_contract_is_explicit():
    _, target = _handler()

    text = ast.unparse(
        target
    )

    assert (
        "depends_on must be an array"
        in text
    )

    assert (
        "zero-based integer indices of earlier steps"
        in text
    )


def test_no_execution_call_inside_validation_repair_handler():
    _, target = _handler()

    repair_handler = next(
        node
        for node in ast.walk(target)
        if (
            isinstance(
                node,
                ast.ExceptHandler,
            )
            and node.type is not None
            and ast.unparse(node.type)
            == "PlanValidationError"
        )
    )

    execute_calls = [
        node
        for node in ast.walk(
            repair_handler
        )
        if (
            isinstance(node, ast.Call)
            and _call_name(node)
            == "_execute_plan"
        )
    ]

    assert not execute_calls
