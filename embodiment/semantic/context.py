from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class SemanticContext:
    user_utterance: str = ""

    conversation_summary: str = ""

    current_task: str | None = None

    current_application: str | None = None

    screen: dict[str, Any] = field(
        default_factory=dict
    )

    perception: dict[str, Any] = field(
        default_factory=dict
    )

    avatar: dict[str, Any] = field(
        default_factory=dict
    )

    identity: dict[str, Any] = field(
        default_factory=dict
    )

    memory: dict[str, Any] = field(
        default_factory=dict
    )

    recent_actions: list[dict[str, Any]] = field(
        default_factory=list
    )

    provenance: dict[str, dict[str, object]] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def default_context_provenance() -> dict[str, dict[str, object]]:
    """
    Authority metadata created by Neuron itself.

    This metadata is never accepted from planner/model output.
    """
    return {
        "user_utterance": {
            "origin": "user",
            "read": True,
            "trust": True,
            "persist": True,
            "execute": True,
            "propagate": True,
        },
        "screen": {
            "origin": "screen",
            "read": True,
            "trust": False,
            "persist": True,
            "execute": False,
            "propagate": False,
        },
        "perception": {
            "origin": "external",
            "read": True,
            "trust": False,
            "persist": True,
            "execute": False,
            "propagate": False,
        },
        "memory": {
            "origin": "memory",
            "read": True,
            "trust": False,
            "persist": False,
            "execute": False,
            "propagate": False,
        },
    }
