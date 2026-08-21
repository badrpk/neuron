"""Pure deterministic reasoning primitives for Neuron Phase A."""

from __future__ import annotations

import ast
from dataclasses import dataclass
import operator
import re
from typing import Any


@dataclass(frozen=True)
class DeterministicResult:
    solved: bool
    answer: str | None
    confidence: float
    reason: str
    evidence: tuple[dict[str, Any], ...] = ()


_NUMBER_PATTERN = (
    r"-?\d+(?:\.\d+)?"
)


def _number(
    value: str,
) -> int | float:
    result = float(
        value
    )

    if result.is_integer():
        return int(
            result
        )

    return result


def _display(
    value: int | float,
) -> str:
    if isinstance(
        value,
        float,
    ) and value.is_integer():
        return str(
            int(value)
        )

    return str(
        value
    )


def _exception_cardinality(
    text: str,
) -> DeterministicResult | None:
    """
    Handle constructions such as:

      A farmer has 17 sheep.
      All but 9 run away.
      He then buys 4 more.

    "All but N" means exactly N remain.
    """

    value = " ".join(
        text.strip().lower().split()
    )

    exception = re.search(
        rf"\ball\s+(?:but|except)\s+"
        rf"({_NUMBER_PATTERN})\b",
        value,
    )

    if exception is None:
        return None

    remaining = _number(
        exception.group(1)
    )

    #
    # Find a later additive acquisition.
    #
    tail = value[
        exception.end():
    ]

    additions = re.findall(
        rf"\b(?:buys?|bought|gets?|got|"
        rf"receives?|received|adds?|added)\s+"
        rf"({_NUMBER_PATTERN})\s+"
        rf"(?:more\s+)?",
        tail,
    )

    result = remaining

    for raw in additions:
        result = (
            result
            + _number(raw)
        )

    evidence = (
        {
            "type":
                "exception_cardinality",

            "remaining":
                remaining,

            "rule":
                (
                    "'all but N' / 'all except N' "
                    "means N remain"
                ),
        },
        {
            "type":
                "subsequent_additions",

            "values":
                [
                    _number(item)
                    for item in additions
                ],
        },
    )

    return DeterministicResult(
        solved=True,
        answer=_display(result),
        confidence=1.0,
        reason="exception_cardinality_state_transition",
        evidence=evidence,
    )


def _percentage(
    text: str,
) -> DeterministicResult | None:
    value = " ".join(
        text.strip().lower().split()
    )

    match = re.search(
        rf"\b({_NUMBER_PATTERN})\s*"
        rf"(?:percent|%)\s+of\s+"
        rf"({_NUMBER_PATTERN})\b",
        value,
    )

    if match is None:
        return None

    percent = _number(
        match.group(1)
    )

    base = _number(
        match.group(2)
    )

    result = (
        float(percent)
        / 100.0
        * float(base)
    )

    return DeterministicResult(
        solved=True,
        answer=_display(result),
        confidence=1.0,
        reason="percentage",
        evidence=(
            {
                "percent":
                    percent,

                "base":
                    base,

                "operation":
                    "percent_of",
            },
        ),
    )


def _sequence(
    text: str,
) -> DeterministicResult | None:
    value = " ".join(
        text.strip().lower().split()
    )

    start = re.search(
        rf"\bstart\s+(?:at|with)\s+"
        rf"({_NUMBER_PATTERN})\b",
        value,
    )

    if start is None:
        return None

    result: int | float = _number(
        start.group(1)
    )

    tail = value[
        start.end():
    ]

    operations = re.findall(
        rf"\b(add|subtract|multiply|divide)"
        rf"(?:\s+the\s+result)?"
        rf"(?:\s+by)?\s+"
        rf"({_NUMBER_PATTERN})\b",
        tail,
    )

    if not operations:
        return None

    evidence = []

    for operation, raw in operations:
        operand = _number(
            raw
        )

        before = result

        if operation == "add":
            result = result + operand

        elif operation == "subtract":
            result = result - operand

        elif operation == "multiply":
            result = result * operand

        elif operation == "divide":
            if operand == 0:
                return None

            result = result / operand

        evidence.append(
            {
                "operation":
                    operation,

                "operand":
                    operand,

                "before":
                    before,

                "after":
                    result,
            }
        )

    return DeterministicResult(
        solved=True,
        answer=_display(result),
        confidence=1.0,
        reason="explicit_arithmetic_sequence",
        evidence=tuple(
            evidence
        ),
    )


_ALLOWED_BINOPS = {
    ast.Add:
        operator.add,

    ast.Sub:
        operator.sub,

    ast.Mult:
        operator.mul,

    ast.Div:
        operator.truediv,
}


def _eval_expression(
    node: ast.AST,
) -> int | float:
    if isinstance(
        node,
        ast.Expression,
    ):
        return _eval_expression(
            node.body
        )

    if isinstance(
        node,
        ast.Constant,
    ):
        if isinstance(
            node.value,
            bool,
        ):
            raise ValueError(
                "boolean_not_allowed"
            )

        if isinstance(
            node.value,
            (
                int,
                float,
            ),
        ):
            return node.value

        raise ValueError(
            "constant_not_numeric"
        )

    if isinstance(
        node,
        ast.UnaryOp,
    ) and isinstance(
        node.op,
        (
            ast.UAdd,
            ast.USub,
        ),
    ):
        value = _eval_expression(
            node.operand
        )

        return (
            value
            if isinstance(
                node.op,
                ast.UAdd,
            )
            else -value
        )

    if isinstance(
        node,
        ast.BinOp,
    ):
        function = _ALLOWED_BINOPS.get(
            type(
                node.op
            )
        )

        if function is None:
            raise ValueError(
                "operator_not_allowed"
            )

        left = _eval_expression(
            node.left
        )

        right = _eval_expression(
            node.right
        )

        if (
            isinstance(
                node.op,
                ast.Div,
            )
            and right == 0
        ):
            raise ValueError(
                "division_by_zero"
            )

        return function(
            left,
            right,
        )

    raise ValueError(
        "expression_not_allowed"
    )


def _binary_expression(
    text: str,
) -> DeterministicResult | None:
    value = text.strip()

    value = re.sub(
        r"[?]+\s*$",
        "",
        value,
    ).strip()

    if not re.fullmatch(
        r"[-+*/().\d\s]+",
        value,
    ):
        return None

    try:
        tree = ast.parse(
            value,
            mode="eval",
        )

        result = _eval_expression(
            tree
        )

    except Exception:
        return None

    return DeterministicResult(
        solved=True,
        answer=_display(result),
        confidence=1.0,
        reason="restricted_arithmetic_expression",
        evidence=(
            {
                "expression":
                    value,

                "result":
                    result,
            },
        ),
    )


def solve_deterministically(
    text: str,
) -> DeterministicResult:
    """Solve only contracts we can establish exactly."""

    for solver in (
        _exception_cardinality,
        _percentage,
        _sequence,
        _binary_expression,
    ):
        result = solver(
            text
        )

        if (
            result is not None
            and result.solved
        ):
            return result

    return DeterministicResult(
        solved=False,
        answer=None,
        confidence=0.0,
        reason="no_deterministic_contract",
        evidence=(),
    )
