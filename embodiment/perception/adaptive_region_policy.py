from __future__ import annotations

from dataclasses import (
    asdict,
    dataclass,
)


@dataclass(frozen=True)
class RegionSize:
    radius_x: int
    radius_y: int
    confidence_score: float
    reason: str = ""

    def to_dict(self):
        return asdict(self)


class AdaptiveRegionPolicy:
    """
    Convert learned-association quality into a bounded crop size.

    Memory influences where/how widely to look.
    It never authorizes motor action.
    """

    MIN_RADIUS = 32

    def choose(
        self,
        *,
        weight: float,
        successes: int,
        failures: int,
    ) -> RegionSize:
        weight = max(
            -1.0,
            min(
                1.0,
                float(weight),
            ),
        )

        successes = max(
            0,
            int(successes),
        )

        failures = max(
            0,
            int(failures),
        )

        total = (
            successes
            + failures
        )

        success_ratio = (
            successes / total
            if total
            else 0.0
        )

        #
        # Combine learned weight with empirical success ratio.
        #
        normalized_weight = (
            weight + 1.0
        ) / 2.0

        score = (
            0.60
            * normalized_weight
            + 0.40
            * success_ratio
        )

        score = max(
            0.0,
            min(
                1.0,
                score,
            ),
        )

        #
        # Very strong/stable association.
        #
        if (
            score >= 0.85
            and successes >= 5
            and failures == 0
        ):
            return RegionSize(
                radius_x=80,
                radius_y=60,
                confidence_score=score,
                reason="very strong stable association",
            )

        #
        # Strong association.
        #
        if (
            score >= 0.70
            and successes >= 3
        ):
            return RegionSize(
                radius_x=120,
                radius_y=90,
                confidence_score=score,
                reason="strong learned association",
            )

        #
        # Usable but still uncertain.
        #
        if (
            score >= 0.55
            and successes >= 2
        ):
            return RegionSize(
                radius_x=180,
                radius_y=130,
                confidence_score=score,
                reason="moderate learned association",
            )

        #
        # Weak/stale memory: wide crop.
        #
        return RegionSize(
            radius_x=260,
            radius_y=190,
            confidence_score=score,
            reason="weak or uncertain association",
        )
