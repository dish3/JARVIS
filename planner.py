#!/usr/bin/env python3
"""
JARVIS Planner - AI Planning with Groq + Ollama Fallback

Primary:  Groq API (llama-3.3-70b-versatile) — fast cloud inference
Fallback: Ollama (phi3.5) — local inference when offline

Only called when the Router can't handle the goal via pattern matching.
"""

import json
import logging
import os
import time
import requests
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger('PLANNER')

# ── Configuration ──────────────────────────────────────────────────────────────

# Groq settings
GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')
GROQ_MODEL = os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile')
GROQ_TIMEOUT = 15  # seconds — Groq is fast

# Ollama settings (fallback)
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_HEALTH_URL = "http://localhost:11434/api/tags"
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'phi3.5')
OLLAMA_TIMEOUT = 20  # seconds
OLLAMA_HEALTH_TIMEOUT = 3

# Backend selection: 'groq', 'ollama', or 'auto' (try groq first)
AI_BACKEND = os.getenv('AI_BACKEND', 'auto').lower()

# Shared settings
TEMPERATURE = 0.2
MAX_RETRIES = 2

# ── System prompt ──────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are JARVIS, a powerful AI desktop assistant. Analyze the user's goal and decide how to handle it.

You have access to these tools:
1. **terminal** — Execute shell commands (python, node, npm, pip, git, ls, dir, etc.)
2. **file** — Read, write, list, or append files. Actions: read, write, list, append
3. **browser** — Open URLs, search the web, launch desktop apps, generate images. Actions: open, search, generate_image
4. **search** — Search the web via DuckDuckGo for current information. Action: search
5. **linkedin** — Post to LinkedIn or delete last post. Actions: post, delete
6. **git** — Git operations: status, add, commit, push, pull, log
7. **code** — Read, patch, run, or create Python files; open in VS Code. Actions: read, patch, run, create, open_vscode
8. **automation** — Control mouse/keyboard/screen via pyautogui. Actions: click, double_click, right_click, type, press_key, hotkey, screenshot, move_mouse, get_mouse_position, get_screen_size, scroll, drag_drop, locate_image

Respond with a JSON object (and ONLY a JSON object, no markdown, no explanation):
{
  "tool": "<tool_name or null if no tool needed>",
  "action": "<action or null>",
  "parameters": {<action-specific parameters>},
  "response": "<your response to the user>"
}

Parameter reference:
- terminal: {"command": "..."}
- file read: {"path": "..."}
- file write: {"path": "...", "content": "..."}
- file list: {"path": "."}
- browser open: {"url": "...", "browser": "chrome|firefox|edge|null"}
- browser search: {"query": "..."}
- browser generate_image: {"prompt": "..."}
- search: {"query": "..."}
- linkedin post: {"text": "...", "image_path": "...|null"}
- linkedin delete: {}
- git: {"action": "status|add|commit|push|pull|log", "message": "...", "path": ".", "remote": "origin", "branch": "null", "count": 5}
- code read: {"path": "..."}
- code patch: {"path": "...", "find": "...", "replace": "..."}
- code run: {"path": "..."}
- code create: {"path": "...", "content": "..."}
- code open_vscode: {"path": "..."}
- automation click: {"x": 0, "y": 0, "button": "left"}
- automation type: {"text": "..."}
- automation press_key: {"key": "enter"}
- automation hotkey: {"keys": ["ctrl", "c"]}
- automation screenshot: {"filename": "screenshot.png"}
- automation scroll: {"clicks": 5}
- automation move_mouse: {"x": 0, "y": 0}
- automation drag_drop: {"x1": 0, "y1": 0, "x2": 0, "y2": 0}

Rules:
- If the goal is a question or conversation, set tool to null and put your answer in response.
- If the goal needs a tool, pick the most appropriate one.
- Always include a helpful response message.
- Be concise and direct.
- ONLY output valid JSON. No markdown code fences. No extra text.

Important context:
- The **linkedin** tool handles login/authentication AUTOMATICALLY using stored credentials. Never ask the user for LinkedIn credentials or try to type them — just use the linkedin tool directly.
- The **browser** tool opens URLs in the user's regular browser. It does NOT have automation/login capability. For LinkedIn actions (posting, deleting), always use the **linkedin** tool instead.
- The **automation** tool controls the physical mouse/keyboard. Only use it when the user explicitly asks for mouse/keyboard control (e.g., "click at 500 300", "type hello", "take screenshot"). Do NOT use it for app-specific tasks that have a dedicated tool.
- The user's project is at E:\\PROJECTS\\JARVIS\\VirtualAssistant. Use this as the base path for file/code operations when no path is specified."""


class Planner:
    """AI Planner with Groq primary and Ollama fallback.
    
    Analyzes user goals and decides:
    - Which tool to use (if any)
    - What parameters to pass
    - What response to give the user
    """

    def __init__(self):
        logger.info("Initializing Planner...")
        self._groq_client = None
        self._groq_available = False
        self._ollama_available = False

        # Initialize backends based on config
        if AI_BACKEND in ('groq', 'auto'):
            self._init_groq()
        if AI_BACKEND in ('ollama', 'auto'):
            self._check_ollama()

        backend_status = []
        if self._groq_available:
            backend_status.append(f"Groq ({GROQ_MODEL})")
        if self._ollama_available:
            backend_status.append(f"Ollama ({OLLAMA_MODEL})")

        if backend_status:
            logger.info(f"[OK] Planner initialized — backends: {', '.join(backend_status)}")
        else:
            logger.warning("[WARN] Planner initialized — NO backends available")

    # ── Backend initialization ─────────────────────────────────────────────────

    def _init_groq(self) -> None:
        """Initialize the Groq client."""
        if not GROQ_API_KEY or GROQ_API_KEY.startswith('gsk_optional'):
            logger.warning("[GROQ] No valid API key found")
            return

        try:
            from groq import Groq
            self._groq_client = Groq(api_key=GROQ_API_KEY)
            self._groq_available = True
            logger.info(f"[OK] Groq client initialized (model: {GROQ_MODEL})")
        except ImportError:
            logger.warning("[GROQ] groq package not installed — run: pip install groq")
        except Exception as e:
            logger.warning(f"[GROQ] Init failed: {e}")

    def _check_ollama(self) -> bool:
        """Check if Ollama is running at startup (non-blocking)."""
        try:
            response = requests.get(OLLAMA_HEALTH_URL, timeout=OLLAMA_HEALTH_TIMEOUT)
            if response.status_code == 200:
                self._ollama_available = True
                logger.info("[OK] Ollama is running")
                return True
        except Exception:
            pass
        logger.warning("[WARN] Ollama not running. Start with: ollama run phi3.5")
        return False

    def _is_ollama_available(self) -> bool:
        """Pre-inference health check for Ollama (fast 3s timeout)."""
        try:
            r = requests.get(OLLAMA_HEALTH_URL, timeout=OLLAMA_HEALTH_TIMEOUT)
            return r.status_code == 200
        except Exception:
            return False

    # ── Main planning method ───────────────────────────────────────────────────

    def plan(self, goal: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Use AI to plan how to achieve the goal.

        Tries Groq first (if available), falls back to Ollama.

        Args:
            goal: User's goal
            context: Memory context (recent interactions, user facts)

        Returns:
            {
                'requires_tool': bool,
                'tool_type': str or None,
                'action': str or None,
                'parameters': dict,
                'response': str,
                'reasoning': str,
            }
        """
        logger.info(f"[PLANNER] Planning: {goal}")

        # Build context string for the prompt
        context_str = ""
        if context:
            recent = context.get('recent_interactions', [])
            if recent:
                history = []
                for interaction in recent[-5:]:
                    g = interaction.get('goal', '')
                    r = str(interaction.get('result', ''))[:100]
                    history.append(f"User: {g} → Result: {r}")
                context_str = "\n\nRecent conversation:\n" + "\n".join(history)

            older_summary = context.get('older_summary', '')
            if older_summary:
                context_str += f"\n\nOlder history summary:\n{older_summary}"

            facts = context.get('user_facts', {})
            if facts:
                fact_strs = [f"{k}: {v.get('value', v) if isinstance(v, dict) else v}"
                             for k, v in facts.items()]
                context_str += "\n\nKnown user facts:\n" + "\n".join(fact_strs)

        user_message = f"Goal: {goal}{context_str}"

        # Try Groq first
        if AI_BACKEND in ('groq', 'auto') and self._groq_available:
            result = self._plan_with_groq(user_message, goal)
            if result:
                return result
            logger.warning("[PLANNER] Groq failed, trying Ollama fallback...")

        # Fallback to Ollama
        if AI_BACKEND in ('ollama', 'auto'):
            result = self._plan_with_ollama(user_message, goal)
            if result:
                return result

        # Both backends failed
        return self._unavailable_response(goal)

    # ── Groq backend ──────────────────────────────────────────────────────────

    def _plan_with_groq(self, user_message: str, goal: str) -> Optional[Dict[str, Any]]:
        """Plan using Groq API with chat completions."""
        if not self._groq_client:
            return None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.info(f"[GROQ] Calling {GROQ_MODEL} (attempt {attempt})...")

                chat_completion = self._groq_client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_message},
                    ],
                    model=GROQ_MODEL,
                    temperature=TEMPERATURE,
                    max_tokens=1024,
                    timeout=GROQ_TIMEOUT,
                )

                response_text = chat_completion.choices[0].message.content
                logger.info(f"[GROQ] Response received ({len(response_text)} chars)")

                return self._parse_json_response(response_text, goal)

            except Exception as e:
                logger.warning(f"[GROQ] Error on attempt {attempt}: {e}")
                if attempt < MAX_RETRIES:
                    time.sleep(1)

        # Mark groq as temporarily unavailable after repeated failures
        logger.warning("[GROQ] All attempts failed")
        return None

    # ── Ollama backend ─────────────────────────────────────────────────────────

    def _plan_with_ollama(self, user_message: str, goal: str) -> Optional[Dict[str, Any]]:
        """Plan using local Ollama as fallback."""
        if not self._is_ollama_available():
            logger.warning("[OLLAMA] Health check failed — not reachable")
            return None

        # Build a combined prompt (Ollama uses raw text, not chat format)
        prompt = f"{SYSTEM_PROMPT}\n\nUser: {user_message}"

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.info(f"[OLLAMA] Calling {OLLAMA_MODEL} (attempt {attempt})...")

                response = requests.post(
                    OLLAMA_URL,
                    json={
                        "model": OLLAMA_MODEL,
                        "prompt": prompt,
                        "stream": False,
                        "temperature": TEMPERATURE,
                    },
                    timeout=OLLAMA_TIMEOUT,
                )

                if response.status_code != 200:
                    logger.error(f"[OLLAMA] HTTP {response.status_code} on attempt {attempt}")
                    if attempt < MAX_RETRIES:
                        continue
                    return None

                result = response.json()
                response_text = result.get('response', '')
                logger.info(f"[OLLAMA] Response received ({len(response_text)} chars)")

                return self._parse_json_response(response_text, goal)

            except requests.exceptions.Timeout:
                logger.warning(f"[OLLAMA] Timeout after {OLLAMA_TIMEOUT}s (attempt {attempt})")
                if attempt < MAX_RETRIES:
                    time.sleep(1)

            except Exception as e:
                logger.error(f"[OLLAMA] Error on attempt {attempt}: {e}")
                if attempt < MAX_RETRIES:
                    time.sleep(1)

        return None

    # ── Response parsing ───────────────────────────────────────────────────────

    def _parse_json_response(self, response_text: str, goal: str) -> Dict[str, Any]:
        """Parse JSON response from either Groq or Ollama.

        Handles common LLM output quirks:
        - Markdown code fences around JSON
        - Extra text before/after JSON
        - Malformed JSON (falls back to text extraction)
        """
        logger.info("[PLANNER] Parsing response...")

        # Strip markdown code fences if present
        cleaned = response_text.strip()
        if cleaned.startswith('```'):
            # Remove opening fence (with optional language tag)
            first_newline = cleaned.index('\n') if '\n' in cleaned else len(cleaned)
            cleaned = cleaned[first_newline + 1:]
        if cleaned.endswith('```'):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        # Try to extract JSON object
        try:
            # Find the first { and last }
            start = cleaned.index('{')
            end = cleaned.rindex('}') + 1
            json_str = cleaned[start:end]
            data = json.loads(json_str)

            tool = data.get('tool')
            action = data.get('action')
            parameters = data.get('parameters', {})
            response = data.get('response', goal)

            # Normalize null/none/empty tool
            if tool in (None, 'null', 'none', 'None', ''):
                tool = None
            if action in (None, 'null', 'none', 'None', ''):
                action = None

            # Ensure action is in parameters for tools that need it
            if tool and action and 'action' not in parameters:
                parameters['action'] = action

            plan_result = {
                'requires_tool': tool is not None,
                'tool_type': tool,
                'action': action,
                'parameters': parameters,
                'response': response,
                'reasoning': response_text,
            }

            logger.info(f"[DEBUG] Plan dict: {str(plan_result)[:200]}")
            return plan_result

        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"[PLANNER] JSON parse failed ({e}), using text fallback")
            return self._parse_text_fallback(response_text, goal)

    def _parse_text_fallback(self, response_text: str, goal: str) -> Dict[str, Any]:
        """Fallback parser when JSON parsing fails.

        Tries to extract TOOL/ACTION/PARAMETERS/RESPONSE from text format
        (backwards compatibility with old Ollama responses).
        """
        lines = response_text.strip().split('\n')

        tool_type = None
        action = None
        parameters = {}
        response = ""
        response_lines = []
        in_response = False

        for line in lines:
            if line.startswith('TOOL:'):
                in_response = False
                tool_type = line.replace('TOOL:', '').strip().lower()
                if tool_type in ('none', 'null', ''):
                    tool_type = None
            elif line.startswith('ACTION:'):
                in_response = False
                action = line.replace('ACTION:', '').strip().lower()
                if action in ('none', 'null', ''):
                    action = None
            elif line.startswith('PARAMETERS:'):
                in_response = False
                try:
                    params_str = line.replace('PARAMETERS:', '').strip()
                    if params_str and params_str not in ('empty', 'NONE', '{}', ''):
                        if params_str.startswith('{'):
                            parameters = json.loads(params_str)
                except Exception:
                    parameters = {}
            elif line.startswith('RESPONSE:'):
                in_response = True
                first = line.replace('RESPONSE:', '').strip()
                if first:
                    response_lines.append(first)
            elif in_response and line.strip():
                response_lines.append(line.strip())

        response = ' '.join(response_lines).strip()
        if not response:
            response = goal

        # Clean up
        if len(response) > 300:
            response = response.split('.')[0] + '.'

        if tool_type and action and 'action' not in parameters:
            parameters['action'] = action

        return {
            'requires_tool': tool_type is not None,
            'tool_type': tool_type,
            'action': action,
            'parameters': parameters,
            'response': response,
            'reasoning': response_text,
        }

    # ── Fallback responses ─────────────────────────────────────────────────────

    def _default_response(self, goal: str) -> Dict[str, Any]:
        """Default response when AI times out or returns an error."""
        logger.warning("[PLANNER] Using default response")
        return {
            'requires_tool': False,
            'tool_type': None,
            'action': None,
            'parameters': {},
            'response': f"I understood your goal: {goal}. The AI backend timed out — please try again.",
            'reasoning': "AI backend timeout",
        }

    def _unavailable_response(self, goal: str) -> Dict[str, Any]:
        """Response when no AI backend is available."""
        logger.warning("[PLANNER] No AI backend available")

        hints = []
        if not self._groq_available:
            hints.append("Set GROQ_API_KEY in .env and install groq: pip install groq")
        if not self._ollama_available:
            hints.append("Start Ollama: ollama run phi3.5")

        return {
            'requires_tool': False,
            'tool_type': None,
            'action': None,
            'parameters': {},
            'response': (
                "No AI backend is available. "
                + " | ".join(hints)
            ),
            'reasoning': "No backend available",
        }


def main():
    """Test planner with both backends."""
    planner = Planner()

    test_goals = [
        "What is Python?",
        "Tell me a joke",
        "open chrome",
        "take a screenshot",
        "read code from planner.py",
    ]

    for goal in test_goals:
        print(f"\nGoal: {goal}")
        result = planner.plan(goal)
        print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
