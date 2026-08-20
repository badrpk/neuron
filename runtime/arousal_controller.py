from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ArousalState(str, Enum):
    SLEEPING = "sleeping"
    ATTENTIVE = "attentive"
    ENGAGED = "engaged"


@dataclass(frozen=True)
class ArousalEvent:
    event: str
    text: str
    state: ArousalState


class NeuronArousalController:
    def __init__(self):
        self.state = ArousalState.SLEEPING

    @property
    def sleeping(self):
        return self.state == ArousalState.SLEEPING

    @property
    def attentive(self):
        return self.state in (
            ArousalState.ATTENTIVE,
            ArousalState.ENGAGED,
        )

    @property
    def engaged(self):
        return self.state == ArousalState.ENGAGED

    def process_speech(self, text):
        raw = str(text or "").strip()

        if not raw:
            return None

        normalized = raw.lower().strip()
        normalized = normalized.rstrip(" ,.!?")

        if normalized.startswith("neuron") and "sleep" in normalized:
            self.state = ArousalState.SLEEPING
            return ArousalEvent(
                "sleep_command",
                raw,
                self.state,
            )

        if normalized in (
            "neuron wake up",
            "neuron wake",
        ):
            self.state = ArousalState.ENGAGED
            return ArousalEvent(
                "wake_command",
                raw,
                self.state,
            )

        if normalized == "neuron":
            if self.state == ArousalState.SLEEPING:
                self.state = ArousalState.ATTENTIVE
                event = "wake_word"
            else:
                event = "attention_spike"

            return ArousalEvent(
                event,
                raw,
                self.state,
            )

        if self.state == ArousalState.ATTENTIVE:
            self.state = ArousalState.ENGAGED
            return ArousalEvent(
                "user_instruction",
                raw,
                self.state,
            )

        if self.state == ArousalState.ENGAGED:
            return ArousalEvent(
                "user_instruction",
                raw,
                self.state,
            )

        return None
