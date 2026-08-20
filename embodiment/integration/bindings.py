from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from desktop.windows_bridge import WindowsBridge
from perception.vision_client import VisionClient
from runtime.security_boundary import (
    InformationPermission,
    default_security_boundary,
)
from integration.sophyane_visual_memory import (
    SophyaneVisualMemory,
    VisualChunkInput,
)
from semantic.registry import CapabilityRegistry


STATE_PATH = Path(
    r"""/home/badrpk/neuron/embodiment/runtime/state.json"""
)


def _load_runtime_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {}

    try:
        value = json.loads(
            STATE_PATH.read_text()
        )
    except Exception:
        return {}

    if not isinstance(
        value,
        dict,
    ):
        return {}

    return value


def _save_runtime_state(
    state: dict[str, Any],
) -> None:
    STATE_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temp = STATE_PATH.with_suffix(
        STATE_PATH.suffix + ".tmp"
    )

    temp.write_text(
        json.dumps(
            state,
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )

    temp.replace(
        STATE_PATH
    )


def _persist_screen_observation(
    observation: dict[str, Any],
) -> dict[str, Any]:
    state = _load_runtime_state()

    screen = state.get(
        "screen",
    )

    if not isinstance(
        screen,
        dict,
    ):
        screen = {}

    if observation.get(
        "ok"
    ):
        screen.update(
            {
                "grounded":
                    True,

                "provider":
                    observation.get(
                        "provider",
                        "nifdu.screen",
                    ),

                "application":
                    observation.get(
                        "application",
                        "",
                    ),

                "window_title":
                    observation.get(
                        "window_title",
                        "",
                    ),

                "process_id":
                    observation.get(
                        "process_id",
                    ),

                "window_handle":
                    observation.get(
                        "window_handle",
                    ),

                "bounds":
                    observation.get(
                        "bounds",
                    ),

                "screen_bounds":
                    observation.get(
                        "screen_bounds",
                    ),

                "screenshot_path":
                    observation.get(
                        "screenshot_path",
                        "",
                    ),

                "screenshot_format":
                    observation.get(
                        "screenshot_format",
                        "png",
                    ),

                "screenshot_bytes":
                    observation.get(
                        "screenshot_bytes",
                        0,
                    ),
            }
        )
    else:
        screen.update(
            {
                "grounded":
                    False,

                "provider":
                    observation.get(
                        "provider",
                        "nifdu.screen",
                    ),

                "last_error":
                    observation.get(
                        "stderr",
                        "",
                    ),
            }
        )

    state["screen"] = screen

    _save_runtime_state(
        state
    )

    return screen


def _describe_grounded_screen(
    screen: dict[str, Any],
) -> dict[str, Any]:
    if not screen.get(
        "grounded"
    ):
        return {
            "ok":
                False,

            "capability":
                "screen.describe",

            "provider":
                "nifdu.screen",

            "status":
                "no_grounded_screen_observation",

            "description":
                "",

            "screen":
                screen,
        }

    application = str(
        screen.get(
            "application",
            "",
        )
        or ""
    )

    title = str(
        screen.get(
            "window_title",
            "",
        )
        or ""
    )

    bounds = (
        screen.get(
            "screen_bounds"
        )
        or
        {}
    )

    width = bounds.get(
        "width"
    )

    height = bounds.get(
        "height"
    )

    parts: list[str] = []

    if application:
        parts.append(
            f"The active application is {application}."
        )

    if title:
        parts.append(
            f"The active window title is {title}."
        )

    if width and height:
        parts.append(
            "The captured desktop is "
            f"{width} by {height} pixels."
        )

    screenshot_path = str(
        screen.get(
            "screenshot_path",
            "",
        )
        or ""
    )

    if screenshot_path:
        parts.append(
            "A grounded PNG screenshot is available "
            f"at {screenshot_path}."
        )

    description = " ".join(
        parts
    ).strip()

    return {
        "ok":
            True,

        "capability":
            "screen.describe",

        "provider":
            "nifdu.screen",

        "grounded":
            True,

        "description":
            description,

        "application":
            application,

        "window_title":
            title,

        "screen_bounds":
            bounds,

        "screenshot_path":
            screenshot_path,

        "screenshot_bytes":
            screen.get(
                "screenshot_bytes",
                0,
            ),
    }


def bind_local_capabilities(
    registry: CapabilityRegistry,
) -> CapabilityRegistry:

    desktop = WindowsBridge()

    launch = registry.get(
        "desktop.launch"
    )

    if launch is not None:

        def do_launch(args):
            result = desktop.launch_app(
                str(
                    args.get(
                        "application",
                        "",
                    )
                )
            )

            return result.to_dict()

        launch.executor = do_launch

    open_url = registry.get(
        "desktop.open_url"
    )

    if open_url is not None:

        def do_open_url(args):
            result = desktop.open_url(
                str(
                    args.get(
                        "url",
                        "",
                    )
                )
            )

            return result.to_dict()

        open_url.executor = do_open_url

    screen_observe = registry.get(
        "screen.observe"
    )

    if screen_observe is not None:

        def do_screen_observe(args):
            del args

            result = desktop.observe_screen()

            output = result.to_dict()

            output["screen_state"] = (
                _persist_screen_observation(
                    output
                )
            )

            return output

        screen_observe.executor = do_screen_observe

    screen_describe = registry.get(
        "screen.describe"
    )

    if screen_describe is not None:

        def do_screen_describe(args):
            del args

            state = _load_runtime_state()

            screen = state.get(
                "screen",
                {},
            )

            if not isinstance(
                screen,
                dict,
            ):
                screen = {}

            return _describe_grounded_screen(
                screen
            )

        screen_describe.executor = do_screen_describe

    screen_visual_question = registry.get(
        "screen.visual_question"
    )

    if screen_visual_question is not None:

        vision = VisionClient(
            host="127.0.0.1",
            port=8769,
        )

        def do_screen_visual_question(args):
            question = str(
                args.get(
                    "question",
                    "",
                )
                or ""
            ).strip()

            if not question:
                return {
                    "ok":
                        False,

                    "capability":
                        "screen.visual_question",

                    "provider":
                        "neuron.vision",

                    "status":
                        "invalid_question",

                    "answer":
                        "",

                    "error":
                        "question is required",
                }

            #
            # Always acquire fresh pixels for a visual question.
            # Never silently use a stale screenshot.
            #

            observation = (
                desktop.observe_screen()
            )

            observed = (
                observation.to_dict()
            )

            if not observed.get(
                "ok"
            ):
                _persist_screen_observation(
                    observed
                )

                return {
                    "ok":
                        False,

                    "capability":
                        "screen.visual_question",

                    "provider":
                        "neuron.vision",

                    "question":
                        question,

                    "answer":
                        "",

                    "status":
                        "screen_observation_failed",

                    "error":
                        observed.get(
                            "stderr",
                            "screen observation failed",
                        ),
                }

            _persist_screen_observation(
                observed
            )

            screenshot_path = str(
                observed.get(
                    "screenshot_path",
                    "",
                )
                or ""
            )

            result = vision.ask_image(
                screenshot_path,
                question,
            )

            output = result.to_dict()

            #
            # NEURON_SOPHYANE_VISUAL_MEMORY_V5
            #
            # Only successful grounded visual perception becomes
            # durable semantic memory.
            #
            grounded_answer = str(
                output.get(
                    "answer",
                    "",
                )
                or ""
            ).strip()

            if (
                output.get("ok") is True
                and output.get("status")
                    == "grounded_visual_answer"
                and grounded_answer
            ):
                try:
                    memory = SophyaneVisualMemory()

                    latest = (
                        memory.latest_visual_chunks(
                            limit=1
                        )
                    )

                    previous_chunk_id = (
                        latest[-1].id
                        if latest
                        else ""
                    )

                    persistence_security = (
                        default_security_boundary()
                        .authorize(
                            source_text=grounded_answer,
                            permission=(
                                InformationPermission.PERSIST
                            ),
                        )
                    )

                    if not persistence_security.allowed:
                        return {
                            "ok": True,
                            "capability":
                                "screen.visual_question",
                            "status":
                                "grounded_visual_answer",
                            "answer": grounded_answer,
                            "memory_written": False,
                            "memory_security_reason":
                                persistence_security.reason,
                        }

                    chunk = memory.remember(
                        VisualChunkInput(
                            screenshot_path=(
                                screenshot_path
                            ),
                            description=grounded_answer,
                            timestamp=float(
                                observed.get(
                                    "captured_at",
                                    observed.get(
                                        "timestamp",
                                        0.0,
                                    ),
                                )
                                or 0.0
                            ),
                            application=str(
                                observed.get(
                                    "application",
                                    "",
                                )
                                or ""
                            ),
                            window_title=str(
                                observed.get(
                                    "window_title",
                                    "",
                                )
                                or ""
                            ),
                            previous_chunk_id=(
                                previous_chunk_id
                            ),
                        )
                    )

                    output[
                        "sophyane_visual_memory"
                    ] = {
                        "ok": True,
                        "chunk_id": chunk.id,
                        "modality": "visual",
                        "vector_backend": (
                            memory.store
                            .embedder
                            .description
                        ),
                    }

                except Exception as exc:
                    output[
                        "sophyane_visual_memory"
                    ] = {
                        "ok": False,
                        "error": str(exc),
                    }

            output["screen_observation"] = {
                "application":
                    observed.get(
                        "application",
                        "",
                    ),

                "window_title":
                    observed.get(
                        "window_title",
                        "",
                    ),

                "screen_bounds":
                    observed.get(
                        "screen_bounds",
                    ),

                "screenshot_bytes":
                    observed.get(
                        "screenshot_bytes",
                        0,
                    ),
            }

            return output

        screen_visual_question.executor = (
            do_screen_visual_question
        )

    return registry
