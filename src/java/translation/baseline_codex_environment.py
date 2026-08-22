"""Create a temporary Codex home for reproducible baseline runs."""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class CodexEnvironmentError(RuntimeError):
    """Raised when an isolated Codex environment cannot be prepared."""


# Keep experiment tuning local to each temporary CODEX_HOME.
EXPERIMENT_MODEL = "gpt-5.6-terra"
EXPERIMENT_REASONING_EFFORT = "medium"


@dataclass
class CodexEnvironment:
    home: Path
    config_text: str
    _temporary_directory: tempfile.TemporaryDirectory[str]
    telemetry_dir: Path | None = None
    telemetry_stage: str = "unknown"

    @property
    def environment(self) -> dict[str, str]:
        return {"CODEX_HOME": str(self.home)}

    def __enter__(self) -> "CodexEnvironment":
        return self

    def __exit__(self, _exc_type, _exc, _traceback) -> None:
        self._preserve_rollouts()
        self._temporary_directory.cleanup()

    def _preserve_rollouts(self) -> None:
        if self.telemetry_dir is None:
            return
        sessions = self.home / "sessions"
        if not sessions.is_dir():
            return
        destination = self.telemetry_dir / self.telemetry_stage / "sessions"
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(sessions, destination, dirs_exist_ok=True)


def create_codex_environment(
    source_home: str | Path | None,
    workspace: str | Path,
) -> CodexEnvironment:
    """Create an isolated Codex home using only experiment-safe settings."""
    source = Path(source_home or os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    source = source.expanduser().resolve()
    auth_path = source / "auth.json"
    if not auth_path.is_file():
        raise CodexEnvironmentError(
            f"Codex authentication file not found at {auth_path}; "
            "refusing to fall back to the personal Codex home"
        )

    temporary_directory = tempfile.TemporaryDirectory(prefix="x2cangjie-codex-home-")
    home = Path(temporary_directory.name)
    try:
        auth_target = home / "auth.json"
        shutil.copy2(auth_path, auth_target)
        try:
            auth_target.chmod(0o600)
        except OSError:
            pass

        config_text = _minimal_config(source / "config.toml", Path(workspace).resolve())
        (home / "config.toml").write_text(config_text, encoding="utf-8")
    except Exception:
        temporary_directory.cleanup()
        raise

    telemetry_root = os.environ.get("X2CANGJIE_CODEX_TELEMETRY_DIR", "").strip()
    telemetry_dir = Path(telemetry_root).expanduser().resolve() if telemetry_root else None
    telemetry_stage = os.environ.get("X2CANGJIE_CODEX_STAGE", "unknown").strip() or "unknown"
    return CodexEnvironment(home, config_text, temporary_directory, telemetry_dir, telemetry_stage)


def _minimal_config(source_config: Path, workspace: Path) -> str:
    source: dict[str, Any] = {}
    if source_config.is_file():
        try:
            loaded = tomllib.loads(source_config.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError) as exc:
            raise CodexEnvironmentError(
                f"cannot read Codex config {source_config}: {exc}"
            ) from exc
        if isinstance(loaded, dict):
            source = loaded

    lines: list[str] = []
    overrides = {
        "model": EXPERIMENT_MODEL,
        "model_reasoning_effort": EXPERIMENT_REASONING_EFFORT,
    }
    for key in (
        "model_provider",
        "model",
        "model_reasoning_effort",
        "network_access",
        "service_tier",
        "disable_response_storage",
    ):
        value = overrides.get(key, source.get(key))
        if _is_toml_scalar(value):
            lines.append(f"{key} = {_toml_value(value)}")

    provider_name = source.get("model_provider")
    providers = source.get("model_providers", {})
    if isinstance(provider_name, str) and isinstance(providers, dict):
        provider = providers.get(provider_name)
        if isinstance(provider, dict):
            lines.append("")
            _append_table(lines, ("model_providers", provider_name), provider)

    lines.extend([
        "",
        "[features]",
        "plugins = false",
        "",
        f"[projects.{_toml_value(str(workspace))}]",
        'trust_level = "trusted"',
        "",
    ])
    return "\n".join(lines)


def _append_table(lines: list[str], path: tuple[str, ...], values: dict[str, Any]) -> None:
    scalar_items = [
        (key, value)
        for key, value in values.items()
        if _is_toml_scalar(value)
    ]
    lines.append("[" + ".".join(_toml_key(item) for item in path) + "]")
    lines.extend(
        f"{_toml_key(key)} = {_toml_value(value)}"
        for key, value in scalar_items
    )
    for key, value in values.items():
        if isinstance(value, dict):
            lines.append("")
            _append_table(lines, (*path, key), value)


def _is_toml_scalar(value: Any) -> bool:
    return isinstance(value, (str, bool, int, float))


def _toml_key(value: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9_-]+", value):
        return value
    return json.dumps(value, ensure_ascii=False)


def _toml_value(value: Any) -> str:
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    raise TypeError(f"unsupported TOML value: {type(value).__name__}")
