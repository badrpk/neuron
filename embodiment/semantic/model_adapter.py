from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


class SemanticModelError(RuntimeError):
    pass


class OpenAICompatiblePlanner:
    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str | None = None,
        timeout: float = 45.0,
    ) -> None:

        self.base_url = (
            base_url.rstrip("/")
        )

        self.model = model

        self.api_key = api_key

        self.timeout = timeout

    def plan(
        self,
        prompt: str,
    ) -> dict[str, Any]:

        url = (
            self.base_url
            + "/v1/chat/completions"
        )

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Return strict JSON only."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "temperature": 0.1,
        }

        body = json.dumps(
            payload
        ).encode(
            "utf-8"
        )

        request = urllib.request.Request(
            url,
            data=body,
            method="POST",
        )

        request.add_header(
            "Content-Type",
            "application/json",
        )

        if self.api_key:
            request.add_header(
                "Authorization",
                "Bearer "
                + self.api_key,
            )

        try:
            with urllib.request.urlopen(
                request,
                timeout=self.timeout,
            ) as response:

                raw = response.read()

        except Exception as exc:
            raise SemanticModelError(
                str(exc)
            ) from exc

        data = json.loads(
            raw.decode(
                "utf-8"
            )
        )

        try:
            text = (
                data[
                    "choices"
                ][0][
                    "message"
                ][
                    "content"
                ]
            )

        except Exception as exc:
            raise SemanticModelError(
                "unexpected model response"
            ) from exc

        text = text.strip()

        if text.startswith("```"):

            lines = text.splitlines()

            if lines:
                lines = lines[1:]

            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]

            text = "\n".join(
                lines
            )

            if text.lstrip().startswith(
                "json"
            ):
                text = text.lstrip()[4:]

        try:
            return json.loads(
                text
            )

        except Exception as exc:
            raise SemanticModelError(
                "planner returned non-JSON content"
            ) from exc


def from_environment() -> OpenAICompatiblePlanner | None:

    base = os.getenv(
        "NEURON_SEMANTIC_BASE_URL",
        "",
    ).strip()

    model = os.getenv(
        "NEURON_SEMANTIC_MODEL",
        "",
    ).strip()

    key = os.getenv(
        "NEURON_SEMANTIC_API_KEY",
        "",
    ).strip()

    if not base or not model:
        return None

    return OpenAICompatiblePlanner(
        base_url=base,
        model=model,
        api_key=key or None,
    )
