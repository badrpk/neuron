from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class VisualTarget:
    ok: bool
    label: str = ""
    x: int = -1
    y: int = -1
    confidence: float = 0.0
    reason: str = ""
    raw: str = ""

    def to_dict(self):
        return asdict(self)


class VisualTargeting:
    """
    Parse a deliberately constrained target-location response.

    Required model format:

        {
          "target_found": true,
          "label": "...",
          "x": 500,
          "y": 300,
          "confidence": 0.82,
          "reason": "..."
        }

    Coordinates are screen pixels.
    """

    def __init__(
        self,
        *,
        minimum_confidence: float = 0.55,
        max_width: int = 10000,
        max_height: int = 10000,
    ):
        self.minimum_confidence = float(
            minimum_confidence
        )
        self.max_width = int(max_width)
        self.max_height = int(max_height)

    @staticmethod
    def targeting_question(
        instruction: str,
    ) -> str:
        instruction = str(
            instruction or ""
        ).strip()

        return (
            "Locate the single visible clickable target requested "
            "by the user on the CURRENT rendered screenshot.\n\n"
            f"User request: {instruction}\n\n"
            "Return ONLY one JSON object with exactly these fields:\n"
            '{"target_found":true|false,'
            '"label":"visible target label",'
            '"x":integer_pixel_x,'
            '"y":integer_pixel_y,'
            '"confidence":0.0,'
            '"reason":"short visible grounding reason"}\n\n'
            "Rules:\n"
            "- x/y must identify the visible center of the clickable target.\n"
            "- Use only what is visibly grounded in the screenshot.\n"
            "- Do not infer hidden DOM structure.\n"
            "- Do not guess a coordinate.\n"
            "- If uncertain, set target_found=false.\n"
        )

    @staticmethod
    def _extract_json(
        raw: str,
    ) -> dict | None:
        raw = str(
            raw or ""
        ).strip()

        if not raw:
            return None

        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                return data
        except Exception:
            pass

        match = re.search(
            r"\{.*\}",
            raw,
            flags=re.DOTALL,
        )

        if not match:
            return None

        try:
            data = json.loads(
                match.group(0)
            )
        except Exception:
            return None

        if not isinstance(data, dict):
            return None

        return data

    def parse(
        self,
        raw: str,
    ) -> VisualTarget:
        data = self._extract_json(
            raw
        )

        if data is None:
            return VisualTarget(
                ok=False,
                reason="invalid target JSON",
                raw=str(raw or ""),
            )

        if data.get(
            "target_found"
        ) is not True:
            return VisualTarget(
                ok=False,
                label=str(
                    data.get(
                        "label",
                        "",
                    )
                ),
                confidence=float(
                    data.get(
                        "confidence",
                        0.0,
                    )
                    or 0.0
                ),
                reason=str(
                    data.get(
                        "reason",
                        "target not found",
                    )
                ),
                raw=str(raw or ""),
            )

        try:
            x = int(
                data["x"]
            )
            y = int(
                data["y"]
            )
            confidence = float(
                data.get(
                    "confidence",
                    0.0,
                )
            )
        except Exception:
            return VisualTarget(
                ok=False,
                reason="invalid target coordinate",
                raw=str(raw or ""),
            )

        if confidence < self.minimum_confidence:
            return VisualTarget(
                ok=False,
                label=str(
                    data.get(
                        "label",
                        "",
                    )
                ),
                x=x,
                y=y,
                confidence=confidence,
                reason="target confidence below threshold",
                raw=str(raw or ""),
            )

        if (
            x < 0
            or y < 0
            or x > self.max_width
            or y > self.max_height
        ):
            return VisualTarget(
                ok=False,
                label=str(
                    data.get(
                        "label",
                        "",
                    )
                ),
                x=x,
                y=y,
                confidence=confidence,
                reason="target coordinate outside bounds",
                raw=str(raw or ""),
            )

        return VisualTarget(
            ok=True,
            label=str(
                data.get(
                    "label",
                    "",
                )
            ).strip(),
            x=x,
            y=y,
            confidence=confidence,
            reason=str(
                data.get(
                    "reason",
                    "",
                )
            ).strip(),
            raw=str(raw or ""),
        )
