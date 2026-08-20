from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


HERE = Path(
    __file__
).resolve()

EMB = HERE.parents[1]

sys.path.insert(
    0,
    str(EMB),
)

from integration.bindings import (
    bind_local_capabilities,
)

from integration.sophyane_planner import (
    SophyaneCapabilityPlanner,
)

from semantic.context import (
    SemanticContext,
    default_context_provenance,
)

from semantic.executor import (
    CapabilityExecutor,
)

from semantic.prompt import (
    build_planner_prompt,
)

from semantic.registry import (
    build_default_registry,
)

from semantic.validator import (
    validate_plan,
)
from runtime.security_provenance import (
    semantic_context_execution_provenance,
)
from runtime.semantic_dependency_resolver import (
    derive_step_provenance,
)


def load_json(
    path: Path,
) -> dict:

    if not path.exists():
        return {}

    try:
        x = json.loads(
            path.read_text(
                encoding="utf-8",
            )
        )

        return (
            x
            if isinstance(
                x,
                dict,
            )
            else {}
        )

    except Exception:
        return {}


def main() -> int:

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "utterance",
        nargs="+",
    )

    parser.add_argument(
        "--plan-only",
        action="store_true",
    )

    args = parser.parse_args()

    utterance = " ".join(
        args.utterance
    )

    registry = (
        build_default_registry()
    )

    registry = (
        bind_local_capabilities(
            registry
        )
    )

    runtime_state = load_json(
        EMB
        / "runtime"
        / "state.json"
    )

    context = SemanticContext(
        user_utterance=
            utterance,

        current_task=
            runtime_state.get(
                "task"
            ),

        current_application=
            runtime_state
            .get(
                "screen",
                {}
            )
            .get(
                "application"
            ),

        screen=
            runtime_state.get(
                "screen",
                {},
            ),

        perception=
            runtime_state.get(
                "presence",
                {},
            ),

        avatar={
            "animation":
                runtime_state.get(
                    "avatar",
                    {},
                ),

            "appearance":
                runtime_state.get(
                    "appearance",
                    {},
                ),
        },

        identity=
            runtime_state.get(
                "identity",
                {},
            ),
        provenance=
            default_context_provenance(),
    )

    planner = (
        SophyaneCapabilityPlanner()
    )

    raw = planner.plan(
        user_message=utterance,
        capabilities=registry.describe(),
        context=context.to_dict(),
    )

    routing = raw.pop(
        "_routing",
        {},
    )

    fallback_provenance = (
        semantic_context_execution_provenance(
            context
        )
    )

    fallback_dict = (
        fallback_provenance
        .permissions.__dict__
        | {
            "origin":
                fallback_provenance.origin.value
        }
    )

    def resolve_step_provenance(
        *,
        capability,
        arguments,
        reason,
    ):
        resolved = derive_step_provenance(
            context=context,
            capability=capability,
            arguments=arguments,
            reason=reason,
        )

        return (
            resolved.permissions.__dict__
            | {
                "origin":
                    resolved.origin.value,
                "source_ids":
                    list(
                        resolved.source_ids
                    ),
                "transformed":
                    resolved.transformed,
            }
        )

    plan = validate_plan(
        raw,
        registry,
        provenance=fallback_dict,
        step_provenance_resolver=
            resolve_step_provenance,
    )

    result = {
        "ok":
            True,

        "routing":
            routing,

        "plan":
            plan.to_dict(),
    }

    if not args.plan_only:

        executor = (
            CapabilityExecutor(
                registry
            )
        )

        result[
            "execution"
        ] = executor.execute(
            plan
        )

    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
