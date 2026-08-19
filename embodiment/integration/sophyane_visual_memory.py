from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _sophyane_root() -> Path:
    configured = os.environ.get(
        "NEURON_SOPHYANE_ROOT",
        str(Path.home() / "sophyane"),
    )
    return Path(configured).expanduser().resolve()


def _visual_home() -> Path:
    configured = os.environ.get(
        "NEURON_VISUAL_MEMORY_HOME",
        "/mnt/d/BadrpkData/repo-data/neuron/sophyane-visual-memory",
    )
    return Path(configured).expanduser().resolve()


def _load_store():
    sophyane_root = _sophyane_root()
    src = sophyane_root / "src"

    if not src.is_dir():
        raise RuntimeError(
            f"Sophyane src missing: {src}"
        )

    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

    # Reuse Sophyane exactly; do not create another embedding/vector layer.
    from sophyane.code_memory.store import ChunkStore

    # Point Sophyane's existing memory root at D: for Neuron visual memory.
    home = _visual_home()
    home.mkdir(parents=True, exist_ok=True)

    os.environ["SOPHYANE_HOME"] = str(home)

    return ChunkStore()


@dataclass(frozen=True)
class VisualChunkInput:
    screenshot_path: str
    description: str
    timestamp: float
    application: str = ""
    window_title: str = ""
    previous_chunk_id: str = ""
    objects: tuple[str, ...] = ()
    weight: float = 1.0


class SophyaneVisualMemory:
    """Thin Neuron adapter over Sophyane's existing ChunkStore.

    Sophyane remains authoritative for:
      - embedding
      - vector persistence
      - chunk weights
      - semantic similarity retrieval

    This class only maps a visual observation into the existing chunk schema.
    """

    def __init__(self) -> None:
        self.store = _load_store()

    def remember(
        self,
        observation: VisualChunkInput,
    ):
        screenshot = Path(
            observation.screenshot_path
        ).expanduser().resolve()

        if not screenshot.is_file():
            raise FileNotFoundError(
                f"screenshot missing: {screenshot}"
            )

        description = str(
            observation.description or ""
        ).strip()

        if not description:
            description = (
                f"Visual screen observation from "
                f"{observation.application or 'unknown application'}"
            )

        tags = [
            "visual",
            "neuron",
            "screen",
            "temporal",
        ]

        if observation.application:
            tags.append(
                "app:" + observation.application
            )

        meta: dict[str, Any] = {
            "modality": "visual",
            "timestamp": float(
                observation.timestamp
            ),
            "application": str(
                observation.application or ""
            ),
            "window_title": str(
                observation.window_title or ""
            ),
            "previous_chunk_id": str(
                observation.previous_chunk_id or ""
            ),
            "objects": list(
                observation.objects
            ),
            "screenshot_path": str(
                screenshot
            ),
        }

        return self.store.add_chunk(
            text=description,
            language="visual",
            path=str(screenshot),
            source="neuron-screen",
            tags=tags,
            meta=meta,
            weight=float(
                observation.weight
            ),
        )

    def retrieve(
        self,
        query: str,
        top_k: int = 8,
    ):
        # Deliberately use Sophyane's generic vector retrieval directly.
        #
        # semantic_retrieve.py currently has code-specific role heuristics;
        # visual memory should not inherit those heuristics accidentally.
        return self.store.retrieve(
            str(query or ""),
            top_k=int(top_k),
        )

    def latest_visual_chunks(
        self,
        limit: int = 20,
    ):
        chunks = []

        for chunk_id in self.store.ids:
            chunk = self.store.chunks.get(
                chunk_id
            )

            if chunk is None:
                continue

            meta = dict(
                chunk.meta or {}
            )

            if meta.get(
                "modality"
            ) != "visual":
                continue

            chunks.append(chunk)

        chunks.sort(
            key=lambda item: float(
                (item.meta or {}).get(
                    "timestamp",
                    item.created_at or 0.0,
                )
            )
        )

        return chunks[
            -max(1, int(limit)):
        ]


__all__ = [
    "SophyaneVisualMemory",
    "VisualChunkInput",
]
