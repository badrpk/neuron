from __future__ import annotations

import hashlib
import json
import os

from perception.perceptual_context import (
    PerceptualContextBuilder,
)

# NEURON_PERCEPTUAL_CONTEXT_V2
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class MotorAssociation:
    context_key: str
    target_key: str
    action_key: str
    weight: float
    successes: int
    failures: int
    last_x: int
    last_y: int

    def to_dict(self):
        return asdict(self)


class XerusMotorLearning:
    """
    V1 persistent percept->action->result association layer.

    This adapter intentionally stores only compact learned
    associations, not raw screenshots.

    The persistence format is local and replaceable by the
    native Xerus synaptic backend later.
    """

    def __init__(
        self,
        root: str | None = None,
    ):
        self.root = Path(
            root
            or os.environ.get(
                "NEURON_XERUS_MOTOR_HOME",
                "/mnt/d/BadrpkData/repo-data/"
                "neuron/xerus-motor-learning",
            )
        )

        self.root.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.path = (
            self.root
            / "motor-associations.json"
        )

    @staticmethod
    def _norm(
        text: str,
    ) -> str:
        return " ".join(
            str(text or "")
            .lower()
            .strip()
            .split()
        )

    @classmethod
    def context_key(
        cls,
        *,
        screenshot_path: str,
        target_instruction: str,
        semantic_gist: str = "",
    ) -> str:
        #
        # V2:
        # context no longer depends on screenshot filename.
        #
        # Semantic gist + coarse rendered-pixel structure
        # define the perceptual context.
        #
        builder = (
            PerceptualContextBuilder()
        )

        context = builder.build(
            screenshot_path=(
                screenshot_path
            ),
            semantic_gist=(
                semantic_gist
                or target_instruction
            ),
        )

        return context.context_key

    @classmethod
    def target_key(
        cls,
        instruction: str,
    ) -> str:
        return cls._norm(
            instruction
        )

    @staticmethod
    def action_key(
        x: int,
        y: int,
    ) -> str:
        #
        # Quantize coordinates slightly so nearby successful
        # locations can reinforce the same association.
        #
        qx = int(x) // 20
        qy = int(y) // 20

        return (
            f"click:{qx}:{qy}"
        )

    def _load(
        self,
    ) -> dict:
        if not self.path.exists():
            return {}

        try:
            data = json.loads(
                self.path.read_text(
                    encoding="utf-8"
                )
            )
        except Exception:
            return {}

        if not isinstance(
            data,
            dict,
        ):
            return {}

        return data

    def _save(
        self,
        data: dict,
    ):
        temporary = (
            self.path
            .with_suffix(
                ".tmp"
            )
        )

        temporary.write_text(
            json.dumps(
                data,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        temporary.replace(
            self.path
        )

    def record(
        self,
        *,
        screenshot_path: str,
        target_instruction: str,
        x: int,
        y: int,
        success: bool,
        semantic_gist: str = "",
    ) -> MotorAssociation:
        context = self.context_key(
            screenshot_path=screenshot_path,
            target_instruction=(
                target_instruction
            ),
            semantic_gist=(
                semantic_gist
            ),
        )

        target = self.target_key(
            target_instruction
        )

        action = self.action_key(
            x,
            y,
        )

        compound = (
            context
            + "|"
            + target
            + "|"
            + action
        )

        data = self._load()

        current = dict(
            data.get(
                compound,
                {},
            )
        )

        weight = float(
            current.get(
                "weight",
                0.0,
            )
            or 0.0
        )

        successes = int(
            current.get(
                "successes",
                0,
            )
            or 0
        )

        failures = int(
            current.get(
                "failures",
                0,
            )
            or 0
        )

        if success:
            #
            # Bounded Hebbian-like reinforcement.
            #
            weight = min(
                1.0,
                weight + 0.15,
            )

            successes += 1

        else:
            #
            # Failed verified outcome depresses association.
            #
            weight = max(
                -1.0,
                weight - 0.10,
            )

            failures += 1

        record = {
            "context_key":
                context,
            "target_key":
                target,
            "action_key":
                action,
            "weight":
                weight,
            "successes":
                successes,
            "failures":
                failures,
            "last_x":
                int(x),
            "last_y":
                int(y),
        }

        data[
            compound
        ] = record

        self._save(
            data
        )

        return MotorAssociation(
            **record
        )

    def strongest(
        self,
        *,
        target_instruction: str,
        limit: int = 5,
    ) -> list[MotorAssociation]:
        target = self.target_key(
            target_instruction
        )

        rows = []

        for value in (
            self._load()
            .values()
        ):
            if (
                value.get(
                    "target_key"
                )
                != target
            ):
                continue

            try:
                rows.append(
                    MotorAssociation(
                        context_key=str(
                            value[
                                "context_key"
                            ]
                        ),
                        target_key=str(
                            value[
                                "target_key"
                            ]
                        ),
                        action_key=str(
                            value[
                                "action_key"
                            ]
                        ),
                        weight=float(
                            value[
                                "weight"
                            ]
                        ),
                        successes=int(
                            value[
                                "successes"
                            ]
                        ),
                        failures=int(
                            value[
                                "failures"
                            ]
                        ),
                        last_x=int(
                            value[
                                "last_x"
                            ]
                        ),
                        last_y=int(
                            value[
                                "last_y"
                            ]
                        ),
                    )
                )
            except Exception:
                continue

        rows.sort(
            key=lambda item: (
                item.weight,
                item.successes,
                -item.failures,
            ),
            reverse=True,
        )

        return rows[
            :max(
                1,
                int(limit),
            )
        ]

    # NEURON_XERUS_CONTEXT_RECALL_V1
    def recall_for_context(
        self,
        *,
        screenshot_path: str,
        target_instruction: str,
        semantic_gist: str = "",
        minimum_weight: float = 0.30,
    ) -> MotorAssociation | None:
        """
        Recall strongest learned action for the CURRENT
        perceptual context.

        Memory only proposes an action region.
        It does not authorize execution.
        """

        context = self.context_key(
            screenshot_path=screenshot_path,
            target_instruction=(
                target_instruction
            ),
            semantic_gist=(
                semantic_gist
            ),
        )

        target = self.target_key(
            target_instruction
        )

        candidates = []

        for value in (
            self._load()
            .values()
        ):
            if (
                value.get(
                    "context_key"
                )
                != context
            ):
                continue

            if (
                value.get(
                    "target_key"
                )
                != target
            ):
                continue

            try:
                association = (
                    MotorAssociation(
                        context_key=str(
                            value[
                                "context_key"
                            ]
                        ),
                        target_key=str(
                            value[
                                "target_key"
                            ]
                        ),
                        action_key=str(
                            value[
                                "action_key"
                            ]
                        ),
                        weight=float(
                            value[
                                "weight"
                            ]
                        ),
                        successes=int(
                            value[
                                "successes"
                            ]
                        ),
                        failures=int(
                            value[
                                "failures"
                            ]
                        ),
                        last_x=int(
                            value[
                                "last_x"
                            ]
                        ),
                        last_y=int(
                            value[
                                "last_y"
                            ]
                        ),
                    )
                )
            except Exception:
                continue

            if (
                association.weight
                < float(
                    minimum_weight
                )
            ):
                continue

            candidates.append(
                association
            )

        if not candidates:
            return None

        candidates.sort(
            key=lambda item: (
                item.weight,
                item.successes,
                -item.failures,
            ),
            reverse=True,
        )

        return candidates[0]
