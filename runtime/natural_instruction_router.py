from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class NaturalInstructionPlan:
    intent: str
    confidence: float = 0.0
    url: str = ""
    requires_visual_observation: bool = False
    instruction: str = ""


class NaturalInstructionRouter:
    URLS = {
        "dawn": "https://www.dawn.com",
        "bbc": "https://www.bbc.com",
    }

    @staticmethod
    def strip_wake_word(text):
        value = str(text or "").strip()

        return re.sub(
            r"^\s*neuron\s*[,:\-]?\s*",
            "",
            value,
            flags=re.I,
        ).strip()

    def _url(self, text):
        lower = text.lower()

        for name, url in self.URLS.items():
            if re.search(
                rf"\b{re.escape(name)}\b",
                lower,
            ):
                return url

        return ""

    def plan(self, text):
        instruction = self.strip_wake_word(text)
        lower = instruction.lower()
        url = self._url(instruction)

        memory_markers = (
            "what did you see",
            "remember seeing",
            "saw before",
            "seen before",
            "earlier on",
        )

        if any(x in lower for x in memory_markers):
            return NaturalInstructionPlan(
                intent="recall_visual_memory",
                confidence=1.0,
                instruction=instruction,
            )

        visual = any(
            x in lower
            for x in (
                "what do you see",
                "tell me what you see",
                "describe",
                "look at",
                "inspect",
                "appears",
            )
        )

        if url and (
            "open" in lower
            and visual
        ):
            return NaturalInstructionPlan(
                intent="open_and_observe",
                confidence=1.0,
                url=url,
                requires_visual_observation=True,
                instruction=instruction,
            )

        if url and "open" in lower:
            return NaturalInstructionPlan(
                intent="open_url",
                confidence=1.0,
                url=url,
                instruction=instruction,
            )

        if visual:
            return NaturalInstructionPlan(
                intent="observe_screen",
                confidence=1.0,
                requires_visual_observation=True,
                instruction=instruction,
            )

        return NaturalInstructionPlan(
            intent="unresolved_instruction",
            confidence=0.0,
            instruction=instruction,
        )
