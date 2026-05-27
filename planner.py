#!/usr/bin/env python3
"""
JARVIS Planner - Local AI Planning
Uses Ollama phi3.5 for reasoning
Only called when router can't handle the goal
"""

import requests
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger('PLANNER')

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_HEALTH_URL = "http://localhost:11434/api/tags"
MODEL = "phi3.5"
INFERENCE_TIMEOUT = 20   # seconds per attempt
HEALTH_TIMEOUT = 3       # seconds for health check


class Planner:
    """Uses Ollama for planning and reasoning"""
    
    def __init__(self):
        logger.info("Initializing Planner...")
        self.model = MODEL
        self.url = OLLAMA_URL
        self._check_ollama()
        logger.info("[OK] Planner initialized")
    
    def _check_ollama(self) -> bool:
        """Check if Ollama is running at startup (non-blocking, 3s timeout)."""
        try:
            response = requests.get(OLLAMA_HEALTH_URL, timeout=HEALTH_TIMEOUT)
            if response.status_code == 200:
                logger.info("[OK] Ollama is running")
                return True
        except Exception:
            pass
        logger.warning("[WARN] Ollama not running. Start with: ollama run phi3.5")
        return False

    def _is_ollama_available(self) -> bool:
        """
        Pre-inference health check — called before every plan() attempt.
        Fast 3s timeout so the UI is never blocked waiting for a dead server.
        Returns True if Ollama responds, False otherwise.
        """
        try:
            r = requests.get(OLLAMA_HEALTH_URL, timeout=HEALTH_TIMEOUT)
            return r.status_code == 200
        except Exception:
            return False
    
    def plan(self, goal: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Use Ollama to plan how to achieve the goal
        
        Args:
            goal: User's goal
            context: Memory context
            
        Returns:
            {
                'requires_tool': bool,
                'tool_type': str (terminal/file/browser),
                'parameters': dict,
                'response': str,
                'reasoning': str,
            }
        """
        logger.info(f"[PLANNER] Planning: {goal}")

        # Pre-inference health check — fast fail instead of 120s hang
        if not self._is_ollama_available():
            logger.warning("[OLLAMA] Health check failed — Ollama is not reachable")
            return self._unavailable_response(goal)

        # Build prompt
        prompt = self._build_prompt(goal, context)

        # Try inference up to 2 times (original attempt + one retry)
        for attempt in range(1, 3):
            try:
                logger.info(f"[OLLAMA] Calling {self.model} (attempt {attempt})...")
                response = requests.post(
                    self.url,
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "temperature": 0.3,
                    },
                    timeout=INFERENCE_TIMEOUT
                )

                if response.status_code != 200:
                    logger.error(f"[OLLAMA] HTTP {response.status_code} on attempt {attempt}")
                    if attempt == 2:
                        return self._default_response(goal)
                    continue

                result = response.json()
                response_text = result.get('response', '')
                logger.info(f"[OLLAMA] Response received ({len(response_text)} chars)")
                return self._parse_response(response_text, goal)

            except requests.exceptions.Timeout:
                logger.warning(f"[OLLAMA] Timeout after {INFERENCE_TIMEOUT}s (attempt {attempt})")
                if attempt == 2:
                    return self._default_response(goal)
                # Brief pause before retry
                import time
                time.sleep(1)

            except Exception as e:
                logger.error(f"[OLLAMA] Error on attempt {attempt}: {e}")
                if attempt == 2:
                    return self._default_response(goal)

        return self._default_response(goal)
    
    def _build_prompt(self, goal: str, context: Optional[Dict] = None) -> str:
        """Build prompt for Ollama"""
        context_str = ""
        if context:
            context_str = f"\nContext: {json.dumps(context)}"
        
        prompt = f"""You are JARVIS, an AI assistant. Analyze this goal and decide:
1. Can you handle it with a tool? (terminal/file/browser)
2. Or just provide a response?

Goal: {goal}{context_str}

Respond in this format:
TOOL: [terminal/file/browser or NONE]
ACTION: [execute/read/write/list/open/search or NONE]
PARAMETERS: [JSON parameters or empty]
RESPONSE: [Your response to the user]

Be concise and direct."""
        
        return prompt
    
    def _parse_response(self, response_text: str, goal: str) -> Dict[str, Any]:
        """Parse Ollama response"""
        logger.info("[PLANNER] Parsing response...")
        
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
                if tool_type == 'none':
                    tool_type = None
            elif line.startswith('ACTION:'):
                in_response = False
                action = line.replace('ACTION:', '').strip().lower()
                if action == 'none':
                    action = None
            elif line.startswith('PARAMETERS:'):
                in_response = False
                try:
                    params_str = line.replace('PARAMETERS:', '').strip()
                    if params_str and params_str not in ('empty', 'NONE', '{}', ''):
                        if not params_str.startswith('{'):
                            params_str = '{}'
                        parameters = json.loads(params_str)
                except:
                    parameters = {}
            elif line.startswith('RESPONSE:'):
                in_response = True
                first = line.replace('RESPONSE:', '').strip()
                if first:
                    response_lines.append(first)
            elif in_response and line.strip():
                import re as _re
                cleaned = _re.sub(r'^response\s*:\s*', '', line.strip(), flags=_re.IGNORECASE)
                # Stop collecting if Ollama switches to JSON output
                if cleaned.startswith('"') or cleaned.startswith('{'):
                    break
                if cleaned:
                    response_lines.append(cleaned)
        
        # Join all response lines, strip code fences and stray JSON chars
        def clean(text: str) -> str:
            bad = ('`', '{', '}', '```')
            return text.strip() if not any(text.strip().startswith(b) for b in bad) else ''
        
        response = ' '.join(l for l in response_lines if clean(l)).strip()
        # Strip any echoed RESPONSE: prefix Ollama sometimes adds (case-insensitive)
        import re as _re
        response = _re.sub(r'^response\s*:\s*', '', response, flags=_re.IGNORECASE).strip()
        
        # Final fallback: scan full text for first clean meaningful line
        if not response:
            for l in response_text.strip().split('\n'):
                c = clean(l)
                if c and not any(c.startswith(k) for k in ('TOOL:', 'ACTION:', 'PARAMETERS:', 'RESPONSE:')):
                    response = c
                    break
        
        if not response:
            response = goal
        
        # Clean up response - remove JSON fragments and extra text
        if response:
            # Remove common artifacts
            response = response.replace('RESPONse:', '').replace('RESPONSE:', '').strip()
            # Take only first sentence if too long
            if len(response) > 200:
                response = response.split('.')[0] + '.'
        
        plan_result = {
            'requires_tool': tool_type is not None,
            'tool_type': tool_type,
            'action': action,
            'parameters': parameters,
            'response': response,
            'reasoning': response_text,
        }
        
        logger.info(f"[DEBUG] Plan dict: {str(plan_result)[:200]}")
        return plan_result
    
    def _default_response(self, goal: str) -> Dict[str, Any]:
        """Default response when Ollama times out or returns an error."""
        logger.warning("[PLANNER] Using default response")
        return {
            'requires_tool': False,
            'tool_type': None,
            'action': None,
            'parameters': {},
            'response': f"I understood your goal: {goal}. Please ensure Ollama is running.",
            'reasoning': "Ollama not available",
        }

    def _unavailable_response(self, goal: str) -> Dict[str, Any]:
        """User-friendly response when Ollama is not reachable at all."""
        logger.warning("[PLANNER] Ollama unreachable — returning user-friendly error")
        return {
            'requires_tool': False,
            'tool_type': None,
            'action': None,
            'parameters': {},
            'response': (
                "Ollama is not running. "
                "Start it with: ollama run phi3.5 — "
                "then try again."
            ),
            'reasoning': "Ollama health check failed",
        }


def main():
    """Test planner"""
    planner = Planner()
    
    test_goals = [
        "What is the weather today?",
        "Tell me a joke",
        "How do I learn Python?",
    ]
    
    for goal in test_goals:
        print(f"\nGoal: {goal}")
        result = planner.plan(goal)
        print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
