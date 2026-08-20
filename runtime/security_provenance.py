from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable


class ProvenanceOrigin(str, Enum):
    USER = "user"
    SCREEN = "screen"
    EXTERNAL = "external"
    MEMORY = "memory"
    MODEL = "model"
    SYSTEM = "system"


@dataclass(frozen=True)
class ProvenancePermissions:
    read: bool = True
    trust: bool = False
    persist: bool = False
    execute: bool = False
    propagate: bool = False

    def intersect(
        self,
        other: "ProvenancePermissions",
    ) -> "ProvenancePermissions":
        """
        Authority composition is monotonic.

        A derived value receives only permissions held by
        every contributing parent.
        """
        return ProvenancePermissions(
            read=self.read and other.read,
            trust=self.trust and other.trust,
            persist=self.persist and other.persist,
            execute=self.execute and other.execute,
            propagate=(
                self.propagate
                and other.propagate
            ),
        )


@dataclass(frozen=True)
class SecurityProvenance:
    origin: ProvenanceOrigin

    permissions: ProvenancePermissions = field(
        default_factory=ProvenancePermissions
    )

    source_ids: tuple[str, ...] = ()

    transformed: bool = False

    def derive(
        self,
        *,
        origin: ProvenanceOrigin = ProvenanceOrigin.MODEL,
        source_id: str = "",
    ) -> "SecurityProvenance":
        ids = list(self.source_ids)

        if source_id:
            ids.append(source_id)

        return SecurityProvenance(
            origin=origin,
            permissions=self.permissions,
            source_ids=tuple(dict.fromkeys(ids)),
            transformed=True,
        )


def combine_provenance(
    parents: Iterable[SecurityProvenance],
    *,
    origin: ProvenanceOrigin = ProvenanceOrigin.MODEL,
) -> SecurityProvenance:
    parents = tuple(parents)

    if not parents:
        return SecurityProvenance(
            origin=origin,
        )

    permissions = parents[0].permissions

    source_ids: list[str] = []

    for parent in parents:
        permissions = permissions.intersect(
            parent.permissions
        )

        source_ids.extend(parent.source_ids)

    return SecurityProvenance(
        origin=origin,
        permissions=permissions,
        source_ids=tuple(
            dict.fromkeys(source_ids)
        ),
        transformed=True,
    )


def external_observation(
    *,
    source_id: str = "",
) -> SecurityProvenance:
    """
    External information may be observed and retained as
    untrusted evidence, but cannot itself authorize actions.
    """
    return SecurityProvenance(
        origin=ProvenanceOrigin.EXTERNAL,
        permissions=ProvenancePermissions(
            read=True,
            trust=False,
            persist=True,
            execute=False,
            propagate=False,
        ),
        source_ids=(
            (source_id,)
            if source_id
            else ()
        ),
    )


def trusted_user_instruction(
    *,
    source_id: str = "",
) -> SecurityProvenance:
    return SecurityProvenance(
        origin=ProvenanceOrigin.USER,
        permissions=ProvenancePermissions(
            read=True,
            trust=True,
            persist=True,
            execute=True,
            propagate=False,
        ),
        source_ids=(
            (source_id,)
            if source_id
            else ()
        ),
    )


def semantic_context_execution_provenance(
    context,
):
    """
    Conservative V1 authority derivation for semantic planning.

    Explicit user text starts trusted, but executable authority is
    removed when the current semantic context contains substantive
    external screen/perception/memory text that could influence the
    planner.

    This intentionally prefers false negatives over provenance
    laundering until step-level information-flow tracking exists.
    """
    user = trusted_user_instruction(
        source_id="semantic:user"
    )

    external_present = False

    for value in (
        getattr(context, "screen", {}),
        getattr(context, "perception", {}),
        getattr(context, "memory", {}),
    ):
        if not value:
            continue

        text = str(value).strip()

        if text and text not in {
            "{}",
            "[]",
        }:
            external_present = True
            break

    if not external_present:
        return user

    return combine_provenance(
        [
            user,
            external_observation(
                source_id="semantic:external-context"
            ),
        ],
        origin=ProvenanceOrigin.MODEL,
    )


def _semantic_source_provenance(
    source_name: str,
) -> SecurityProvenance:
    """
    Convert a Neuron-owned semantic source identifier into
    immutable authority.

    Unknown sources fail closed.
    """

    if source_name == "user_utterance":
        return trusted_user_instruction(
            source_id="semantic:user"
        )

    if source_name == "screen":
        return external_observation(
            source_id="semantic:screen"
        )

    if source_name == "perception":
        return external_observation(
            source_id="semantic:perception"
        )

    if source_name == "memory":
        return SecurityProvenance(
            origin=ProvenanceOrigin.MEMORY,
            permissions=ProvenancePermissions(
                read=True,
                trust=False,
                persist=False,
                execute=False,
                propagate=False,
            ),
            source_ids=("semantic:memory",),
        )

    #
    # Unknown/model-invented source.
    #
    return SecurityProvenance(
        origin=ProvenanceOrigin.MODEL,
        permissions=ProvenancePermissions(
            read=True,
            trust=False,
            persist=False,
            execute=False,
            propagate=False,
        ),
        source_ids=(
            f"semantic:unknown:{source_name}",
        ),
    )


def semantic_step_execution_provenance(
    context,
    *,
    source_dependencies,
) -> SecurityProvenance:
    """
    V2 step-scoped authority derivation.

    Authority is derived exclusively from Neuron-owned source
    classes. The planner may never supply permission bits.

    Empty dependency information fails closed.
    """

    dependencies = tuple(
        dict.fromkeys(
            str(item)
            for item in source_dependencies
            if str(item)
        )
    )

    if not dependencies:
        return SecurityProvenance(
            origin=ProvenanceOrigin.MODEL,
            permissions=ProvenancePermissions(
                read=True,
                trust=False,
                persist=False,
                execute=False,
                propagate=False,
            ),
            source_ids=("semantic:missing-dependency",),
        )

    parents = [
        _semantic_source_provenance(name)
        for name in dependencies
    ]

    if len(parents) == 1:
        return parents[0].derive(
            source_id="semantic:step"
        )

    return combine_provenance(
        parents,
        origin=ProvenanceOrigin.MODEL,
    )
