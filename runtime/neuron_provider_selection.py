from __future__ import annotations

from dataclasses import dataclass
import getpass
import json
import os
from pathlib import Path
import signal
import time


CONFIG_DIR = Path.home() / ".config/sophyane"
CONFIG_FILE = CONFIG_DIR / "config.json"
LLM_FILE = CONFIG_DIR / "llm.json"
SECRETS_FILE = CONFIG_DIR / "secrets.json"

STATE_DIR = Path.home() / ".local/state/sophyane"
GGUF_STATE = STATE_DIR / "gguf_runtime.json"
PID_FILE = STATE_DIR / "llama-server.pid"
START_FILE = STATE_DIR / "llama-server.started"
LOCK_FILE = STATE_DIR / "llama-server.starting"


CLOUDS = {
    "gemini": {
        "label": "Google Gemini",
        "env": (
            "GEMINI_API_KEY",
            "GOOGLE_API_KEY",
        ),
        "models": (
            "gemini-3.7-flash",
            "gemini-3.6-flash",
            "gemini-3.6-pro",
            "gemini-2.5-flash",
            "gemini-2.5-pro",
        ),
    },
    "openai": {
        "label": "OpenAI",
        "env": ("OPENAI_API_KEY",),
        "models": (
            "gpt-4.1",
            "gpt-4.1-mini",
            "o3",
        ),
    },
    "anthropic": {
        "label": "Anthropic Claude",
        "env": ("ANTHROPIC_API_KEY",),
        "models": (
            "claude-sonnet-4-20250514",
            "claude-opus-4-20250514",
            "claude-3-5-haiku-latest",
        ),
    },
    "xai": {
        "label": "xAI / Grok",
        "env": ("XAI_API_KEY",),
        "models": (
            "grok-3",
            "grok-3-mini",
        ),
    },
    "deepseek": {
        "label": "DeepSeek",
        "env": ("DEEPSEEK_API_KEY",),
        "models": (
            "deepseek-chat",
            "deepseek-reasoner",
        ),
    },
    "groq": {
        "label": "Groq",
        "env": ("GROQ_API_KEY",),
        "models": (
            "llama-3.3-70b-versatile",
            "qwen-qwq-32b",
        ),
    },
    "openrouter": {
        "label": "OpenRouter",
        "env": ("OPENROUTER_API_KEY",),
        "models": (
            "openrouter/auto",
            "meta-llama/llama-3.3-70b-instruct",
            "deepseek/deepseek-r1",
            "qwen/qwen-2.5-coder-32b-instruct",
        ),
    },
}


KNOWN_PROVIDER_IDS = (
    "gemini",
    "openai",
    "anthropic",
    "xai",
    "deepseek",
    "groq",
    "openrouter",
    "local_gguf",
)


@dataclass(frozen=True)
class ProviderSelection:
    mode: str
    provider: str
    model: str
    label: str
    gguf_path: str = ""

    def environment(self) -> dict[str, str]:
        env = {
            "NEURON_PROVIDER": self.provider,
            "NEURON_MODEL": self.model,
        }

        if self.provider == "local_gguf":
            env.update(
                {
                    "SOPHYANE_SESSION_MODE":
                        "local_llm",
                    "SOPHYANE_LOCAL_ONLY":
                        "1",
                    "SOPHYANE_DISABLE_CLOUD_FALLBACK":
                        "1",
                }
            )

            if self.gguf_path:
                env["SOPHYANE_GGUF_PATH"] = (
                    self.gguf_path
                )

        else:
            env.update(
                {
                    "SOPHYANE_SESSION_MODE":
                        "cloud_llm",
                    "SOPHYANE_DISABLE_LOCAL_FALLBACK":
                        "1",
                    "SOPHYANE_ALLOW_CLOUD_LOCAL_RESCUE":
                        "0",
                }
            )

        return env


def _load_json(path: Path) -> dict:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8")
        )
    except (
        OSError,
        json.JSONDecodeError,
    ):
        return {}

    return value if isinstance(value, dict) else {}


def _save_json(
    path: Path,
    value: dict,
    *,
    private: bool = True,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = path.with_suffix(
        path.suffix + ".tmp"
    )

    temporary.write_text(
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    temporary.replace(path)

    if private:
        try:
            path.chmod(0o600)
        except OSError:
            pass


def _size(path: Path) -> str:
    try:
        count = path.stat().st_size
    except OSError:
        return "?"

    gb = count / (1024 ** 3)

    if gb >= 1:
        return f"{gb:.1f} GB"

    return (
        f"{count / (1024 ** 2):.0f} MB"
    )


def discover_local_models() -> list[Path]:
    result: list[Path] = []
    seen: set[str] = set()

    state = _load_json(GGUF_STATE)

    state_path = str(
        state.get("gguf_path")
        or ""
    ).strip()

    if state_path:
        path = Path(
            state_path
        ).expanduser()

        if path.is_file():
            resolved = str(path.resolve())
            seen.add(resolved)
            result.append(path.resolve())

    roots = (
        Path.home()
        / ".local/share/sophyane/models/gguf",

        Path.home()
        / ".local/share/sophyane/models",

        Path.home() / "models",

        Path.home()
        / "sophyane/models",
    )

    for root in roots:
        if not root.is_dir():
            continue

        try:
            paths = root.rglob("*.gguf")
        except OSError:
            continue

        for path in paths:
            try:
                if not path.is_file():
                    continue

                resolved = str(path.resolve())

            except OSError:
                continue

            if resolved in seen:
                continue

            seen.add(resolved)
            result.append(
                Path(resolved)
            )

    return result


def _secret_present(provider: str) -> bool:
    data = _load_json(SECRETS_FILE)

    if str(
        data.get(provider)
        or ""
    ).strip():
        return True

    info = CLOUDS.get(provider) or {}

    for variable in info.get(
        "env",
        (),
    ):
        if os.environ.get(
            variable,
            "",
        ).strip():
            return True

    if provider == "gemini":
        for alias in (
            "google",
            "GOOGLE_API_KEY",
            "GEMINI_API_KEY",
        ):
            if str(
                data.get(alias)
                or ""
            ).strip():
                return True

    return False


def _write_secret(
    provider: str,
    api_key: str,
) -> None:
    secrets = _load_json(
        SECRETS_FILE
    )

    secrets[provider] = api_key

    _save_json(
        SECRETS_FILE,
        secrets,
        private=True,
    )


def _ask_number(
    prompt: str,
    minimum: int,
    maximum: int,
    *,
    default: int | None = None,
) -> int:
    while True:
        value = input(prompt).strip()

        if (
            not value
            and default is not None
        ):
            return default

        try:
            number = int(value)
        except ValueError:
            print("Enter a valid number.")
            continue

        if minimum <= number <= maximum:
            return number

        print(
            f"Enter a number from "
            f"{minimum} to {maximum}."
        )


def _stop_managed_llama_server() -> None:
    try:
        pid = int(
            PID_FILE.read_text(
                encoding="utf-8"
            ).strip()
        )
    except (
        OSError,
        ValueError,
    ):
        pid = 0

    if pid > 0:
        cmdline = ""

        try:
            cmdline = (
                Path(f"/proc/{pid}/cmdline")
                .read_bytes()
                .replace(b"\0", b" ")
                .decode(
                    "utf-8",
                    errors="replace",
                )
            )
        except OSError:
            pass

        # Never kill an arbitrary reused PID.
        if "llama-server" in cmdline:
            try:
                os.killpg(
                    pid,
                    signal.SIGTERM,
                )
            except OSError:
                try:
                    os.kill(
                        pid,
                        signal.SIGTERM,
                    )
                except OSError:
                    pass

            deadline = (
                time.monotonic()
                + 3.0
            )

            while (
                time.monotonic()
                < deadline
            ):
                try:
                    os.kill(pid, 0)
                except OSError:
                    break

                time.sleep(0.1)

    for path in (
        PID_FILE,
        START_FILE,
        LOCK_FILE,
    ):
        try:
            path.unlink()
        except OSError:
            pass


def _select_local(
    models: list[Path],
) -> ProviderSelection | None:
    if not models:
        print()
        print(
            "No local GGUF models were "
            "detected."
        )
        print(
            "Expected models under "
            "~/.local/share/sophyane/"
            "models/gguf/"
        )
        return None

    print()
    print("Available local LLMs")
    print("────────────────────")

    for index, path in enumerate(
        models,
        1,
    ):
        print(
            f"  {index}. "
            f"{path.name} "
            f"[{_size(path)}]"
        )

    print("  0. Back")

    selected = _ask_number(
        f"Select local model "
        f"[0-{len(models)}]: ",
        0,
        len(models),
    )

    if selected == 0:
        return None

    path = models[selected - 1]

    old_state = _load_json(
        GGUF_STATE
    )

    old_path = str(
        old_state.get("gguf_path")
        or ""
    ).strip()

    state = dict(old_state)

    state.update(
        {
            "gguf_path":
                str(path),
            "model":
                path.stem,
            "endpoint":
                str(
                    state.get("endpoint")
                    or
                    "http://127.0.0.1:8766"
                ),
            "context":
                int(
                    state.get("context")
                    or 8192
                ),
            "parallel":
                int(
                    state.get("parallel")
                    or 1
                ),
        }
    )

    GGUF_STATE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    _save_json(
        GGUF_STATE,
        state,
        private=True,
    )

    if (
        old_path
        and Path(old_path).expanduser()
            != path
    ):
        _stop_managed_llama_server()

    config = _load_json(
        CONFIG_FILE
    )

    config.update(
        {
            "provider":
                "local_gguf",
            "model":
                path.stem,
            "company":
                "Local / llama.cpp",
            "timeout":
                600,
            "temperature":
                float(
                    config.get(
                        "temperature",
                        0.3,
                    )
                ),
            "max_tokens":
                int(
                    config.get(
                        "max_tokens",
                        4096,
                    )
                ),
        }
    )

    _save_json(
        CONFIG_FILE,
        config,
        private=True,
    )

    llm = _load_json(
        LLM_FILE
    )

    llm["active_provider"] = (
        "local_gguf"
    )
    llm["fallback_order"] = [
        "local_gguf"
    ]
    llm["allow_quality_escalation"] = (
        False
    )
    llm["quality_rescue_provider"] = ""
    llm["allow_local_fallbacks"] = False
    llm["allow_cloud_local_rescue"] = False

    providers = llm.setdefault(
        "providers",
        {},
    )

    if isinstance(providers, dict):
        local = providers.setdefault(
            "local_gguf",
            {},
        )

        if isinstance(local, dict):
            local["enabled"] = True
            local["model"] = (
                path.stem
            )

    _save_json(
        LLM_FILE,
        llm,
        private=True,
    )

    return ProviderSelection(
        mode="local",
        provider="local_gguf",
        model=path.stem,
        label=f"Local · {path.name}",
        gguf_path=str(path),
    )


def _cloud_model(
    provider: str,
) -> str | None:
    info = CLOUDS[provider]

    models = list(
        info["models"]
    )

    config = _load_json(
        CONFIG_FILE
    )

    current_provider = str(
        config.get("provider")
        or ""
    )

    current_model = str(
        config.get("model")
        or ""
    ).strip()

    if (
        current_provider == provider
        and current_model
        and current_model
            not in models
    ):
        models.insert(
            0,
            current_model,
        )

    print()
    print(
        f"{info['label']} models"
    )
    print(
        "─"
        * min(
            60,
            len(info["label"]) + 7,
        )
    )

    for index, model in enumerate(
        models,
        1,
    ):
        suffix = ""

        if model == current_model:
            suffix = "  [current]"

        print(
            f"  {index}. "
            f"{model}"
            f"{suffix}"
        )

    custom = len(models) + 1

    print(
        f"  {custom}. "
        f"Enter custom model ID"
    )
    print("  0. Back")

    selected = _ask_number(
        f"Select model "
        f"[0-{custom}]: ",
        0,
        custom,
    )

    if selected == 0:
        return None

    if selected == custom:
        value = input(
            "Model ID: "
        ).strip()

        return value or None

    return models[selected - 1]


def _select_cloud() -> ProviderSelection | None:
    provider_ids = list(
        CLOUDS
    )

    print()
    print("Cloud APIs")
    print("──────────")

    for index, provider in enumerate(
        provider_ids,
        1,
    ):
        status = (
            "✓ configured"
            if _secret_present(provider)
            else "not configured"
        )

        print(
            f"  {index}. "
            f"{CLOUDS[provider]['label']} "
            f"[{status}]"
        )

    print("  0. Back")

    selected = _ask_number(
        f"Select cloud provider "
        f"[0-{len(provider_ids)}]: ",
        0,
        len(provider_ids),
    )

    if selected == 0:
        return None

    provider = (
        provider_ids[
            selected - 1
        ]
    )

    info = CLOUDS[provider]

    if _secret_present(provider):
        answer = input(
            "Use currently configured API "
            "credential? [Y/n]: "
        ).strip().lower()

        replace = (
            answer
            not in {
                "",
                "y",
                "yes",
            }
        )

    else:
        replace = True

    if replace:
        key = getpass.getpass(
            f"{info['label']} API key: "
        ).strip()

        if not key:
            print(
                "API key cannot be empty."
            )
            return None

        _write_secret(
            provider,
            key,
        )

        print(
            "API credential stored with "
            "user-only permissions."
        )

    model = _cloud_model(
        provider
    )

    if not model:
        return None

    config = _load_json(
        CONFIG_FILE
    )

    config.update(
        {
            "provider":
                provider,
            "model":
                model,
            "company":
                info["label"],
            "timeout":
                300,
            "temperature":
                float(
                    config.get(
                        "temperature",
                        0.3,
                    )
                ),
            "max_tokens":
                int(
                    config.get(
                        "max_tokens",
                        4096,
                    )
                ),
        }
    )

    _save_json(
        CONFIG_FILE,
        config,
        private=True,
    )

    llm = _load_json(
        LLM_FILE
    )

    llm["active_provider"] = provider
    llm["fallback_order"] = [
        provider
    ]
    llm["allow_quality_escalation"] = (
        False
    )
    llm["quality_rescue_provider"] = ""
    llm["allow_local_fallbacks"] = False
    llm["allow_cloud_local_rescue"] = False

    providers = llm.setdefault(
        "providers",
        {},
    )

    if isinstance(providers, dict):
        # Explicit Neuron selection is authoritative.
        # Do not silently fall through to another
        # configured cloud or to local inference.
        for provider_id in KNOWN_PROVIDER_IDS:
            entry = providers.setdefault(
                provider_id,
                {},
            )

            if isinstance(entry, dict):
                entry["enabled"] = (
                    provider_id
                    == provider
                )

        selected_cfg = providers.setdefault(
            provider,
            {},
        )

        if isinstance(
            selected_cfg,
            dict,
        ):
            selected_cfg["enabled"] = True
            selected_cfg["model"] = model

    _save_json(
        LLM_FILE,
        llm,
        private=True,
    )

    return ProviderSelection(
        mode="cloud",
        provider=provider,
        model=model,
        label=(
            f"{info['label']} · "
            f"{model}"
        ),
    )


def current_provider() -> ProviderSelection:
    config = _load_json(
        CONFIG_FILE
    )

    provider = str(
        config.get("provider")
        or "local_gguf"
    ).strip()

    model = str(
        config.get("model")
        or "not configured"
    ).strip()

    if provider == "local_gguf":
        state = _load_json(
            GGUF_STATE
        )

        path = str(
            state.get("gguf_path")
            or ""
        ).strip()

        return ProviderSelection(
            mode="local",
            provider=provider,
            model=(
                str(
                    state.get("model")
                    or model
                )
            ),
            label=(
                f"Local · "
                f"{Path(path).name}"
                if path
                else
                f"Local · {model}"
            ),
            gguf_path=path,
        )

    label = (
        CLOUDS
        .get(
            provider,
            {},
        )
        .get(
            "label",
            provider,
        )
    )

    return ProviderSelection(
        mode="cloud",
        provider=provider,
        model=model,
        label=f"{label} · {model}",
    )


def select_startup_provider() -> ProviderSelection:
    if not os.isatty(0):
        return current_provider()

    while True:
        models = discover_local_models()
        current = current_provider()

        print()
        print(
            "╭──────────────────────────────────────────────╮"
        )
        print(
            "│  NEURON · SELECT INTELLIGENCE                │"
        )
        print(
            "╰──────────────────────────────────────────────╯"
        )
        print()

        print(
            f" Current: {current.label}"
        )
        print()

        if models:
            print(
                f"  1. Local LLM "
                f"— {len(models)} GGUF "
                f"model"
                f"{'' if len(models) == 1 else 's'} "
                f"detected"
            )
        else:
            print(
                "  1. Local LLM "
                "— no GGUF models detected"
            )

        configured_clouds = sum(
            1
            for provider in CLOUDS
            if _secret_present(provider)
        )

        print(
            f"  2. Cloud API "
            f"— {configured_clouds} "
            f"configured"
        )

        print(
            "  3. Keep current selection"
        )
        print(
            "  0. Exit"
        )
        print()

        default = (
            1
            if models
            else 2
        )

        answer = _ask_number(
            f"Select [0-3, default {default}]: ",
            0,
            3,
            default=default,
        )

        if answer == 0:
            raise SystemExit(0)

        if answer == 3:
            return current

        if answer == 1:
            selected = _select_local(
                models
            )

            if selected:
                return selected

        if answer == 2:
            selected = _select_cloud()

            if selected:
                return selected
