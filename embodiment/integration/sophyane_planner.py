from __future__ import annotations

import json
from typing import Any


class SophyanePlannerError(RuntimeError):
    pass


class SophyaneCapabilityPlanner:
    """
    Semantic planner for Neuron using Sophyane's authoritative
    Gemini -> local GGUF provider chain.

    Natural language remains unrestricted.
    Capability execution remains typed and validated.
    """

    def __init__(self) -> None:
        self._last_provider = ""
        self._last_model = ""
        self._last_errors: list[str] = []

    @property
    def last_provider(self) -> str:
        return self._last_provider

    @property
    def last_model(self) -> str:
        return self._last_model

    @property
    def last_errors(self) -> list[str]:
        return list(self._last_errors)

    @staticmethod
    def _clean_json_text(text: str) -> str:
        value = str(text or "").strip()

        if value.startswith("```"):
            lines = value.splitlines()

            if lines:
                lines = lines[1:]

            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]

            value = "\n".join(lines).strip()

            if value.lower().startswith("json"):
                value = value[4:].lstrip()

        first = value.find("{")
        last = value.rfind("}")

        if first >= 0 and last > first:
            value = value[first:last + 1]

        return value.strip()

    @staticmethod
    def _compact_capabilities(
        capabilities: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:

        result = []

        for item in capabilities:
            args = []

            for arg in item.get("arguments", []) or []:
                args.append(
                    {
                        "name": arg.get("name"),
                        "type": arg.get("type", "string"),
                        "required": bool(
                            arg.get("required", False)
                        ),
                    }
                )

            result.append(
                {
                    "name": item.get("name"),
                    "description": str(
                        item.get("description", "")
                    )[:220],
                    "arguments": args,
                }
            )

        return result

    @staticmethod
    def build_compact_prompt(
        *,
        user_message: str,
        capabilities: list[dict[str, Any]],
        context: dict[str, Any],
    ) -> str:

        compact_context = {
            "task":
                context.get("current_task"),

            "application":
                context.get("current_application"),

            "screen":
                context.get("screen", {}),

            "identity":
                context.get("identity", {}),

            "avatar":
                context.get("avatar", {}),

            "perception":
                context.get("perception", {}),
        }

        payload = {
            "utterance":
                user_message,

            "context":
                compact_context,

            "capabilities":
                SophyaneCapabilityPlanner
                ._compact_capabilities(
                    capabilities
                ),
        }

        return (
            "Interpret the utterance semantically from context. "
            "Do not phrase-match. Choose only listed capabilities. "
            "Return compact JSON only with keys: "
            "interpretation, confidence, clarification_needed, "
            "clarification_question, steps, reply. "
            "Each step must contain capability, arguments, reason, "
            "confidence, depends_on.\n\n"
            + json.dumps(
                payload,
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )

    def plan(
        self,
        *,
        user_message: str,
        capabilities: list[dict[str, Any]],
        context: dict[str, Any],
    ) -> dict[str, Any]:

        from sophyane.config import (
            load_config,
        )

        from sophyane.main import (
            create_provider,
        )

        from sophyane.runtime_sli_brain import (
            decide,
        )

        sli = decide(
            user_message,
            has_project=False,
        )

        config = load_config()

        #
        # Semantic planning is a compact bounded task.
        #
        # Give local Qwen enough wall time to answer on CPU,
        # but cap output strongly to prevent long generations.
        #

        config = dict(config)

        config["timeout"] = max(
            int(
                config.get(
                    "timeout",
                    180,
                )
                or 180
            ),
            180,
        )

        config["max_tokens"] = 384

        provider = create_provider(
            config
        )

        prompt = self.build_compact_prompt(
            user_message=user_message,
            capabilities=capabilities,
            context=context,
        )

        system_prompt = (
            "SOPHYANE_RESPONSE_MODE: chat\n"
            "You are Neuron's semantic capability planner. "
            "Return one compact valid JSON object only. "
            "Never claim execution occurred."
        )

        text = provider.generate(
            prompt,
            system_prompt,
        )

        self._last_provider = str(
            getattr(
                provider,
                "last_provider",
                "",
            )
            or getattr(
                provider,
                "primary",
                "",
            )
        )

        self._last_model = str(
            getattr(
                provider,
                "model",
                "",
            )
        )

        self._last_errors = list(
            getattr(
                provider,
                "last_errors",
                [],
            )
            or []
        )

        cleaned = self._clean_json_text(
            text
        )

        try:
            result = json.loads(
                cleaned
            )

        except Exception as exc:
            raise SophyanePlannerError(
                "invalid planner JSON: "
                + cleaned[:1200]
            ) from exc

        if not isinstance(
            result,
            dict,
        ):
            raise SophyanePlannerError(
                "planner result is not an object"
            )

        result["_routing"] = {
            "provider":
                self._last_provider,

            "model":
                self._last_model,

            "errors":
                self._last_errors,

            "sli": {
                "route":
                    getattr(
                        sli,
                        "route",
                        "",
                    ),

                "profile":
                    getattr(
                        sli,
                        "profile",
                        "",
                    ),

                "refined_request":
                    getattr(
                        sli,
                        "refined_request",
                        user_message,
                    ),

                "criteria":
                    list(
                        getattr(
                            sli,
                            "criteria",
                            (),
                        )
                    ),
            },
        }

        return result
