from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AgentResult:
    status: str
    content: dict[str, Any] | None
    session_id: str = ""
    raw_events: tuple[dict[str, Any], ...] = ()
    stderr: str = ""
    returncode: int = 0


class AgentRunner(ABC):
    """Backend-neutral one-turn coding-agent interface."""

    @abstractmethod
    def run(
        self,
        prompt: str,
        output_schema: dict[str, Any],
        *,
        workspace: str | Path,
        session_id: str = "",
    ) -> AgentResult:
        raise NotImplementedError


@dataclass
class CodexRunner(AgentRunner):
    executable: str = "codex"
    model: str = ""
    sandbox: str = "read-only"
    timeout: int = 1800
    extra_args: list[str] = field(default_factory=list)

    def run(
        self,
        prompt: str,
        output_schema: dict[str, Any],
        *,
        workspace: str | Path,
        session_id: str = "",
    ) -> AgentResult:
        executable = shutil.which(self.executable) or (
            self.executable if Path(self.executable).is_file() else ""
        )
        if not executable:
            return AgentResult(
                status="error",
                content=None,
                stderr=f"Codex executable not found: {self.executable}",
                returncode=127,
            )

        workspace = Path(workspace).resolve()
        with tempfile.TemporaryDirectory(prefix="x2cangjie-codex-") as temp_dir:
            temp = Path(temp_dir)
            schema_path = temp / "output.schema.json"
            output_path = temp / "last-message.json"
            schema_path.write_text(json.dumps(output_schema, indent=2), encoding="utf-8")

            if session_id:
                command = [executable, "exec", "resume"]
                command.extend(self._common_args(schema_path, output_path, resume=True))
                command.extend([session_id, "-"])
            else:
                command = [executable, "exec"]
                command.extend(self._common_args(schema_path, output_path, resume=False))
                command.append("-")

            try:
                completed = subprocess.run(
                    command,
                    input=prompt,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    cwd=workspace,
                    check=False,
                )
            except subprocess.TimeoutExpired as exc:
                return AgentResult(
                    status="timeout",
                    content=None,
                    session_id=session_id,
                    stderr=f"Codex timed out after {self.timeout}s: {exc}",
                    returncode=124,
                )

            events = tuple(self._parse_events(completed.stdout))
            discovered_session = self._session_id(events) or session_id
            content = self._read_content(output_path)
            status = "success" if completed.returncode == 0 and content is not None else "error"
            stderr = completed.stderr.strip()
            if content is None and output_path.exists():
                stderr = (stderr + "\nCodex final response was not valid JSON.").strip()
            return AgentResult(
                status=status,
                content=content,
                session_id=discovered_session,
                raw_events=events,
                stderr=stderr,
                returncode=completed.returncode,
            )

    def _common_args(self, schema_path: Path, output_path: Path, *, resume: bool) -> list[str]:
        args = [
            "--json",
            "--output-schema", str(schema_path),
            "--output-last-message", str(output_path),
        ]
        if self.model:
            args.extend(["--model", self.model])
        if not resume:
            args.extend(["--sandbox", self.sandbox, "--color", "never"])
        args.extend(self.extra_args)
        return args

    @staticmethod
    def _parse_events(stdout: str) -> list[dict[str, Any]]:
        events = []
        for line in stdout.splitlines():
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                events.append(value)
        return events

    @staticmethod
    def _session_id(events: tuple[dict[str, Any], ...]) -> str:
        preferred = ("thread_id", "session_id", "conversation_id")
        for event in events:
            for key in preferred:
                value = event.get(key)
                if isinstance(value, str) and value:
                    return value
        return ""

    @staticmethod
    def _read_content(path: Path) -> dict[str, Any] | None:
        if not path.is_file():
            return None
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
        return value if isinstance(value, dict) else None
