from __future__ import annotations

import json
import os
import time
import urllib.request
from dataclasses import asdict
from pathlib import Path
from typing import Any


class SophyaneSemanticError(RuntimeError):
    pass


class SophyaneSemanticAdapter:
    """
    Neuron semantic bridge.

    Responsibilities:
      1. Let Sophyane SLI inspect the natural-language request.
      2. Use Sophyane's configured primary provider path.
      3. Fall back to the existing local llama.cpp Qwen 7B service.
      4. Return model text plus routing provenance.

    Neuron does not phrase-match user language here.
    """

    def __init__(
        self,
        *,
        qwen_base_url: str | None = None,
        qwen_model: str | None = None,
        timeout: float = 60.0,
    ) -> None:

        self.qwen_base_url = (
            qwen_base_url
            or os.environ.get(
                "SOPHYANE_LLAMA_SERVER",
                "http://127.0.0.1:8766",
            )
        ).rstrip("/")

        self.qwen_model = (
            qwen_model
            or os.environ.get(
                "SOPHYANE_LOCAL_FALLBACK_MODEL",
                "qwen2.5-7b-instruct",
            )
        )

        self.timeout = timeout

    def sli_decision(
        self,
        message: str,
        *,
        has_project: bool = False,
    ) -> dict[str, Any]:

        from sophyane.runtime_sli_brain import decide

        decision = decide(
            message,
            has_project=has_project,
        )

        try:
            return asdict(decision)
        except Exception:
            return {
                "route":
                    getattr(
                        decision,
                        "route",
                        "",
                    ),

                "profile":
                    getattr(
                        decision,
                        "profile",
                        "",
                    ),

                "refined_request":
                    getattr(
                        decision,
                        "refined_request",
                        message,
                    ),

                "criteria":
                    list(
                        getattr(
                            decision,
                            "criteria",
                            (),
                        )
                    ),
            }

    def sophyane_primary(
        self,
        prompt: str,
        system_prompt: str = "",
    ) -> dict[str, Any]:

        """
        Invoke Sophyane's configured provider path.

        We intentionally discover/import the actual provider factory
        at runtime rather than duplicating Gemini credentials in Neuron.
        """

        errors: list[str] = []

        #
        # Candidate 1:
        # main.create_provider(...) is already used by Sophyane tests.
        #

        try:
            from sophyane import main as sophyane_main

            create_provider = getattr(
                sophyane_main,
                "create_provider",
                None,
            )

            if callable(create_provider):

                from sophyane.llm_catalog import load_llm_config

                config = load_llm_config() or {}

                llm = config.get(
                    "llm",
                    config,
                )

                provider_name = (
                    llm.get("provider")
                    or
                    llm.get("active_provider")
                    or
                    ""
                )

                model_name = (
                    llm.get("model")
                    or
                    llm.get("configured_model")
                    or
                    ""
                )

                if provider_name:

                    provider = create_provider(
                        {
                            "provider":
                                provider_name,

                            "model":
                                model_name,
                        }
                    )

                    if provider is not None:

                        generate = getattr(
                            provider,
                            "generate",
                            None,
                        )

                        if callable(generate):

                            t0 = time.perf_counter()

                            text = generate(
                                prompt,
                                system_prompt,
                            )

                            elapsed = (
                                time.perf_counter()
                                - t0
                            ) * 1000.0

                            if not isinstance(
                                text,
                                str,
                            ):
                                text = getattr(
                                    text,
                                    "text",
                                    str(text),
                                )

                            if text.strip():

                                return {
                                    "ok": True,
                                    "provider":
                                        provider_name,

                                    "model":
                                        model_name,

                                    "text":
                                        text,

                                    "latency_ms":
                                        elapsed,
                                }

        except Exception as exc:
            errors.append(
                "create_provider: "
                + repr(exc)
            )

        #
        # Candidate 2:
        # provider modules may expose a configured generate surface.
        #

        try:
            from sophyane.provider_state import snapshot

            state = snapshot()

            errors.append(
                "provider_state="
                + json.dumps(
                    state,
                    default=str,
                )
            )

        except Exception as exc:
            errors.append(
                "provider_state: "
                + repr(exc)
            )

        raise SophyaneSemanticError(
            "Sophyane primary unavailable: "
            + "; ".join(errors)
        )

    def qwen_fallback(
        self,
        prompt: str,
        system_prompt: str = "",
    ) -> dict[str, Any]:

        messages = []

        if system_prompt.strip():
            messages.append(
                {
                    "role":
                        "system",

                    "content":
                        system_prompt,
                }
            )

        messages.append(
            {
                "role":
                    "user",

                "content":
                    prompt,
            }
        )

        payload = {
            "model":
                self.qwen_model,

            "messages":
                messages,

            "temperature":
                0.1,
        }

        request = urllib.request.Request(
            self.qwen_base_url
            + "/v1/chat/completions",

            data=json.dumps(
                payload
            ).encode(
                "utf-8"
            ),

            headers={
                "Content-Type":
                    "application/json",
            },

            method="POST",
        )

        t0 = time.perf_counter()

        with urllib.request.urlopen(
            request,
            timeout=self.timeout,
        ) as response:

            raw = response.read()

        elapsed = (
            time.perf_counter()
            - t0
        ) * 1000.0

        data = json.loads(
            raw.decode(
                "utf-8"
            )
        )

        text = (
            data.get(
                "choices",
                [{}],
            )[0]
            .get(
                "message",
                {},
            )
            .get(
                "content",
                "",
            )
        )

        if not str(text).strip():
            raise SophyaneSemanticError(
                "Qwen fallback returned empty content"
            )

        return {
            "ok":
                True,

            "provider":
                "local_gguf",

            "model":
                self.qwen_model,

            "text":
                str(text),

            "latency_ms":
                elapsed,

            "fallback":
                True,
        }

    def generate(
        self,
        prompt: str,
        *,
        system_prompt: str = "",
        user_message: str = "",
        has_project: bool = False,
        force_fallback: bool = False,
    ) -> dict[str, Any]:

        sli = self.sli_decision(
            user_message or prompt,
            has_project=has_project,
        )

        primary_error = None

        if not force_fallback:

            try:

                primary = self.sophyane_primary(
                    prompt,
                    system_prompt,
                )

                return {
                    **primary,

                    "fallback":
                        False,

                    "sli":
                        sli,
                }

            except Exception as exc:
                primary_error = repr(exc)

        fallback = self.qwen_fallback(
            prompt,
            system_prompt,
        )

        fallback["sli"] = sli

        fallback[
            "primary_error"
        ] = primary_error

        return fallback
