"""
Subprocess stdio JSON-RPC transport with stream framing, pollution detection, and timeouts.
"""

import json
import os
import queue
import shlex
import subprocess
import threading
import time
from typing import Any, Dict, List, Optional, Tuple


class StdioTransport:
    """Manages an active MCP Server process over stdio pipes."""

    def __init__(self, command: str, cwd: Optional[str] = None, env: Optional[Dict[str, str]] = None):
        self.command = command
        self.cwd = cwd
        self.env = {**os.environ, **(env or {})}

        self.proc: Optional[subprocess.Popen] = None
        self._stdout_queue: queue.Queue = queue.Queue()
        self._stderr_lines: List[str] = []
        self._raw_stdout_pollutions: List[str] = []
        self._threads: List[threading.Thread] = []
        self._is_running = False

    def start(self) -> None:
        """Spawn the server process."""
        args = shlex.split(self.command) if isinstance(self.command, str) else self.command
        self.proc = subprocess.Popen(
            args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.cwd,
            env=self.env,
            text=True,
            bufsize=1
        )
        self._is_running = True

        # Reader thread for stdout
        t_out = threading.Thread(target=self._read_stdout, daemon=True)
        t_out.start()
        self._threads.append(t_out)

        # Reader thread for stderr
        t_err = threading.Thread(target=self._read_stderr, daemon=True)
        t_err.start()
        self._threads.append(t_err)

    def _read_stdout(self) -> None:
        """Reads lines from stdout and categorizes into JSON-RPC vs raw pollution."""
        while self._is_running and self.proc and self.proc.stdout:
            line = self.proc.stdout.readline()
            if not line:
                break
            stripped = line.strip()
            if not stripped:
                continue

            try:
                msg = json.loads(stripped)
                self._stdout_queue.put(("json", msg, stripped))
            except json.JSONDecodeError:
                # Stdout polluted with non-JSON logs (common violation breaking MCP clients)
                self._raw_stdout_pollutions.append(stripped)
                self._stdout_queue.put(("raw", None, stripped))

    def _read_stderr(self) -> None:
        """Collects stderr output for diagnostics."""
        while self._is_running and self.proc and self.proc.stderr:
            line = self.proc.stderr.readline()
            if not line:
                break
            self._stderr_lines.append(line.rstrip())

    def send_request(self, method: str, params: Optional[Dict[str, Any]] = None, req_id: int = 1) -> None:
        """Send a JSON-RPC 2.0 Request."""
        if not self.proc or not self.proc.stdin:
            raise RuntimeError("Server process is not running")

        msg = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method
        }
        if params is not None:
            msg["params"] = params

        line = json.dumps(msg, ensure_ascii=False) + "\n"
        self.proc.stdin.write(line)
        self.proc.stdin.flush()

    def send_notification(self, method: str, params: Optional[Dict[str, Any]] = None) -> None:
        """Send a JSON-RPC 2.0 Notification (no id)."""
        if not self.proc or not self.proc.stdin:
            raise RuntimeError("Server process is not running")

        msg = {
            "jsonrpc": "2.0",
            "method": method
        }
        if params is not None:
            msg["params"] = params

        line = json.dumps(msg, ensure_ascii=False) + "\n"
        self.proc.stdin.write(line)
        self.proc.stdin.flush()

    def receive_response(self, timeout: float = 5.0) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Wait for next JSON-RPC response from server.
        Returns: (parsed_json_or_None, raw_string_line)
        """
        start = time.time()
        while time.time() - start < timeout:
            try:
                msg_type, data, raw = self._stdout_queue.get(timeout=0.1)
                if msg_type == "json":
                    return data, raw
            except queue.Empty:
                if self.proc and self.proc.poll() is not None:
                    # Process died
                    break
        return None, None

    @property
    def stdout_pollutions(self) -> List[str]:
        """Lines printed to stdout that were not valid JSON-RPC."""
        return list(self._raw_stdout_pollutions)

    @property
    def stderr_logs(self) -> List[str]:
        """Stderr logs captured during execution."""
        return list(self._stderr_lines)

    def close(self) -> None:
        """Gracefully terminate server process and close open pipes."""
        self._is_running = False
        if self.proc:
            try:
                if self.proc.stdin:
                    self.proc.stdin.close()
                self.proc.terminate()
                self.proc.wait(timeout=1.0)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass
            finally:
                if self.proc.stdout:
                    self.proc.stdout.close()
                if self.proc.stderr:
                    self.proc.stderr.close()
