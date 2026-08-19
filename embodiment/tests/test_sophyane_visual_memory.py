from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOPHYANE = Path.home() / "sophyane"

sys.path.insert(
    0,
    str(ROOT),
)

sys.path.insert(
    0,
    str(SOPHYANE / "src"),
)


def test_visual_chunk_uses_sophyane_chunkstore(
    tmp_path,
    monkeypatch,
):
    visual_home = (
        tmp_path /
        "visual-memory"
    )

    screenshot = (
        tmp_path /
        "frame.png"
    )

    # Minimal real PNG signature is enough for adapter persistence test.
    screenshot.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        b"neuron-test"
    )

    monkeypatch.setenv(
        "NEURON_SOPHYANE_ROOT",
        str(SOPHYANE),
    )

    monkeypatch.setenv(
        "NEURON_VISUAL_MEMORY_HOME",
        str(visual_home),
    )

    # Avoid accidental dependency on a running GGUF embedding server.
    monkeypatch.setenv(
        "SOPHYANE_EMBED_BACKEND",
        "hashing",
    )

    import integration.sophyane_visual_memory as visual

    importlib.reload(visual)

    memory = (
        visual.SophyaneVisualMemory()
    )

    chunk = memory.remember(
        visual.VisualChunkInput(
            screenshot_path=str(
                screenshot
            ),
            description=(
                "Windows terminal showing "
                "Neuron synaptic tests."
            ),
            timestamp=1234.5,
            application="Windows Terminal",
            window_title="badrpk@Badar",
            objects=(
                "terminal",
                "text",
            ),
        )
    )

    assert chunk.language == "visual"
    assert chunk.source == "neuron-screen"
    assert chunk.path == str(
        screenshot.resolve()
    )

    assert (
        chunk.meta["modality"]
        == "visual"
    )

    assert (
        chunk.meta["application"]
        == "Windows Terminal"
    )

    assert (
        chunk.meta["objects"]
        == ["terminal", "text"]
    )

    assert memory.store.vectors is not None
    assert len(memory.store.vectors) == 1

    # Sophyane's canonical stable vector dimension.
    assert (
        memory.store.vectors.shape[1]
        == 384
    )

    results = memory.retrieve(
        "terminal neuron tests",
        top_k=3,
    )

    assert results

    retrieved, score = results[0]

    assert retrieved.id == chunk.id
    assert isinstance(
        score,
        float,
    )

    latest = (
        memory.latest_visual_chunks()
    )

    assert [
        item.id
        for item in latest
    ] == [chunk.id]
