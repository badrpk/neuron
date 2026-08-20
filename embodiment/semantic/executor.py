from __future__ import annotations

from typing import Any

from semantic.plan import SemanticPlan
from runtime.security_boundary import (
    InformationPermission,
    default_security_boundary,
)
from semantic.registry import CapabilityRegistry


class CapabilityExecutor:
    def __init__(
        self,
        registry: CapabilityRegistry,
    ) -> None:

        self.registry = registry

    def execute(
        self,
        plan: SemanticPlan,
    ) -> list[dict[str, Any]]:

        results = []

        for index, step in enumerate(
            plan.steps
        ):

            capability = self.registry.get(
                step.capability
            )

            if capability is None:
                results.append(
                    {
                        "step": index,
                        "ok": False,
                        "capability":
                            step.capability,
                        "error":
                            "capability unavailable",
                    }
                )
                continue

            #
            # Semantic planning is active now.
            #
            # Actual providers are attached incrementally.
            #
            # Never pretend an unbound provider executed.
            #

            if capability.executor is None:

                results.append(
                    {
                        "step": index,
                        "ok": False,
                        "capability":
                            step.capability,
                        "provider":
                            capability.provider,
                        "status":
                            "provider_not_bound",
                        "arguments":
                            step.arguments,
                    }
                )

                continue

            try:

                provenance = dict(
                    getattr(
                        step,
                        "provenance",
                        {},
                    )
                    or {}
                )

                if not provenance.get(
                    "execute",
                    False,
                ):
                    results.append(
                        {
                            "step": index,
                            "ok": False,
                            "capability":
                                step.capability,
                            "provider":
                                capability.provider,
                            "error":
                                "security_denied",
                            "security_reason":
                                "provenance_denied",
                        }
                    )
                    continue

                source_text = (
                    str(
                        getattr(
                            plan,
                            "interpretation",
                            "",
                        )
                        or ""
                    )
                )

                if not source_text:
                    source_text = str(
                        step.reason or ""
                    )

                gate = default_security_boundary()

                security = gate.authorize(
                    source_text=source_text,
                    permission=(
                        InformationPermission.EXECUTE
                    ),
                )

                if not security.allowed:
                    results.append(
                        {
                            "ok": False,
                            "capability":
                                step.capability,
                            "provider":
                                capability.provider,
                            "error":
                                "security_denied",
                            "security_reason":
                                security.reason,
                            "security_decision":
                                security.assessment.decision,
                        }
                    )
                    continue

                outcome = capability.executor(
                    step.arguments
                )

                results.append(
                    {
                        "step": index,
                        "ok": True,
                        "capability":
                            step.capability,
                        "provider":
                            capability.provider,
                        "result":
                            outcome,
                    }
                )

            except Exception as exc:

                results.append(
                    {
                        "step": index,
                        "ok": False,
                        "capability":
                            step.capability,
                        "provider":
                            capability.provider,
                        "error":
                            str(exc),
                    }
                )

        return results
