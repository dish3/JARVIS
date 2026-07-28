#!/usr/bin/env python3
"""
Git Tool - Run common git workflows safely
"""

import subprocess
import logging
import os
from typing import Optional

logger = logging.getLogger('GIT_TOOL')


class GitTool:
    """Simple Git tool for commit, push, pull, status operations"""

    def __init__(self):
        logger.info("Initializing Git Tool...")
        logger.info("[OK] Git Tool initialized")

    def _run_git(self, args, cwd: Optional[str] = None) -> str:
        command = ['git'] + args
        logger.info(f"[GIT] Executing: {' '.join(command)}")
        try:
            result = subprocess.run(
                command,
                cwd=cwd or os.getcwd(),
                capture_output=True,
                text=True,
                shell=False,
                timeout=20,
            )
            output = result.stdout.strip() or result.stderr.strip()
            if result.returncode == 0:
                return output or "Git command executed successfully"
            return f"Error: {output}"
        except subprocess.TimeoutExpired:
            logger.error("[GIT] Command timed out")
            return "Error: Git command timed out"
        except Exception as e:
            logger.error(f"[GIT] Error: {str(e)}")
            return f"Error: {str(e)}"

    def status(self, cwd: Optional[str] = None) -> str:
        return self._run_git(['status', '--short', '--branch'], cwd=cwd)

    def add(self, path: str = '.') -> str:
        return self._run_git(['add', path])

    def commit(self, message: str, allow_empty: bool = False) -> str:
        args = ['commit', '-m', message]
        if allow_empty:
            args.append('--allow-empty')
        return self._run_git(args)

    def push(self, remote: str = 'origin', branch: Optional[str] = None) -> str:
        if branch:
            return self._run_git(['push', remote, branch])
        return self._run_git(['push', remote])

    def pull(self, remote: str = 'origin', branch: Optional[str] = None) -> str:
        if branch:
            return self._run_git(['pull', remote, branch])
        return self._run_git(['pull', remote])

    def log(self, count: int = 5) -> str:
        return self._run_git(['log', f'--oneline', f'-n', str(count)])


if __name__ == '__main__':
    tool = GitTool()
    print(tool.status())
