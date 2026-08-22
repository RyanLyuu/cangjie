from __future__ import annotations

import json
import os
import select
import shutil
import subprocess
import tempfile
import signal
import time
from collections import deque
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
    bypass_approvals_and_sandbox: bool = False
    environment: dict[str, str] | None = None

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

            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=workspace,
                env=(os.environ | self.environment) if self.environment else None,
                start_new_session=True,
            )
            try:
                stdout, stderr = process.communicate(input=prompt, timeout=self.timeout)
            except subprocess.TimeoutExpired as exc:
                # Codex launches a native child process. Kill the whole process
                # group so a descendant holding stdout cannot outlive the
                # controller's timeout and block the next file transaction.
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    pass
                process.wait()
                return AgentResult(
                    status="timeout",
                    content=None,
                    session_id=session_id,
                    stderr=f"Codex timed out after {self.timeout}s: {exc}",
                    returncode=124,
                )

            completed = subprocess.CompletedProcess(
                command, process.returncode, stdout, stderr
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
            if self.bypass_approvals_and_sandbox:
                args.append("--dangerously-bypass-approvals-and-sandbox")
        args.append("--ignore-rules")
        args.extend(["--disable", "plugins"])
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


@dataclass
class PersistentCodexRunner(AgentRunner):
    """Keep one Codex app-server process alive across multiple file turns.

    ``codex exec`` is intentionally one-shot: ``exec resume`` restores a
    thread but still starts a new CLI process.  The app-server protocol keeps
    the thread and transport alive, while the caller still decides when a
    file turn starts and ends.
    """

    executable: str = "codex"
    model: str = ""
    sandbox: str = "workspace-write"
    timeout: int = 1800
    extra_args: list[str] = field(default_factory=list)
    bypass_approvals_and_sandbox: bool = False
    approval_policy: str = ""
    environment: dict[str, str] | None = None
    client_name: str = "x2cangjie"
    client_version: str = "0.1"
    _process: subprocess.Popen[str] | None = field(default=None, init=False, repr=False)
    _thread_id: str = field(default="", init=False, repr=False)
    _request_id: int = field(default=0, init=False, repr=False)
    _pending: deque[dict[str, Any]] = field(default_factory=deque, init=False, repr=False)
    _turn_deltas: dict[str, list[str]] = field(default_factory=dict, init=False, repr=False)
    _stdout_buffer: bytearray = field(default_factory=bytearray, init=False, repr=False)

    def run(
        self,
        prompt: str,
        output_schema: dict[str, Any],
        *,
        workspace: str | Path,
        session_id: str = "",
    ) -> AgentResult:
        started = time.monotonic()
        turn_id = ""
        try:
            deadline = started + self.timeout
            self._ensure_started(Path(workspace).resolve(), session_id, deadline)
            request_id = self._send_request(
                "turn/start",
                {
                    "threadId": self._thread_id,
                    "input": [{"type": "text", "text": prompt}],
                    "cwd": str(Path(workspace).resolve()),
                    "outputSchema": output_schema,
                },
            )
            response = self._await_response(request_id, deadline)
            turn_id = str(response.get("result", {}).get("turn", {}).get("id", ""))
            if not turn_id:
                raise RuntimeError("app-server turn/start returned no turn id")
            text = self._await_turn(turn_id, deadline)
            content = self._parse_content(text)
            if content is None:
                return AgentResult(
                    status="error",
                    content=None,
                    session_id=self._thread_id,
                    stderr="app-server final response was not a JSON object",
                    returncode=1,
                )
            return AgentResult(
                status="success",
                content=content,
                session_id=self._thread_id,
            )
        except _AppServerTimeout as exc:
            if turn_id:
                self._interrupt_turn(turn_id)
            else:
                self.close()
            return AgentResult(
                status="timeout",
                content=None,
                session_id=self._thread_id,
                stderr=str(exc),
                returncode=124,
            )
        except Exception as exc:  # transport failures must become file failures
            self.close()
            return AgentResult(
                status="error",
                content=None,
                session_id=session_id or self._thread_id,
                stderr=f"Codex app-server error: {exc}",
                returncode=1,
            )

    def close(self) -> None:
        """Stop the long-lived app-server process and its descendants."""
        process = self._process
        self._process = None
        self._thread_id = ""
        self._pending.clear()
        self._turn_deltas.clear()
        self._stdout_buffer.clear()
        if process is None:
            return
        try:
            if process.stdin:
                process.stdin.close()
        except OSError:
            pass
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            pass
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
            process.wait()
        for stream in (process.stdout, process.stderr):
            if stream is not None:
                try:
                    stream.close()
                except OSError:
                    pass

    def __enter__(self) -> "PersistentCodexRunner":
        return self

    def __exit__(self, _exc_type, _exc, _traceback) -> None:
        self.close()

    def _ensure_started(self, workspace: Path, session_id: str, deadline: float) -> None:
        if self._process is not None and self._process.poll() is None:
            if self._thread_id and session_id and session_id != self._thread_id:
                raise RuntimeError(
                    f"persistent runner session mismatch: {session_id} != {self._thread_id}"
                )
            return

        executable = shutil.which(self.executable) or (
            self.executable if Path(self.executable).is_file() else ""
        )
        if not executable:
            raise FileNotFoundError(f"Codex executable not found: {self.executable}")

        command = [executable, "app-server", "--disable", "plugins", "--listen", "stdio://"]
        command.extend(self.extra_args)
        self._process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=False,
            cwd=workspace,
            env=(os.environ | self.environment) if self.environment else None,
            start_new_session=True,
        )
        self._request_id = 0
        self._pending.clear()
        self._stdout_buffer.clear()
        self._send_request(
            "initialize",
            {
                "clientInfo": {
                    "name": self.client_name,
                    "version": self.client_version,
                },
                "capabilities": {"experimentalApi": True},
            },
        )
        self._await_response(self._request_id, deadline)
        self._send_notification("initialized", {})

        approval_policy = self._approval_policy()
        if session_id:
            response = self._request_and_wait(
                "thread/resume",
                {"threadId": session_id},
                workspace,
                deadline,
            )
        else:
            params: dict[str, Any] = {
                "cwd": str(workspace),
                "sandbox": self.sandbox,
                "approvalPolicy": approval_policy,
            }
            if self.model:
                params["model"] = self.model
            response = self._request_and_wait(
                "thread/start", params, workspace, deadline
            )
        self._thread_id = str(response.get("result", {}).get("thread", {}).get("id", ""))
        if not self._thread_id:
            raise RuntimeError("app-server thread response returned no thread id")

    def _approval_policy(self) -> str:
        if self.approval_policy:
            if self.approval_policy not in {"on-request", "never"}:
                raise ValueError("approval_policy must be 'on-request' or 'never'")
            return self.approval_policy
        return "never" if self.bypass_approvals_and_sandbox else "on-request"

    def _request_and_wait(
        self,
        method: str,
        params: dict[str, Any],
        _workspace: Path,
        deadline: float,
    ) -> dict[str, Any]:
        request_id = self._send_request(method, params)
        return self._await_response(request_id, deadline)

    def _send_request(self, method: str, params: dict[str, Any]) -> int:
        self._request_id += 1
        message = {"jsonrpc": "2.0", "id": self._request_id, "method": method, "params": params}
        self._write_message(message)
        return self._request_id

    def _send_notification(self, method: str, params: dict[str, Any]) -> None:
        self._write_message({"jsonrpc": "2.0", "method": method, "params": params})

    def _write_message(self, message: dict[str, Any]) -> None:
        if self._process is None or self._process.stdin is None:
            raise RuntimeError("app-server process is not running")
        self._process.stdin.write(
            (json.dumps(message, ensure_ascii=False) + "\n").encode("utf-8")
        )
        self._process.stdin.flush()

    def _await_response(self, request_id: int, deadline: float) -> dict[str, Any]:
        while True:
            message = self._next_message(deadline)
            if message.get("id") != request_id:
                self._pending.append(message)
                self._respond_to_server_request(message)
                continue
            if "error" in message:
                error = message.get("error", {})
                raise RuntimeError(str(error.get("message", error)))
            return message

    def _await_turn(self, turn_id: str, deadline: float) -> str:
        final_text = ""
        self._turn_deltas.clear()
        while True:
            # A busy app-server can queue many events at once. Check the
            # absolute deadline before draining that queue so a turn cannot
            # bypass the file watchdog while processing buffered messages.
            if time.monotonic() >= deadline:
                raise _AppServerTimeout(f"Codex app-server timed out after {self.timeout}s")
            message = self._pending.popleft() if self._pending else self._next_message(deadline)
            self._respond_to_server_request(message)
            method = message.get("method")
            params = message.get("params", {})
            if method != "turn/completed" and params.get("turnId") != turn_id:
                continue
            if method == "item/agentMessage/delta":
                item_id = str(params.get("itemId", ""))
                self._turn_deltas.setdefault(item_id, []).append(str(params.get("delta", "")))
            elif method == "item/completed":
                item = params.get("item", {})
                if item.get("type") == "agentMessage":
                    final_text = str(item.get("text", ""))
            elif method == "turn/completed":
                turn = params.get("turn", {})
                if str(turn.get("id", "")) != turn_id:
                    continue
                if str(turn.get("status", "")) != "completed":
                    raise RuntimeError(
                        f"app-server turn ended with status {turn.get('status', 'unknown')}"
                    )
                if final_text:
                    return final_text
                return "".join(
                    text for values in self._turn_deltas.values() for text in values
                )

    def _interrupt_turn(self, turn_id: str) -> None:
        try:
            request_id = self._send_request(
                "turn/interrupt",
                {"threadId": self._thread_id, "turnId": turn_id},
            )
            self._await_response(request_id, time.monotonic() + 2)
        except Exception:
            self.close()

    def _next_message(self, deadline: float) -> dict[str, Any]:
        if self._process is None or self._process.stdout is None:
            raise RuntimeError("app-server process is not running")
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise _AppServerTimeout(f"Codex app-server timed out after {self.timeout}s")
            if b"\n" in self._stdout_buffer:
                line, _, remainder = self._stdout_buffer.partition(b"\n")
                self._stdout_buffer = bytearray(remainder)
                try:
                    message = json.loads(line.decode("utf-8"))
                except json.JSONDecodeError:
                    continue
                if isinstance(message, dict):
                    return message
            ready, _, _ = select.select([self._process.stdout], [], [], min(remaining, 0.5))
            if not ready:
                if self._process.poll() is not None:
                    raise RuntimeError("Codex app-server exited unexpectedly")
                continue
            chunk = os.read(self._process.stdout.fileno(), 65536)
            if not chunk:
                raise RuntimeError("Codex app-server closed its stdout")
            self._stdout_buffer.extend(chunk)

    def _respond_to_server_request(self, message: dict[str, Any]) -> None:
        if "method" not in message or "id" not in message or "result" in message:
            return
        # ``approvalPolicy=never`` should avoid these requests. Decline any
        # unexpected approval instead of allowing the app-server turn to hang.
        self._write_message({
            "jsonrpc": "2.0",
            "id": message["id"],
            "result": {"decision": "decline"},
        })

    @staticmethod
    def _parse_content(text: str) -> dict[str, Any] | None:
        try:
            value = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return None
        return value if isinstance(value, dict) else None


class _AppServerTimeout(TimeoutError):
    pass
