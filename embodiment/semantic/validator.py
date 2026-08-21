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

        raw_depends_on = item.get(
            "depends_on",
            [],
        )

        if not isinstance(
            raw_depends_on,
            list,
        ):
            raise PlanValidationError(
                f"step {index} depends_on must be an array "
                "of earlier integer step indices"
            )

        depends_on: list[int] = []

        for dependency in raw_depends_on:
            # bool is an int subclass in Python, but it is not a
            # valid semantic-plan dependency index.
            if (
                not isinstance(
                    dependency,
                    int,
                )
                or isinstance(
                    dependency,
                    bool,
                )
            ):
                raise PlanValidationError(
                    f"step {index} has invalid dependency "
                    f"{dependency!r}; depends_on must contain "
                    "integer step indices"
                )

            if dependency < 0:
                raise PlanValidationError(
                    f"step {index} dependency {dependency} "
                    "must not be negative"
                )

            if dependency >= index:
                raise PlanValidationError(
                    f"step {index} dependency {dependency} "
                    "must reference an earlier step"
                )

            depends_on.append(
                dependency
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
                depends_on=depends_on,
                provenance=resolved_provenance,
            )
        )

    raw_reply = raw.get(
        "reply"
    )

    #
    # A semantic plan must choose exactly one answer path.
    #
    # When capability execution is requested, the planner may not
    # pre-claim a user-facing answer. The final grounded answer is
    # synthesized only after those capabilities actually execute.
    #
    # This also catches a common small-model failure mode where the
    # model invents an unnecessary capability while simultaneously
    # answering the question from its own reasoning.
    #
    if steps:
        if (
            raw_reply is not None
            and str(
                raw_reply
            ).strip()
        ):
            raise PlanValidationError(
                "semantic plan mixes capability execution "
                "with a direct reply; plans with steps must "
                "set reply to null"
            )

    return SemanticPlan(
        interpretation=interpretation,
        steps=steps,
        reply=raw_reply,
        clarification_needed=
            clarification_needed,
        clarification_question=
            clarification_question,
        confidence=confidence,
        provenance=dict(
            provenance or {}
        ),
    )
