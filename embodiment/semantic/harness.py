from __future__ import annotations

import argparse
import json
import os
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

from integration.bindings import bind_local_capabilities
from semantic.context import SemanticContext
from semantic.executor import CapabilityExecutor
from semantic.model_adapter import from_environment
from semantic.prompt import build_planner_prompt
from semantic.registry import build_default_registry
from semantic.validator import validate_plan


def load_state() -> dict:

    path = (
        EMB
        / "runtime"
        / "state.json"
    )

    if not path.exists():
        return {}

    try:
        return json.loads(
            path.read_text(
                encoding="utf-8"
            )
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

    state = load_state()

    registry = (
        build_default_registry()
    )

    registry = bind_local_capabilities(
        registry
    )

    context = SemanticContext(
        user_utterance=utterance,
        current_task=state.get(
            "task"
        ),
        current_application=(
            state
            .get(
                "screen",
                {}
            )
            .get(
                "application"
            )
        ),
        screen=state.get(
            "screen",
            {},
        ),
        perception=state.get(
            "presence",
            {},
        ),
        avatar={
            "animation":
                state.get(
                    "avatar",
                    {}
                ),
            "appearance":
                state.get(
                    "appearance",
                    {}
                ),
        },
        identity=state.get(
            "identity",
            {},
        ),
    )

    prompt = build_planner_prompt(
        context,
        registry,
    )

    planner = from_environment()

    if planner is None:

        print(
            json.dumps(
                {
                    "ok": False,
                    "status":
                        "semantic_model_not_configured",

                    "message":
                        (
                            "Set NEURON_SEMANTIC_BASE_URL "
                            "and NEURON_SEMANTIC_MODEL to an "
                            "authoritative local NIFDU/Sophyane/Qwen "
                            "OpenAI-compatible endpoint after discovery."
                        ),

                    "capability_count":
                        len(
                            registry.all()
                        ),

                    "utterance":
                        utterance,

                    "prompt_path":
                        str(
                            EMB
                            / "runtime"
                            / "last-semantic-prompt.txt"
                        ),
                },
                indent=2,
            )
        )

        (
            EMB
            / "runtime"
            / "last-semantic-prompt.txt"
        ).write_text(
            prompt,
            encoding="utf-8",
        )

        return 3

    raw = planner.plan(
        prompt
    )

    plan = validate_plan(
        raw,
        registry,
    )

    output = {
        "ok": True,
        "plan":
            plan.to_dict(),
    }

    if not args.plan_only:

        executor = CapabilityExecutor(
            registry
        )

        output[
            "execution"
        ] = executor.execute(
            plan
        )

    print(
        json.dumps(
            output,
            indent=2,
            ensure_ascii=False,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
