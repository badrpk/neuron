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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
