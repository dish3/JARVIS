#!/usr/bin/env python3
"""
Terminal Tool - Execute system commands
Subprocess execution with safety checks and live streaming.
"""

import subprocess
import logging
import os
import threading
from typing import Dict, Any

logger = logging.getLogger('TERMINAL_TOOL')

# Allowlist of safe commands — preserved exactly
ALLOWED_COMMANDS = {
    'python', 'node', 'npm', 'pip', 'git', 'ls', 'dir', 'cd', 'mkdir',
    'echo', 'cat', 'type', 'copy', 'move', 'del', 'rm', 'cp', 'mv',
    'pwd', 'whoami', 'date', 'time', 'ping', 'curl', 'wget',
}

# Blocklist of dangerous commands — preserved exactly
BLOCKED_COMMANDS = {
    'rm -rf', 'del /s', 'format', 'fdisk', 'dd', 'mkfs',
    'shutdown', 'reboot', 'halt', 'poweroff',
}

# Commands that can legitimately run for a long time
_LONG_RUNNING_PREFIXES = ('npm', 'pip', 'pip3', 'yarn', 'node', 'python', 'pytest')

# Default timeout for quick commands; extended for installs/builds
_DEFAULT_TIMEOUT = 10
_LONG_TIMEOUT    = 300   # 5 minutes for npm install, pip install, etc.


class TerminalTool:
    """Execute terminal commands safely with live stdout/stderr streaming."""

    def __init__(self):
        logger.info("Initializing Terminal Tool...")
        logger.info("[OK] Terminal Tool initialized")

    def execute(self, command: str, timeout: int = None) -> str:
        """
        Execute a terminal command and return its combined output.

        Signature is identical to the original — callers are unaffected.
        Internally uses streaming so stdout/stderr are logged live and the
        process is never silently blocked for 10s on long installs.

        Args:
            command: Command to execute
            timeout:  Override timeout in seconds. If None, auto-detected:
                      long-running commands get 300s, others get 10s.

        Returns:
            Combined stdout+stderr output, or an error message string.
        """
        logger.info(f"[TERMINAL] Executing: {command}")

        # Safety checks — preserved exactly
        if not self._is_safe(command):
            logger.warning(f"[TERMINAL] Blocked unsafe command: {command}")
            return "Error: Command not allowed for security reasons"

        # Auto-select timeout based on command type
        if timeout is None:
            timeout = self._select_timeout(command)

        return self._stream_execute(command, timeout)

    # ── Private: streaming execution ──────────────────────────────────────────

    def _stream_execute(self, command: str, timeout: int) -> str:
        """
        Run command via Popen, stream stdout and stderr live to the logger,
        collect all output, and return it as a single string.

        stdout and stderr are read concurrently on separate daemon threads so
        neither pipe blocks the other (avoids deadlock on large output).
        """
        stdout_lines = []
        stderr_lines = []

        def _read_stream(stream, collector: list, tag: str) -> None:
            """Read lines from a stream, log each one, append to collector."""
            try:
                for raw in stream:
                    line = raw.rstrip('\n').rstrip('\r\n')
                    if line:
                        logger.info(f"[TERMINAL] {tag}: {line}")
                        collector.append(line)
            except Exception as e:
                logger.debug(f"[TERMINAL] Stream read error ({tag}): {e}")
            finally:
                try:
                    stream.close()
                except Exception:
                    pass

        try:
            proc = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace',
                cwd=os.getcwd(),
            )

            # Read stdout and stderr concurrently — prevents pipe buffer deadlock
            t_out = threading.Thread(
                target=_read_stream,
                args=(proc.stdout, stdout_lines, 'OUT'),
                daemon=True,
            )
            t_err = threading.Thread(
                target=_read_stream,
                args=(proc.stderr, stderr_lines, 'ERR'),
                daemon=True,
            )
            t_out.start()
            t_err.start()

            # Wait for process to finish within timeout
            try:
                proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                proc.kill()
                # Drain remaining output after kill
                t_out.join(timeout=2)
                t_err.join(timeout=2)
                logger.error(f"[TERMINAL] Timeout after {timeout}s: {command}")
                partial = '\n'.join(stdout_lines + stderr_lines)
                suffix = f"\n[partial output above]\nError: Command timed out after {timeout}s"
                return (partial + suffix).strip()

            # Wait for reader threads to finish draining
            t_out.join(timeout=5)
            t_err.join(timeout=5)

            # Combine output — stdout first, then stderr
            all_lines = stdout_lines + stderr_lines
            output = '\n'.join(all_lines).strip()

            if proc.returncode == 0:
                logger.info(f"[TERMINAL] Success (exit 0): {command}")
                return output or "Command executed successfully"
            else:
                logger.warning(
                    f"[TERMINAL] Failed (exit {proc.returncode}): {command}"
                )
                return f"Error (exit {proc.returncode}): {output}" if output else \
                       f"Error: Command exited with code {proc.returncode}"

        except Exception as e:
            logger.error(f"[TERMINAL] Error: {e}")
            return f"Error: {str(e)}"

    # ── Private: helpers ───────────────────────────────────────────────────────

    def _select_timeout(self, command: str) -> int:
        """
        Return an appropriate timeout for the command.
        npm/pip/yarn/python scripts get 300s; everything else gets 10s.
        """
        first = command.strip().lower().split()[0] if command.strip() else ''
        if first in _LONG_RUNNING_PREFIXES:
            logger.info(
                f"[TERMINAL] Long-running command detected ({first}) "
                f"— timeout set to {_LONG_TIMEOUT}s"
            )
            return _LONG_TIMEOUT
        return _DEFAULT_TIMEOUT

    def _is_safe(self, command: str) -> bool:
        """Check if command is safe to execute — preserved exactly."""
        command_lower = command.lower().strip()

        # Check blocklist
        for blocked in BLOCKED_COMMANDS:
            if blocked in command_lower:
                return False

        # Check if starts with allowed command
        first_word = command_lower.split()[0] if command_lower.split() else ""

        # Allow if first word is in allowlist
        if first_word in ALLOWED_COMMANDS:
            return True

        # Allow if it's a path to executable
        if '/' in first_word or '\\' in first_word:
            return True

        logger.warning(f"[TERMINAL] Unknown command: {first_word}")
        return False


def main():
    """Test terminal tool"""
    tool = TerminalTool()

    commands = [
        "echo hello world",
        "python --version",
        "dir",
        "pwd",
    ]

    for cmd in commands:
        print(f"\nCommand: {cmd}")
        result = tool.execute(cmd)
        print(f"Result: {result}")


if __name__ == '__main__':
    main()
