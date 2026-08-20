from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re
import sys
import time
from typing import Any
from urllib.parse import quote_plus


ROOT = Path(__file__).resolve().parents[1]
EMB = ROOT / "embodiment"

for value in (
    str(ROOT),
    str(EMB),
):
    if value not in sys.path:
        sys.path.insert(0, value)


@dataclass(frozen=True)
class NativeResult:
    handled: bool
    ok: bool
    capability: str = ""
    answer: str = ""
    error: str = ""
    partial: bool = False
    raw: dict[str, Any] | None = None


def _normalise(text: str) -> str:
    return " ".join(
        str(text or "")
        .strip()
        .casefold()
        .split()
    )


def classify_native(text: str) -> str:
    lower = _normalise(text)

    if not lower:
        return ""

    # ---------------------------------------------------------
    # SYSTEM CLOCK
    # ---------------------------------------------------------

    clock_patterns = (
        r"\bwhat(?:'s| is)? the time\b",
        r"\bwhat time is it\b",
        r"\btime now\b",
        r"\bcurrent time\b",
        r"\bwhat(?:'s| is)? (?:the )?date\b",
        r"\bdate and time\b",
        r"\bcurrent date\b",
        r"\bdate today\b",
        r"\bwhat day is it\b",
    )

    if any(
        re.search(pattern, lower)
        for pattern in clock_patterns
    ):
        return "system.clock"

    # ---------------------------------------------------------
    # SCREEN METADATA
    # ---------------------------------------------------------

    metadata_patterns = (
        r"\bwhat is opened on (?:my|the) screen\b",
        r"\bwhat is open on (?:my|the) screen\b",
        r"\bwhat's open on (?:my|the) screen\b",
        r"\bwhich window is active\b",
        r"\bwhat window is active\b",
        r"\bactive window\b",
        r"\bforeground window\b",
        r"\bwhich app is open\b",
        r"\bwhat app is open\b",
        r"\bwhich application is active\b",
    )

    if any(
        re.search(pattern, lower)
        for pattern in metadata_patterns
    ):
        return "screen.observe"

    # ---------------------------------------------------------
    # PIXEL-LEVEL SCREEN VISION
    # ---------------------------------------------------------

    visual_markers = (
        "what do you see on my screen",
        "what can you see on my screen",
        "describe my screen",
        "describe the screen",
        "look at my screen",
        "inspect my screen",
        "what is visible on my screen",
        "read my screen",
        "read the screen",
        "what is shown on my screen",
        "what is displayed on my screen",
    )

    if any(
        marker in lower
        for marker in visual_markers
    ):
        return "screen.visual_question"

    # ---------------------------------------------------------
    # MICROPHONE
    # ---------------------------------------------------------

    audio_markers = (
        "hear around",
        "listen around",
        "listen to my surroundings",
        "listen to the room",
        "who is talking",
        "who is speaking",
        "how many people are talking",
        "how many people are speaking",
        "how many females",
        "how many males",
        "microphone",
        "listen to me",
    )

    if any(
        marker in lower
        for marker in audio_markers
    ):
        return "audio.listen"

    # ---------------------------------------------------------
    # CURRENT AFFECT / EMOTION
    # ---------------------------------------------------------

    affect_patterns = (
        r"\bam i happy\b",
        r"\bam i sad\b",
        r"\bam i angry\b",
        r"\bam i tired\b",
        r"\bwhat is my mood\b",
        r"\bwhat's my mood\b",
        r"\bhow do i feel\b",
        r"\bhow am i feeling\b",
    )

    if any(
        re.search(pattern, lower)
        for pattern in affect_patterns
    ):
        return "person.affect"

    # ---------------------------------------------------------
    # YOUTUBE / BROWSER ACTION
    # ---------------------------------------------------------

    if (
        "youtube" in lower
        and any(
            word in lower
            for word in (
                "play ",
                "open ",
                "search ",
                "find ",
            )
        )
    ):
        return "youtube.action"

    return ""


def _clock() -> NativeResult:
    now = datetime.now().astimezone()

    zone = (
        now.tzname()
        or str(now.utcoffset() or "")
    )

    answer = (
        "It is "
        + now.strftime(
            "%I:%M:%S %p on %A, %d %B %Y"
        )
        + (
            f" ({zone})."
            if zone
            else "."
        )
    )

    return NativeResult(
        handled=True,
        ok=True,
        capability="system.clock",
        answer=answer,
    )


def _screen_observe() -> NativeResult:
    try:
        from desktop.windows_bridge import (
            WindowsBridge,
        )
    except Exception as exc:
        return NativeResult(
            handled=True,
            ok=False,
            capability="screen.observe",
            error=(
                "Windows screen bridge unavailable: "
                f"{exc}"
            ),
        )

    result = (
        WindowsBridge()
        .observe_screen()
    )

    raw = result.to_dict()

    if not result.ok:
        return NativeResult(
            handled=True,
            ok=False,
            capability="screen.observe",
            error=(
                result.stderr
                or "screen capture failed"
            ),
            raw=raw,
        )

    parts: list[str] = []

    if result.application:
        parts.append(
            "The active application is "
            f"{result.application}."
        )

    if result.window_title:
        parts.append(
            'The active window is '
            f'"{result.window_title}".'
        )

    if result.screen_bounds:
        width = (
            result.screen_bounds
            .get("width")
        )
        height = (
            result.screen_bounds
            .get("height")
        )

        if width and height:
            parts.append(
                f"The desktop is "
                f"{width}×{height}."
            )

    if not parts:
        parts.append(
            "I captured the desktop, but "
            "Windows returned no foreground "
            "window metadata."
        )

    return NativeResult(
        handled=True,
        ok=True,
        capability="screen.observe",
        answer=" ".join(parts),
        raw=raw,
    )


def _screen_visual(
    question: str,
) -> NativeResult:
    try:
        from desktop.windows_bridge import (
            WindowsBridge,
        )
        from perception.vision_client import (
            VisionClient,
        )
    except Exception as exc:
        return NativeResult(
            handled=True,
            ok=False,
            capability="screen.visual_question",
            error=(
                "visual runtime unavailable: "
                f"{exc}"
            ),
        )

    observation = (
        WindowsBridge()
        .observe_screen()
    )

    if not observation.ok:
        return NativeResult(
            handled=True,
            ok=False,
            capability="screen.visual_question",
            error=(
                observation.stderr
                or "screen capture failed"
            ),
            raw=observation.to_dict(),
        )

    result = VisionClient(
        host="127.0.0.1",
        port=8769,
    ).ask_image(
        observation.screenshot_path,
        question,
    )

    raw = result.to_dict()

    if not result.ok:
        return NativeResult(
            handled=True,
            ok=False,
            capability="screen.visual_question",
            error=(
                result.error
                or result.status
                or "vision unavailable"
            ),
            raw=raw,
        )

    return NativeResult(
        handled=True,
        ok=True,
        capability="screen.visual_question",
        answer=result.answer,
        raw=raw,
    )


def _audio_listen(
    text: str,
) -> NativeResult:
    try:
        from audio.windows_listener import (
            WindowsListener,
        )
    except Exception as exc:
        return NativeResult(
            handled=True,
            ok=False,
            capability="audio.listen",
            error=(
                "Windows audio listener "
                f"unavailable: {exc}"
            ),
        )

    lower = _normalise(text)

    result = (
        WindowsListener()
        .listen_once(
            timeout_seconds=12
        )
    )

    raw = result.to_dict()

    asks_demographics = any(
        marker in lower
        for marker in (
            "male",
            "female",
            "men",
            "women",
            "gender",
            "how many people",
            "who is talking",
            "who is speaking",
        )
    )

    if not result.ok:
        if asks_demographics:
            answer = (
                "I could not obtain a usable "
                "speech sample from the Windows "
                "microphone. Also, Neuron's current "
                "audio capability is speech "
                "recognition only; it does not yet "
                "provide reliable speaker diarization "
                "or male/female speaker counts."
            )

            return NativeResult(
                handled=True,
                ok=True,
                capability="audio.listen",
                answer=answer,
                raw=raw,
            )

        return NativeResult(
            handled=True,
            ok=False,
            capability="audio.listen",
            error=(
                result.error
                or "no speech detected"
            ),
            raw=raw,
        )

    if asks_demographics:
        answer = (
            "I heard speech"
            + (
                f': "{result.text}". '
                if result.text
                else ". "
            )
            + "The current Windows listener "
            "does not provide reliable speaker "
            "diarization or male/female speaker "
            "classification, so I will not invent "
            "those counts."
        )
    else:
        answer = (
            "I heard: "
            f'"{result.text}".'
        )

    return NativeResult(
        handled=True,
        ok=True,
        capability="audio.listen",
        answer=answer,
        raw=raw,
    )


def _affect() -> NativeResult:
    # Current repository has person-presence concepts,
    # but no validated affect classifier is authoritative
    # here. Do not convert generic LLM speculation into
    # a claimed sensor observation.
    return NativeResult(
        handled=True,
        ok=True,
        capability="person.affect",
        answer=(
            "I cannot determine whether you are "
            "happy or sad from grounded evidence "
            "yet. Neuron needs a validated current "
            "face/voice affect signal before making "
            "that kind of claim."
        ),
    )


def _youtube_query(
    text: str,
) -> str:
    value = str(text or "").strip()

    value = re.sub(
        r"\bplay\b",
        " ",
        value,
        flags=re.I,
    )

    value = re.sub(
        r"\b(?:from|on)\s+youtube\b",
        " ",
        value,
        flags=re.I,
    )

    value = re.sub(
        r"\bon\s+my\s+computer\b",
        " ",
        value,
        flags=re.I,
    )

    value = re.sub(
        r"\bon\s+the\s+computer\b",
        " ",
        value,
        flags=re.I,
    )

    value = re.sub(
        r"\byoutube\b",
        " ",
        value,
        flags=re.I,
    )

    value = " ".join(
        value.split()
    )

    return (
        value
        or "latest Indian song"
    )


def _youtube_action(
    text: str,
) -> NativeResult:
    try:
        from desktop.windows_bridge import (
            WindowsBridge,
        )
    except Exception as exc:
        return NativeResult(
            handled=True,
            ok=False,
            capability="youtube.action",
            error=(
                "Windows browser bridge "
                f"unavailable: {exc}"
            ),
        )

    query = _youtube_query(
        text
    )

    url = (
        "https://www.youtube.com/"
        "results?search_query="
        + quote_plus(query)
    )

    bridge = WindowsBridge()

    opened = bridge.open_url(
        url
    )

    if not opened.ok:
        return NativeResult(
            handled=True,
            ok=False,
            capability="youtube.action",
            error=(
                opened.stderr
                or "failed to open YouTube"
            ),
            raw=opened.to_dict(),
        )

    lower = _normalise(text)

    # Search/open requests are complete once the
    # grounded URL launch succeeds.
    wants_play = (
        "play " in lower
        or lower.startswith("play")
    )

    if not wants_play:
        return NativeResult(
            handled=True,
            ok=True,
            capability="youtube.action",
            answer=(
                "Opened YouTube search results "
                f'for "{query}".'
            ),
            raw=opened.to_dict(),
        )

    # Give browser rendering a bounded head start.
    time.sleep(3.0)

    try:
        from desktop.windows_motor import (
            WindowsMotor,
        )
        from perception.vision_client import (
            VisionClient,
        )
        from runtime.verified_visual_click import (
            VerifiedVisualClick,
        )

        clicker = VerifiedVisualClick(
            bridge=bridge,
            motor=WindowsMotor(),
            vision=VisionClient(
                host="127.0.0.1",
                port=8769,
            ),
            motor_recall=None,
        )

        click = clicker.run(
            "Click the first actual YouTube "
            "video result in the main results "
            "column. Do not click an advertisement, "
            "navigation control, filter, or channel."
        )

    except Exception as exc:
        return NativeResult(
            handled=True,
            ok=False,
            partial=True,
            capability="youtube.action",
            answer=(
                "I opened YouTube search results "
                f'for "{query}", but could not '
                "perform a verified playback click."
            ),
            error=str(exc),
        )

    if not click.ok:
        return NativeResult(
            handled=True,
            ok=False,
            partial=True,
            capability="youtube.action",
            answer=(
                "I opened YouTube search results "
                f'for "{query}", but did not '
                "perform an ungrounded click."
            ),
            error=(
                click.error
                or "video target was not grounded"
            ),
            raw={
                "target_label":
                    click.target_label,
                "confidence":
                    click.target_confidence,
                "x":
                    click.x,
                "y":
                    click.y,
            },
        )

    return NativeResult(
        handled=True,
        ok=True,
        capability="youtube.action",
        answer=(
            "Opened YouTube and performed a "
            "verified click on the first grounded "
            f'video result for "{query}".'
        ),
        raw={
            "target_label":
                click.target_label,
            "confidence":
                click.target_confidence,
            "x":
                click.x,
            "y":
                click.y,
            "rendered_change":
                click.changed,
        },
    )


def handle_native(
    text: str,
) -> NativeResult:
    capability = classify_native(
        text
    )

    if not capability:
        return NativeResult(
            handled=False,
            ok=False,
        )

    if capability == "system.clock":
        return _clock()

    if capability == "screen.observe":
        return _screen_observe()

    if capability == "screen.visual_question":
        return _screen_visual(
            text
        )

    if capability == "audio.listen":
        return _audio_listen(
            text
        )

    if capability == "person.affect":
        return _affect()

    if capability == "youtube.action":
        return _youtube_action(
            text
        )

    return NativeResult(
        handled=False,
        ok=False,
    )


# ============================================================
# NEURON_NATIVE_FRONTDOOR_V3_MEMORY_AUDIO_MULTIMODAL
# ============================================================

_previous_classify_native_v3 = (
    classify_native
)

_previous_handle_native_v3 = (
    handle_native
)


def _requested_listen_seconds(
    text: str,
) -> int:

    lower = _normalise(
        text
    )

    match = re.search(
        r"\b(\d{1,3})\s*"
        r"(?:seconds?|secs?|s)\b",
        lower,
    )

    if match:
        value = int(
            match.group(1)
        )

        return max(
            1,
            min(
                value,
                60,
            ),
        )

    if any(
        value in lower
        for value in (
            "longer",
            "for a while",
            "keep listening",
        )
    ):
        return 30

    return 10


def _listen_window(
    text: str,
) -> NativeResult:

    try:
        from audio.windows_listener import (
            WindowsListener,
        )

    except Exception as exc:
        return NativeResult(
            handled=True,
            ok=False,
            capability="audio.listen",
            error=(
                "Windows microphone listener "
                f"is unavailable: {exc}"
            ),
        )

    seconds = (
        _requested_listen_seconds(
            text
        )
    )

    listener = WindowsListener()

    deadline = (
        time.monotonic()
        + seconds
    )

    heard: list[str] = []

    attempts = 0

    while (
        time.monotonic()
        < deadline
        and attempts < 100
    ):
        remaining = (
            deadline
            - time.monotonic()
        )

        if remaining <= 0:
            break

        window = max(
            1,
            min(
                5,
                int(
                    remaining
                    + 0.999
                ),
            ),
        )

        attempts += 1

        result = (
            listener.listen_once(
                timeout_seconds=window
            )
        )

        if (
            result.ok
            and result.text
        ):
            value = (
                result.text
                .strip()
            )

            # Avoid repeated recognitions producing
            # the same phrase many times.
            if (
                value
                and (
                    not heard
                    or value.casefold()
                    != heard[-1].casefold()
                )
            ):
                heard.append(
                    value
                )

        # Prevent a recognizer returning immediately
        # from forming a CPU-tight loop.
        time.sleep(
            min(
                0.15,
                max(
                    0.0,
                    deadline
                    - time.monotonic()
                ),
            )
        )

    if heard:
        if len(heard) == 1:
            answer = (
                f'I listened for about '
                f'{seconds} seconds and heard: '
                f'"{heard[0]}".'
            )

        else:
            lines = [
                (
                    f"I listened for about "
                    f"{seconds} seconds and "
                    f"recognized these speech segments:"
                )
            ]

            lines.extend(
                f"- {value}"
                for value in heard
            )

            answer = "\n".join(
                lines
            )

    else:
        answer = (
            f"I listened for about "
            f"{seconds} seconds but did not "
            f"recognize clear speech."
        )

    return NativeResult(
        handled=True,
        ok=True,
        capability="audio.listen",
        answer=answer,
        raw={
            "requested_seconds":
                seconds,

            "recognized_segments":
                list(heard),

            # Explicitly state what this provider
            # does NOT prove.
            "speaker_diarization":
                False,

            "speaker_gender_classification":
                False,
        },
    )


def _visual_memory_chunks():
    from integration.sophyane_visual_memory import (
        SophyaneVisualMemory,
    )

    memory = SophyaneVisualMemory()

    return memory.latest_visual_chunks(
        limit=100000,
    )


def _visual_memory_count() -> NativeResult:

    try:
        chunks = (
            _visual_memory_chunks()
        )

    except Exception as exc:
        return NativeResult(
            handled=True,
            ok=False,
            capability="memory.visual.count",
            error=(
                "Neuron visual memory could "
                f"not be opened: {exc}"
            ),
        )

    existing_images = 0

    for chunk in chunks:
        meta = dict(
            getattr(
                chunk,
                "meta",
                {},
            )
            or {}
        )

        path = str(
            meta.get(
                "screenshot_path"
            )
            or ""
        )

        if (
            path
            and Path(
                path
            ).expanduser().is_file()
        ):
            existing_images += 1

    count = len(
        chunks
    )

    if count == 0:
        answer = (
            "My persistent visual memory "
            "currently contains 0 visual "
            "observation chunks."
        )

    else:
        answer = (
            f"My persistent visual memory "
            f"contains {count} visual "
            f"observation chunk"
            f"{'' if count == 1 else 's'}. "
            f"{existing_images} referenced "
            f"screenshot file"
            f"{'' if existing_images == 1 else 's'} "
            f"currently exist on disk."
        )

    return NativeResult(
        handled=True,
        ok=True,
        capability="memory.visual.count",
        answer=answer,
        raw={
            "visual_chunks":
                count,

            "existing_screenshots":
                existing_images,
        },
    )


def _memory_status() -> NativeResult:

    visual = (
        _visual_memory_count()
    )

    try:
        from neuron_reasoning_backend import (
            session_history_count,
        )

        session_items = (
            session_history_count()
        )

    except Exception:
        session_items = 0

    if visual.ok:
        answer = (
            "Yes. Neuron has bounded "
            "in-session conversational memory "
            f"and persistent visual memory. "
            f"This session currently has "
            f"{session_items} stored chat "
            f"entries. "
            + visual.answer
        )

        return NativeResult(
            handled=True,
            ok=True,
            capability="memory.status",
            answer=answer,
            raw={
                "session_entries":
                    session_items,

                **(
                    visual.raw
                    or {}
                ),
            },
        )

    return NativeResult(
        handled=True,
        ok=True,
        capability="memory.status",
        answer=(
            "I have bounded in-session "
            "conversation memory. "
            f"This session currently contains "
            f"{session_items} chat entries. "
            "The persistent visual-memory "
            "store could not be inspected: "
            + visual.error
        ),
    )


def _latest_visual_memory() -> NativeResult:

    try:
        chunks = (
            _visual_memory_chunks()
        )

    except Exception as exc:
        return NativeResult(
            handled=True,
            ok=False,
            capability="memory.visual.latest",
            error=str(exc),
        )

    if not chunks:
        return NativeResult(
            handled=True,
            ok=True,
            capability="memory.visual.latest",
            answer=(
                "I do not currently have "
                "a persisted visual observation "
                "to recall."
            ),
        )

    latest = chunks[-5:]

    lines = [
        "My most recent persisted visual "
        "observations are:"
    ]

    for chunk in reversed(
        latest
    ):
        text = str(
            getattr(
                chunk,
                "text",
                "",
            )
            or ""
        ).strip()

        meta = dict(
            getattr(
                chunk,
                "meta",
                {},
            )
            or {}
        )

        application = str(
            meta.get(
                "application"
            )
            or ""
        ).strip()

        if len(text) > 240:
            text = (
                text[:240]
                + "…"
            )

        label = (
            f"[{application}] "
            if application
            else ""
        )

        lines.append(
            f"- {label}{text}"
        )

    return NativeResult(
        handled=True,
        ok=True,
        capability="memory.visual.latest",
        answer="\n".join(
            lines
        ),
    )


def _camera_scene() -> NativeResult:

    try:
        from neuron_identity_perception import (
            _close_camera,
            _open_camera,
        )

        from desktop.windows_bridge import (
            WindowsBridge,
        )

        from perception.vision_client import (
            VisionClient,
        )

    except Exception as exc:
        return NativeResult(
            handled=True,
            ok=False,
            capability="camera.scene",
            error=(
                "Camera scene observation "
                f"is unavailable: {exc}"
            ),
        )

    opened, error = (
        _open_camera()
    )

    if not opened:
        return NativeResult(
            handled=True,
            ok=False,
            capability="camera.scene",
            error=(
                "Windows Camera could not "
                "be opened: "
                + error
            ),
        )

    screenshot = ""

    try:
        time.sleep(
            3.0
        )

        observation = (
            WindowsBridge()
            .observe_screen()
        )

        if not observation.ok:
            return NativeResult(
                handled=True,
                ok=False,
                capability="camera.scene",
                error=(
                    observation.stderr
                    or (
                        "camera preview capture "
                        "failed"
                    )
                ),
            )

        active = (
            f"{observation.application} "
            f"{observation.window_title}"
        ).casefold()

        if "camera" not in active:
            return NativeResult(
                handled=True,
                ok=False,
                capability="camera.scene",
                error=(
                    "The Windows Camera preview "
                    "did not become the grounded "
                    "foreground window."
                ),
            )

        screenshot = str(
            observation.screenshot_path
            or ""
        )

        result = VisionClient(
            host="127.0.0.1",
            port=8769,
        ).ask_image(
            screenshot,
            (
                "Describe the visible surroundings "
                "shown by the live camera preview. "
                "Use only visible pixels. "
                "Mention major objects and the "
                "number of clearly visible people "
                "if apparent. Do not identify people "
                "and do not infer sensitive traits, "
                "mood, intent, health, or personality."
            ),
        )

        if not result.ok:
            return NativeResult(
                handled=True,
                ok=False,
                capability="camera.scene",
                error=(
                    result.error
                    or result.status
                    or (
                        "local grounded vision "
                        "is unavailable"
                    )
                ),
            )

        return NativeResult(
            handled=True,
            ok=True,
            capability="camera.scene",
            answer=result.answer,
            raw=result.to_dict(),
        )

    finally:
        _close_camera()

        # Scene observation is ephemeral unless
        # another explicit policy-approved path
        # persists it.
        if screenshot:
            try:
                Path(
                    screenshot
                ).unlink()
            except OSError:
                pass


def _multimodal_observe(
    text: str,
) -> NativeResult:

    visual = (
        _camera_scene()
    )

    # A combined "see and hear" query should
    # actually spend time listening rather than
    # return after one utterance.
    seconds = (
        _requested_listen_seconds(
            text
        )
    )

    if seconds == 10:
        audio_text = (
            "listen for 10 seconds"
        )
    else:
        audio_text = (
            f"listen for {seconds} seconds"
        )

    audio = (
        _listen_window(
            audio_text
        )
    )

    parts: list[str] = []

    if visual.ok:
        parts.append(
            "What I see:\n"
            + visual.answer
        )
    else:
        parts.append(
            "Visual observation unavailable:\n"
            + visual.error
        )

    if audio.ok:
        parts.append(
            "What I hear:\n"
            + audio.answer
        )
    else:
        parts.append(
            "Audio observation unavailable:\n"
            + audio.error
        )

    if not (
        visual.ok
        or audio.ok
    ):
        return NativeResult(
            handled=True,
            ok=False,
            capability="multimodal.observe",
            answer="\n\n".join(
                parts
            ),
            error=(
                "Neither grounded camera "
                "nor microphone observation "
                "succeeded."
            ),
        )

    return NativeResult(
        handled=True,
        ok=True,
        partial=not (
            visual.ok
            and audio.ok
        ),
        capability="multimodal.observe",
        answer="\n\n".join(
            parts
        ),
        raw={
            "visual_ok":
                visual.ok,

            "audio_ok":
                audio.ok,
        },
    )


def classify_native(
    text: str,
) -> str:

    lower = _normalise(
        text
    )

    # Combined modality must take precedence
    # over individual audio/screen classifiers.
    combined_markers = (
        "see and hear",
        "see & hear",
        "look and listen",
        "see around and hear",
        "what do you see and hear",
    )

    if any(
        marker in lower
        for marker in combined_markers
    ):
        return "multimodal.observe"

    visual_count_markers = (
        "how many images in your memory",
        "how many image in your memory",
        "how many pictures in your memory",
        "how many photos in your memory",
        "how many visual memories",
        "how many screenshots in your memory",
    )

    if any(
        marker in lower
        for marker in visual_count_markers
    ):
        return "memory.visual.count"

    memory_status_markers = (
        "do you have memory",
        "have you got memory",
        "can you remember",
    )

    if any(
        marker in lower
        for marker in memory_status_markers
    ):
        return "memory.status"

    latest_memory_markers = (
        "what did you see",
        "what do you remember seeing",
        "what have you seen",
        "latest visual memory",
        "recent visual memory",
    )

    if any(
        marker in lower
        for marker in latest_memory_markers
    ):
        return "memory.visual.latest"

    audio_now_markers = (
        "what do you hear now",
        "what you hear now",
        "what can you hear now",
        "listen now",
        "hear now",
        "listen for longer",
        "hear for longer",
        "keep listening",
        "listen for ",
        "hear for ",
    )

    if any(
        marker in lower
        for marker in audio_now_markers
    ):
        return "audio.listen.window"

    return (
        _previous_classify_native_v3(
            text
        )
    )


def handle_native(
    text: str,
) -> NativeResult:

    capability = (
        classify_native(
            text
        )
    )

    if capability == "memory.visual.count":
        return _visual_memory_count()

    if capability == "memory.status":
        return _memory_status()

    if capability == "memory.visual.latest":
        return _latest_visual_memory()

    if capability == "audio.listen.window":
        return _listen_window(
            text
        )

    if capability == "multimodal.observe":
        return _multimodal_observe(
            text
        )

    return (
        _previous_handle_native_v3(
            text
        )
    )
