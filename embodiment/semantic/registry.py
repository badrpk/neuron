from __future__ import annotations

from typing import Any

from semantic.capability import (
    Capability,
    CapabilityArgument,
)


class CapabilityRegistry:
    def __init__(self) -> None:
        self._items: dict[
            str,
            Capability,
        ] = {}

    def register(
        self,
        capability: Capability,
    ) -> None:

        if not capability.name:
            raise ValueError(
                "capability name required"
            )

        self._items[
            capability.name
        ] = capability

    def get(
        self,
        name: str,
    ) -> Capability | None:

        return self._items.get(
            name
        )

    def all(
        self,
    ) -> list[Capability]:

        return list(
            self._items.values()
        )

    def describe(
        self,
    ) -> list[dict[str, Any]]:

        return [
            x.public_dict()
            for x in self.all()
        ]


def build_default_registry() -> CapabilityRegistry:

    r = CapabilityRegistry()

    #
    # SCREEN
    #

    r.register(
        Capability(
            name="screen.observe",
            description=(
                "Observe the current computer screen and return "
                "grounded information about visible content, "
                "active application, text regions, images, and controls."
            ),
            provider="nifdu.screen",
            effects=[
                "screen_state_updated",
            ],
        )
    )

    r.register(
        Capability(
            name="screen.read.start",
            description=(
                "Begin reading visible document or textual screen "
                "content from an appropriate current position."
            ),
            provider="neuron.screen",
            arguments=[
                CapabilityArgument(
                    name="position",
                    description=(
                        "Optional semantic starting position such as "
                        "current, beginning, visible section, or a "
                        "model-resolved location."
                    ),
                    required=False,
                )
            ],
            effects=[
                "reading_session_started",
            ],
        )
    )

    r.register(
        Capability(
            name="screen.read.advance",
            description=(
                "Advance the current reading position by a semantic "
                "unit such as sentence, paragraph, section, or page."
            ),
            provider="neuron.screen",
            arguments=[
                CapabilityArgument(
                    name="unit",
                    description=(
                        "Semantic reading unit."
                    ),
                    required=False,
                ),
                CapabilityArgument(
                    name="count",
                    description=(
                        "Number of units to advance."
                    ),
                    type="integer",
                    required=False,
                ),
            ],
            effects=[
                "reading_cursor_changed",
            ],
        )
    )

    r.register(
        Capability(
            name="screen.read.repeat",
            description=(
                "Repeat an appropriate previously spoken portion "
                "of the active reading session."
            ),
            provider="neuron.screen",
            effects=[
                "reading_cursor_revisited",
            ],
        )
    )

    r.register(
        Capability(
            name="screen.describe",
            description=(
                "Explain visible screen content using grounded "
                "screen perception, including text, images, charts, "
                "application state, and spatial relationships."
            ),
            provider="nifdu.screen",
        )
    )

    r.register(
        Capability(
            name="screen.visual_question",
            description=(
                "Answer a natural-language question about an image, "
                "photo, chart, diagram, or selected visual region "
                "currently visible on the computer screen."
            ),
            provider="neuron.vision",
            arguments=[
                CapabilityArgument(
                    name="question",
                    description=(
                        "Question to answer about the visible visual content."
                    ),
                    required=True,
                )
            ],
        )
    )

    #
    # AVATAR
    #

    r.register(
        Capability(
            name="avatar.inspect",
            description=(
                "Inspect Neuron's current avatar appearance and "
                "animation state."
            ),
            provider="neuron.avatar",
        )
    )

    r.register(
        Capability(
            name="avatar.modify",
            description=(
                "Modify one or more avatar appearance attributes "
                "based on semantic user intent. Attributes may include "
                "skin tone, warmth, geometry, hair, eyes, expression, "
                "age styling, or other renderer-supported properties."
            ),
            provider="neuron.avatar",
            arguments=[
                CapabilityArgument(
                    name="changes",
                    description=(
                        "Structured appearance changes inferred from "
                        "the user's language and conversational context."
                    ),
                    type="object",
                    required=True,
                )
            ],
            effects=[
                "avatar_appearance_changed",
            ],
        )
    )

    r.register(
        Capability(
            name="avatar.research_reference",
            description=(
                "Research public visual references relevant to an "
                "avatar appearance request and derive visual traits "
                "for creation of an original avatar."
            ),
            provider="sophyane.research",
            arguments=[
                CapabilityArgument(
                    name="reference",
                    description=(
                        "Person, style, era, artwork, or visual concept "
                        "used as inspiration."
                    ),
                    required=True,
                )
            ],
            effects=[
                "reference_traits_available",
            ],
        )
    )

    r.register(
        Capability(
            name="avatar.generate",
            description=(
                "Generate or regenerate an original Neuron avatar asset "
                "from an appearance specification and optional "
                "reference-derived traits."
            ),
            provider="comfyui",
            arguments=[
                CapabilityArgument(
                    name="appearance_spec",
                    description=(
                        "Structured visual specification."
                    ),
                    type="object",
                    required=True,
                )
            ],
            effects=[
                "avatar_asset_generated",
            ],
        )
    )

    #
    # DESKTOP
    #

    r.register(
        Capability(
            name="desktop.launch",
            description=(
                "Launch a desktop application when requested or "
                "required by the active task."
            ),
            provider="neuron.desktop",
            arguments=[
                CapabilityArgument(
                    name="application",
                    description=(
                        "Application resolved from user intent."
                    ),
                    required=True,
                )
            ],
            effects=[
                "desktop_application_launched",
            ],
        )
    )

    r.register(
        Capability(
            name="desktop.open_url",
            description=(
                "Open a web URL in the desktop environment."
            ),
            provider="neuron.desktop",
            arguments=[
                CapabilityArgument(
                    name="url",
                    description="HTTP or HTTPS URL.",
                    required=True,
                )
            ],
            effects=[
                "url_opened",
            ],
        )
    )

    #
    # PERSON / SOCIAL
    #

    r.register(
        Capability(
            name="person.observe",
            description=(
                "Use current camera and voice evidence to maintain "
                "the state of people currently present."
            ),
            provider="neuron.perception",
        )
    )

    r.register(
        Capability(
            name="person.identify_enrolled",
            description=(
                "Compare current face and voice evidence only against "
                "explicitly enrolled local identities and return "
                "owner, known, or unknown with calibrated evidence."
            ),
            provider="neuron.identity",
        )
    )

    r.register(
        Capability(
            name="dialogue.respond",
            description=(
                "Produce a natural conversational response grounded "
                "in the current discussion, sensory state, task state, "
                "and retrieved memory."
            ),
            provider="shmry.dialogue",
            arguments=[
                CapabilityArgument(
                    name="content",
                    description=(
                        "Semantic content to communicate."
                    ),
                    required=True,
                )
            ],
        )
    )

    r.register(
        Capability(
            name="dialogue.ask",
            description=(
                "Ask a contextually useful question, for example when "
                "meeting an unknown person or when essential ambiguity "
                "cannot be resolved from context."
            ),
            provider="shmry.dialogue",
            arguments=[
                CapabilityArgument(
                    name="purpose",
                    description=(
                        "Reason for asking."
                    ),
                    required=True,
                )
            ],
        )
    )

    #
    # MEMORY / REASONING
    #

    r.register(
        Capability(
            name="memory.retrieve",
            description=(
                "Retrieve task-relevant or person-relevant memory."
            ),
            provider="huobz+xerus",
            arguments=[
                CapabilityArgument(
                    name="query",
                    description=(
                        "Semantic memory query."
                    ),
                    required=True,
                )
            ],
        )
    )

    r.register(
        Capability(
            name="memory.remember",
            description=(
                "Store an appropriate durable memory after policy and "
                "consent checks."
            ),
            provider="huobz+xerus",
            arguments=[
                CapabilityArgument(
                    name="content",
                    description=(
                        "Structured content to remember."
                    ),
                    type="object",
                    required=True,
                )
            ],
            effects=[
                "memory_written",
            ],
        )
    )

    return r
