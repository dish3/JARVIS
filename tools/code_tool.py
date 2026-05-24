#!/usr/bin/env python3
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger('CODE_TOOL')

class CodeTool:
    """Read, patch, run, and open Python files"""
    
    def execute(self, parameters: Dict) -> Any:
        action = parameters.get('action', '')
        
        if action == 'read':
            return self._read(parameters.get('path', ''))
        elif action == 'patch':
            return self._patch(parameters.get('path', ''),
                              parameters.get('find', ''),
                              parameters.get('replace', ''))
        elif action == 'run':
            return self._run(parameters.get('path', ''))
        elif action == 'open_vscode':
            return self._open_vscode(parameters.get('path', ''))
        elif action == 'create':
            return self._create(parameters.get('path', ''),
                               parameters.get('content', ''))
        
        return f"Unknown action: {action}"
    
    def _read(self, path: str) -> str:
        try:
            return Path(path).read_text(encoding='utf-8')
        except FileNotFoundError:
            return f"Error: File not found: {path}"
        except Exception as e:
            return f"Error reading: {str(e)}"
    
    def _patch(self, path: str, find: str, replace: str) -> str:
        try:
            p = Path(path)
            content = p.read_text(encoding='utf-8')
            if find not in content:
                return f"Error: Pattern not found in {path}"
            p.write_text(content.replace(find, replace, 1), encoding='utf-8')
            return f"Patched: {path}"
        except Exception as e:
            return f"Error patching: {str(e)}"
    
    def _run(self, path: str) -> str:
        try:
            r = subprocess.run(["python", path],
                             capture_output=True, text=True, timeout=30)
            return r.stdout if r.returncode == 0 else r.stderr
        except subprocess.TimeoutExpired:
            return "Error: Timed out after 30s"
        except Exception as e:
            return f"Error running: {str(e)}"
    
    def _open_vscode(self, path: str) -> str:
        try:
            subprocess.Popen(["code", path])
            return f"Opened in VS Code: {path}"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def _create(self, path: str, content: str) -> str:
        try:
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding='utf-8')
            return f"Created: {path}"
        except Exception as e:
            return f"Error creating: {str(e)}"
