from __future__ import annotations

from typing import Any

from semantic.plan import (
    PlanStep,
    SemanticPlan,
)
from semantic.registry import CapabilityRegistry


class PlanValidationError(ValueError):
    pass


def validate_plan(
    raw: dict[str, Any],
    registry: CapabilityRegistry,
    *,
    provenance: dict[str, Any] | None = None,
    step_provenance_resolver=None,
) -> SemanticPlan:

    interpretation = str(
        raw.get(
            "interpretation",
            "",
        )
    )

    confidence = float(
        raw.get(
            "confidence",
            0.0,
        )
    )

    clarification_needed = bool(
        raw.get(
            "clarification_needed",
            False,
        )
    )

    clarification_question = raw.get(
        "clarification_question"
    )

    steps: list[PlanStep] = []

    for index, item in enumerate(
        raw.get(
            "steps",
            [],
        )
    ):

        if not isinstance(
            item,
            dict,
        ):
            raise PlanValidationError(
                f"step {index} is not an object"
            )

        name = str(
            item.get(
                "capability",
                "",
            )
        )

        capability = registry.get(
            name
        )

        if capability is None:
            raise PlanValidationError(
                f"unknown capability: {name}"
            )

        arguments = item.get(
            "arguments",
            {},
        )

        if not isinstance(
            arguments,
            dict,
        ):
            raise PlanValidationError(
                f"arguments for {name} must be object"
            )

        required = {
            arg.name
            for arg in capability.arguments
            if arg.required
        }

        missing = required - set(
            arguments
        )

        if missing:
            raise PlanValidationError(
                f"{name} missing required arguments: "
                + ", ".join(
                    sorted(
                        missing
                    )
                )
            )

        if step_provenance_resolver is not None:
            try:
                resolved_provenance = dict(
                    step_provenance_resolver(
                        capability=name,
                        arguments=arguments,
                        reason=str(
                            item.get(
                                "reason",
                                "",
                            )
                        ),
                    )
                    or {}
                )
            except Exception:
                #
                # Resolver failure can never upgrade authority.
                #
                resolved_provenance = dict(
                    provenance or {}
                )
        else:
            resolved_provenance = dict(
                provenance or {}
            )

        steps.append(
            PlanStep(
                capability=name,
                arguments=arguments,
                reason=str(
                    item.get(
                        "reason",
                        "",
                    )
                ),
                confidence=float(
                    item.get(
                        "confidence",
                        0.0,
                    )
                ),
                depends_on=[
                    int(x)
                    for x in item.get(
                        "depends_on",
                        [],
                    )
                ],
                provenance=resolved_provenance,
            )
        )

    return SemanticPlan(
        interpretation=interpretation,
        steps=steps,
        reply=raw.get(
            "reply"
        ),
        clarification_needed=
            clarification_needed,
        clarification_question=
            clarification_question,
        confidence=confidence,
        provenance=dict(
            provenance or {}
        ),
    )
