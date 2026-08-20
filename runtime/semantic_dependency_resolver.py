from __future__ import annotations

import json
import re
from typing import Any

from runtime.security_provenance import (
    semantic_step_execution_provenance,
)


_SCREEN_REFERENCES = (
    r"\bscreen\b",
    r"\bvisible\b",
    r"\bshown\b",
    r"\bdisplayed\b",
    r"\bpage\b",
    r"\bwindow\b",
    r"\bbutton\b",
    r"\blink\b",
    r"\bthere\b",
    r"\bit\b",
    r"\bthat\b",
    r"\bthis\b",
    r"\bthese\b",
    r"\bthose\b",
    r"\bwhat you see\b",
    r"\bwhat is visible\b",
    r"\bwhatever (?:is|appears)\b",
)

_MEMORY_REFERENCES = (
    r"\bremember\b",
    r"\bmemory\b",
    r"\bprevious(?:ly)?\b",
    r"\bearlier\b",
    r"\bstored\b",
    r"\blast time\b",
    r"\bfrom before\b",
)

_PERCEPTION_REFERENCES = (
    r"\bperson\b",
    r"\bpeople\b",
    r"\bface\b",
    r"\bcamera\b",
    r"\bpresence\b",
    r"\bwho is\b",
    r"\bwho's\b",
)


def _matches_any(
    text: str,
    patterns: tuple[str, ...],
) -> bool:
    return any(
        re.search(
            pattern,
            text,
            re.IGNORECASE,
        )
        for pattern in patterns
    )


def _normalized_words(
    value: str,
) -> set[str]:
    return {
        token.lower()
        for token in re.findall(
            r"[A-Za-z0-9._:/-]+",
            value,
        )
        if len(token) >= 2
    }


def _argument_strings(
    value: Any,
):
    if isinstance(value, str):
        if value.strip():
            yield value.strip()
        return

    if isinstance(value, dict):
        for child in value.values():
            yield from _argument_strings(
                child
            )
        return

    if isinstance(value, (list, tuple)):
        for child in value:
            yield from _argument_strings(
                child
            )


def _arguments_supported_by_user(
    *,
    user_text: str,
    arguments: dict,
) -> bool:
    """
    Conservative evidence check.

    Model-generated arguments cannot CREATE authority.

    If meaningful string arguments introduce information absent
    from the user's utterance while external context is available,
    Neuron treats that step as potentially context-derived.

    Empty/non-string arguments do not by themselves cause taint.
    """

    argument_values = tuple(
        _argument_strings(arguments)
    )

    if not argument_values:
        return True

    user_lower = user_text.lower()
    user_words = _normalized_words(
        user_text
    )

    for value in argument_values:
        value_lower = value.lower()

        #
        # Exact phrase directly supplied by user.
        #
        if value_lower in user_lower:
            continue

        value_words = _normalized_words(
            value
        )

        if (
            value_words
            and value_words.issubset(
                user_words
            )
        ):
            continue

        return False

    return True


def _substantive(
    value,
) -> bool:
    if value in (
        None,
        "",
        {},
        [],
        (),
    ):
        return False

    try:
        rendered = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
        )
    except Exception:
        rendered = str(value)

    return rendered.strip() not in {
        "",
        "{}",
        "[]",
        "null",
    }


def resolve_step_source_dependencies(
    *,
    context,
    capability: str,
    arguments: dict,
    reason: str = "",
) -> tuple[str, ...]:
    """
    Resolve dependencies using Neuron-owned policy.

    IMPORTANT:
      `reason` is deliberately ignored for authority decisions.

    It remains in the signature for compatibility/observability,
    but model-generated reasoning can never grant authority.
    """

    del capability
    del reason

    user_text = str(
        getattr(
            context,
            "user_utterance",
            "",
        )
        or ""
    )

    screen = getattr(
        context,
        "screen",
        {},
    )

    perception = getattr(
        context,
        "perception",
        {},
    )

    memory = getattr(
        context,
        "memory",
        {},
    )

    dependencies = [
        "user_utterance",
    ]

    #
    # Explicit user references to external context.
    #
    if (
        _substantive(screen)
        and _matches_any(
            user_text,
            _SCREEN_REFERENCES,
        )
    ):
        dependencies.append(
            "screen"
        )

    if (
        _substantive(memory)
        and _matches_any(
            user_text,
            _MEMORY_REFERENCES,
        )
    ):
        dependencies.append(
            "memory"
        )

    if (
        _substantive(perception)
        and _matches_any(
            user_text,
            _PERCEPTION_REFERENCES,
        )
    ):
        dependencies.append(
            "perception"
        )

    #
    # If the model introduces action arguments not supported
    # by the user's words, external context may have supplied
    # them.
    #
    arguments_supported = (
        _arguments_supported_by_user(
            user_text=user_text,
            arguments=arguments,
        )
    )

    if not arguments_supported:
        if _substantive(screen):
            dependencies.append(
                "screen"
            )

        if _substantive(perception):
            dependencies.append(
                "perception"
            )

        if _substantive(memory):
            dependencies.append(
                "memory"
            )

        #
        # No known external source explains the unsupported
        # argument. Mark it unknown so authority fails closed.
        #
        if len(dependencies) == 1:
            dependencies.append(
                "unknown_model_argument"
            )

    return tuple(
        dict.fromkeys(
            dependencies
        )
    )


def derive_step_provenance(
    *,
    context,
    capability: str,
    arguments: dict,
    reason: str = "",
):
    dependencies = (
        resolve_step_source_dependencies(
            context=context,
            capability=capability,
            arguments=arguments,
            reason=reason,
        )
    )

    return (
        semantic_step_execution_provenance(
            context,
            source_dependencies=
                dependencies,
        )
    )
