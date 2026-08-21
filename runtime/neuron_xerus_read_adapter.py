"""Read-only Xerus memory evidence adapter.

The adapter calls recall only.

It never calls remember().
"""

from __future__ import annotations

import os
from pathlib import Path
import sys
from typing import Any

from neuron_evidence_contract import (
    EvidenceItem,
)


def _source_root() -> Path:
    configured = os.environ.get(
        "NEURON_BADRPK_XERUS_ROOT",
        "",
    ).strip()

    if configured:
        return Path(
            configured
        ).expanduser()

    return (
        Path.home()
        / "badrpk-repos"
        / "xerus"
    )


def _ensure_import_path() -> Path:
    root = _source_root()

    source = root / "src"

    if (
        source.is_dir()
        and str(source)
        not in sys.path
    ):
        sys.path.insert(
            0,
            str(source),
        )

    return root


def _normalize(
    value: Any,
) -> Any:
    if isinstance(
        value,
        dict,
    ):
        return {
            str(key):
                _normalize(item)
            for key, item
            in value.items()
        }

    if isinstance(
        value,
        (
            list,
            tuple,
        ),
    ):
        return [
            _normalize(item)
            for item in value
        ]

    if isinstance(
        value,
        (
            str,
            int,
            float,
            bool,
        ),
    ) or value is None:
        return value

    return str(value)


def gather_xerus_evidence(
    text: str,
    *,
    limit: int = 4,
) -> tuple[EvidenceItem, ...]:

    query = str(
        text
        or ""
    ).strip()

    if not query:
        return ()

    root = _ensure_import_path()

    if not root.is_dir():
        return ()

    try:
        from xerus.memory import (
            recall,
        )

        result = recall(
            query,
            limit=max(
                1,
                min(
                    int(limit),
                    4,
                ),
            ),
        )

    except Exception as exc:
        return (
            EvidenceItem(
                source="xerus",
                kind="adapter_error",
                content={
                    "stage":
                        "recall",

                    "error":
                        (
                            type(exc).__name__
                            + ": "
                            + str(exc)
                        ),
                },
                confidence=0.0,
                provenance=(
                    "badrpk/xerus:"
                    "xerus.memory.recall"
                ),
                permission="READ",
            ),
        )

    normalized = _normalize(
        result
    )

    empty = (
        normalized is None
        or normalized == []
        or normalized == {}
        or normalized == ""
    )

    if empty:
        return ()

    return (
        EvidenceItem(
            source="xerus",
            kind="memory_recall",
            content={
                "result":
                    normalized,
            },
            confidence=0.64,
            provenance=(
                "badrpk/xerus:"
                "xerus.memory.recall"
            ),
            permission="READ",
        ),
    )
