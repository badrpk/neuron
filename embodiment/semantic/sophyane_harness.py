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

    plan = validate_plan(
        raw,
        registry,
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
