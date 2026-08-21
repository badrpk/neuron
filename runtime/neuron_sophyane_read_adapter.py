"""Read-only Sophyane semantic evidence adapter.

This adapter may interpret/query existing Sophyane intelligence.

It may not:
- execute capabilities;
- mutate repositories;
- invoke provider fallback;
- persist memory;
- propagate information.
"""

from __future__ import annotations

from dataclasses import asdict
import os
from pathlib import Path
import sys
from typing import Any

from neuron_evidence_contract import (
    EvidenceItem,
)


def _source_root() -> Path:
    configured = os.environ.get(
        "NEURON_BADRPK_SOPHYANE_ROOT",
        "",
    ).strip()

    if configured:
        return Path(
            configured
        ).expanduser()

    return (
        Path.home()
        / "badrpk-repos"
        / "sophyane"
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


def _safe_payload(
    value: Any,
) -> Any:
    if hasattr(
        value,
        "__dataclass_fields__",
    ):
        return {
            key:
                _safe_payload(item)
            for key, item
            in asdict(value).items()
        }

    if isinstance(
        value,
        dict,
    ):
        return {
            str(key):
                _safe_payload(item)
            for key, item
            in value.items()
        }

    if isinstance(
        value,
        (
            list,
            tuple,
            set,
        ),
    ):
        return [
            _safe_payload(item)
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


def gather_sophyane_evidence(
    text: str,
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

    items: list[
        EvidenceItem
    ] = []

    #
    # Pure semantic plan construction.
    #
    try:
        from sophyane.sli_semantic_intelligence import (
            build_semantic_plan,
        )

        plan = build_semantic_plan(
            query
        )

        items.append(
            EvidenceItem(
                source="sophyane",
                kind="semantic_plan",
                content={
                    "plan":
                        _safe_payload(
                            plan
                        ),
                },
                confidence=0.72,
                provenance=(
                    "badrpk/sophyane:"
                    "sli_semantic_intelligence."
                    "build_semantic_plan"
                ),
                permission="READ",
            )
        )

    except Exception as exc:
        items.append(
            EvidenceItem(
                source="sophyane",
                kind="adapter_error",
                content={
                    "stage":
                        "build_semantic_plan",

                    "error":
                        (
                            type(exc).__name__
                            + ": "
                            + str(exc)
                        ),
                },
                confidence=0.0,
                provenance=(
                    "badrpk/sophyane:"
                    "sli_semantic_intelligence"
                ),
                permission="READ",
            )
        )

    #
    # Pure runtime semantic ledger analysis.
    #
    try:
        from sophyane.runtime_sli_semantic import (
            analyze,
        )

        ledger = analyze(
            query
        )

        items.append(
            EvidenceItem(
                source="sophyane",
                kind="semantic_ledger",
                content={
                    "ledger":
                        _safe_payload(
                            ledger
                        ),
                },
                confidence=0.68,
                provenance=(
                    "badrpk/sophyane:"
                    "runtime_sli_semantic.analyze"
                ),
                permission="READ",
            )
        )

    except Exception as exc:
        items.append(
            EvidenceItem(
                source="sophyane",
                kind="adapter_error",
                content={
                    "stage":
                        "runtime_semantic_analyze",

                    "error":
                        (
                            type(exc).__name__
                            + ": "
                            + str(exc)
                        ),
                },
                confidence=0.0,
                provenance=(
                    "badrpk/sophyane:"
                    "runtime_sli_semantic"
                ),
                permission="READ",
            )
        )

    return tuple(
        items[:4]
    )
