from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Callable


@dataclass
class CapabilityArgument:
    name: str
    description: str
    type: str = "string"
    required: bool = False


@dataclass
class Capability:
    name: str

    description: str

    provider: str

    arguments: list[CapabilityArgument] = field(
        default_factory=list
    )

    effects: list[str] = field(
        default_factory=list
    )

    requires: list[str] = field(
        default_factory=list
    )

    privilege: str = "routine"

    executor: Callable[
        [dict[str, Any]],
        dict[str, Any],
    ] | None = field(
        default=None,
        repr=False,
    )

    def public_dict(self) -> dict[str, Any]:
        x = asdict(self)
        x.pop(
            "executor",
            None,
        )
        return x
