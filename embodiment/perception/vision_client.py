from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass
class VisionQuestionResult:
    ok: bool
    capability: str = "screen.visual_question"
    provider: str = "neuron.vision"
    question: str = ""
    answer: str = ""
    screenshot_path: str = ""
    model_endpoint: str = ""
    status: str = ""
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class VisionClient:
    """
    Grounded local multimodal client.

    Sends full image pixels to llama.cpp's OpenAI-compatible
    multimodal endpoint. It never fabricates an answer when
    image transport or inference fails.
    """

    def __init__(
        self,
        *,
        host: str = "127.0.0.1",
        port: int = 8769,
        timeout: float = 300.0,
    ) -> None:
        self.host = host
        self.port = int(port)
        self.timeout = float(timeout)

        # NEURON_VISION_TIMEOUT_ENV_V1
        self.timeout = float(
            os.environ.get(
                "NEURON_VISION_TIMEOUT",
                str(self.timeout),
            )
        )

    @property
    def base_url(self) -> str:
        return (
            f"http://{self.host}:{self.port}"
        )

    def ask_image(
        self,
        image_path: str,
        question: str,
    ) -> VisionQuestionResult:

        question = str(
            question or ""
        ).strip()

        if not question:
            return VisionQuestionResult(
                ok=False,
                question="",
                status="invalid_question",
                error="visual question is empty",
            )

        path = Path(
            image_path
        ).expanduser().resolve()

        if not path.is_file():
            return VisionQuestionResult(
                ok=False,
                question=question,
                screenshot_path=str(path),
                status="missing_screenshot",
                error=(
                    "grounded screenshot does not exist"
                ),
            )

        try:
            raw = path.read_bytes()
        except Exception as exc:
            return VisionQuestionResult(
                ok=False,
                question=question,
                screenshot_path=str(path),
                status="screenshot_read_failed",
                error=str(exc),
            )

        if not raw.startswith(
            b"\x89PNG\r\n\x1a\n"
        ):
            return VisionQuestionResult(
                ok=False,
                question=question,
                screenshot_path=str(path),
                status="invalid_screenshot",
                error="grounded screenshot is not PNG",
            )

        encoded = base64.b64encode(
            raw
        ).decode("ascii")

        payload = {
            "messages": [
                {
                    "role":
                        "user",

                    "content": [
                        {
                            "type":
                                "image_url",

                            "image_url": {
                                "url": (
                                    "data:image/png;base64,"
                                    + encoded
                                )
                            },
                        },
                        {
                            "type":
                                "text",

                            "text": (
                                "Answer the following question "
                                "strictly from the visible pixels "
                                "in this screenshot. "
                                "Do not infer from the filename, "
                                "filesystem, runtime state, or "
                                "external context. "
                                "If the pixels do not support the "
                                "answer, say that clearly.\n\n"
                                f"Question: {question}"
                            ),
                        },
                    ],
                }
            ],
            "temperature": 0,
            "max_tokens": 384,
        }

        body = json.dumps(
            payload
        ).encode("utf-8")

        endpoint = (
            self.base_url
            + "/v1/chat/completions"
        )

        request = urllib.request.Request(
            endpoint,
            data=body,
            headers={
                "Content-Type":
                    "application/json",
            },
            method="POST",
        )

        #
        # NEURON_VISION_LOADING_RETRY_V2
        #
        # llama.cpp can expose /v1/models before Gemma has finished
        # loading the multimodal model. Retry ONLY the specific
        # transient 503 "Loading model" response.
        #
        max_loading_attempts = 90
        loading_retry_seconds = 2.0
        raw_response = None

        for loading_attempt in range(
            1,
            max_loading_attempts + 1,
        ):
            try:
                with urllib.request.urlopen(
                    request,
                    timeout=self.timeout,
                ) as response:
                    raw_response = (
                        response.read()
                    )

                break

            except urllib.error.HTTPError as exc:
                try:
                    detail = (
                        exc.read()
                        .decode(
                            "utf-8",
                            errors="replace",
                        )
                    )
                except Exception:
                    detail = str(exc)

                transient_loading = (
                    exc.code == 503
                    and "Loading model" in detail
                )

                if (
                    transient_loading
                    and loading_attempt
                    < max_loading_attempts
                ):
                    time.sleep(
                        loading_retry_seconds
                    )
                    continue

                return VisionQuestionResult(
                    ok=False,
                    question=question,
                    screenshot_path=str(path),
                    model_endpoint=endpoint,
                    status="vision_http_error",
                    error=detail,
                )

            except Exception as exc:
                return VisionQuestionResult(
                    ok=False,
                    question=question,
                    screenshot_path=str(path),
                    model_endpoint=endpoint,
                    status="vision_unavailable",
                    error=str(exc),
                )

        if raw_response is None:
            return VisionQuestionResult(
                ok=False,
                question=question,
                screenshot_path=str(path),
                model_endpoint=endpoint,
                status="vision_http_error",
                error=(
                    "Gemma multimodal model did not become "
                    "ready after loading retries"
                ),
            )

        try:
            data = json.loads(
                raw_response
            )

            choices = data.get(
                "choices",
                [],
            )

            if not choices:
                raise ValueError(
                    "vision response has no choices"
                )

            content = (
                choices[0]
                .get(
                    "message",
                    {},
                )
                .get(
                    "content",
                    "",
                )
            )

            if isinstance(
                content,
                list,
            ):
                pieces: list[str] = []

                for item in content:
                    if isinstance(
                        item,
                        dict,
                    ):
                        value = (
                            item.get("text")
                            or
                            item.get("content")
                            or
                            ""
                        )

                        if value:
                            pieces.append(
                                str(value)
                            )

                content = "\n".join(
                    pieces
                )

            answer = str(
                content
            ).strip()

            if not answer:
                raise ValueError(
                    "vision response is empty"
                )

        except Exception as exc:
            return VisionQuestionResult(
                ok=False,
                question=question,
                screenshot_path=str(path),
                model_endpoint=endpoint,
                status="invalid_vision_response",
                error=str(exc),
            )

        return VisionQuestionResult(
            ok=True,
            question=question,
            answer=answer,
            screenshot_path=str(path),
            model_endpoint=endpoint,
            status="grounded_visual_answer",
            error="",
        )
