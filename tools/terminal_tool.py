#!/usr/bin/env python3
"""
Terminal Tool - Execute system commands
Subprocess execution with safety checks
"""

import subprocess
import logging
import os
from typing import Dict, Any

logger = logging.getLogger('TERMINAL_TOOL')

# Allowlist of safe commands
ALLOWED_COMMANDS = {
    'python', 'node', 'npm', 'pip', 'git', 'ls', 'dir', 'cd', 'mkdir',
    'echo', 'cat', 'type', 'copy', 'move', 'del', 'rm', 'cp', 'mv',
    'pwd', 'whoami', 'date', 'time', 'ping', 'curl', 'wget',
}

# Blocklist of dangerous commands
BLOCKED_COMMANDS = {
    'rm -rf', 'del /s', 'format', 'fdisk', 'dd', 'mkfs',
    'shutdown', 'reboot', 'halt', 'poweroff',
}


class TerminalTool:
    """Execute terminal commands safely"""
    
    def __init__(self):
        logger.info("Initializing Terminal Tool...")
        logger.info("[OK] Terminal Tool initialized")
    
    def execute(self, command: str, timeout: int = 10) -> str:
        """
        Execute a terminal command
        
        Args:
            command: Command to execute
            timeout: Timeout in seconds
            
        Returns:
            Command output or error message
        """
        logger.info(f"[TERMINAL] Executing: {command}")
        
        # Safety checks
        if not self._is_safe(command):
            logger.warning(f"[TERMINAL] Blocked unsafe command: {command}")
            return "Error: Command not allowed for security reasons"
        
        try:
            # Execute command
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=os.getcwd()
            )
            
            output = result.stdout or result.stderr
            
            if result.returncode == 0:
                logger.info(f"[TERMINAL] Success: {command}")
                return output or "Command executed successfully"
            else:
                logger.warning(f"[TERMINAL] Failed: {command}")
                return f"Error: {output}"
        
        except subprocess.TimeoutExpired:
            logger.error(f"[TERMINAL] Timeout: {command}")
            return f"Error: Command timed out after {timeout}s"
        except Exception as e:
            logger.error(f"[TERMINAL] Error: {str(e)}")
            return f"Error: {str(e)}"
    
    def _is_safe(self, command: str) -> bool:
        """Check if command is safe to execute"""
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
    
    # Test commands
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
