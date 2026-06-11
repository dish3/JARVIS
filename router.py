#!/usr/bin/env python3
"""
JARVIS Router - Pure Python Logic
Routes goals to appropriate tools without AI
Handles: terminal commands, file operations, browser actions
"""

import re
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger('ROUTER')


class Router:
    """Routes goals to tools using pure Python logic"""
    
    def __init__(self):
        logger.info("Initializing Router...")
        self.command_patterns = self._build_patterns()
        logger.info("[OK] Router initialized")
    
    def _build_patterns(self) -> Dict[str, list]:
        """Build regex patterns for command detection"""
        return {
            'browser_open': [
                r'^(open|go to|visit|browse)\s+(?:https?://)?(.+?)\s+in\s+(chrome|firefox|edge|safari|ie)$',
                r'^(open|go to|visit|browse)\s+(?:https?://)?([^,]+?)(?:\s+in\s+(chrome|firefox|edge|safari))?$',
                r'^(open|launch)\s+(?:browser|chrome|firefox|edge)\s+([^,]+)$',
            ],
            'browser_image': [
                r'^(generate|create|make)\s+(?:an?\s+)?image\s+(?:of\s+)?(.+)$',
                r'^(generate|create|make)\s+(?:a\s+)?picture\s+(?:of\s+)?(.+)$',
                r'^(generate|create)\s+(?:an?\s+)?photo\s+(?:of\s+)?(.+)$',
                r'^draw\s+(?:a\s+|an\s+)?(.+)$',
                r'^(generate|draw|paint|sketch)\s+(.+)$',
            ],
            'browser_search': [
                r'^(search\s+)?(?:google|web)\s+(?:for\s+)?(.+)$',
                r'^(google)\s+(?:for\s+)?(.+)$',
            ],
            'web_search': [
                r'^(search|google|look up|find|what is|who is|when is|where is|how to)\s+(.+)$',
                r'^(search web|web search|search online)\s+(?:for\s+)?(.+)$',
            ],
            'linkedin_post': [
                r'^post(?:\s+to)?\s+linkedin[:\s]+(.+?)\s*\|\s*image[:\s]+(.+)$',
                r'^post(?:\s+to)?\s+linkedin[:\s]+(.+)$',
                r'^linkedin\s+post[:\s]+(.+?)\s*\|\s*image[:\s]+(.+)$',
                r'^linkedin\s+post[:\s]+(.+)$',
                r'^share(?:\s+on)?\s+linkedin[:\s]+(.+)$',
            ],
            'linkedin_delete': [
                r'^delete\s+(?:my\s+)?(?:last|latest|recent)\s+linkedin\s+post$',
                r'^delete\s+linkedin\s+post$',
                r'^remove\s+(?:my\s+)?(?:last|latest|recent)\s+linkedin\s+post$',
                r'^remove\s+linkedin\s+post$',
                r'^linkedin\s+delete\s+(?:last\s+)?post$',
            ],
            'terminal': [
                r'^(run|execute|cmd|command)\s+(.+)$',
                r'^(python|node|npm|pip)\s+(.+)$',
                r'^(ls|dir|cd|mkdir|rm|cp|mv)\s+(.+)$',
            ],
            'git_status': [
                r'^(?:git\s+)?status$',
                r'^show\s+git\s+status$',
            ],
            'git_add': [
                r'^(?:git\s+)?add\s+(.+)$',
            ],
            'git_commit': [
                r'^(?:git\s+)?commit(?:\s+changes)?(?:\s+to\s+github)?(?:\s+and\s+push)?(?:\s+with\s+message\s+(?:"([^"]+)"|\'([^\']+)\'))?$' ,
                r'^(?:git\s+)?commit(?:\s+changes)?(?:\s+to\s+github)?(?:\s+and\s+push)?(?:\s+with\s+message\s+(.+))$' ,
            ],
            'git_push': [
                r'^(?:git\s+)?push(?:\s+(?:to\s+)?([A-Za-z0-9_-]+))?(?:\s+([A-Za-z0-9_/-]+))?$',
                r'^push\s+to\s+github(?:\s+([A-Za-z0-9_/-]+))?$',
            ],
            'git_pull': [
                r'^(?:git\s+)?pull(?:\s+(?:from\s+)?([A-Za-z0-9_-]+))?(?:\s+([A-Za-z0-9_/-]+))?$',
            ],
            'git_log': [
                r'^(?:git\s+)?log(?:\s+last\s+(\d+))?$',
                r'^show\s+git\s+log$',
            ],
            'file_read': [
                r'^(read|view|cat)\s+file\s+(.+)$',
                r'^(read|view|cat)\s+(?!file|code\s)(.+)$',
                r'^(show|display)\s+file\s+(.+)$',
            ],
            'file_write': [
                r'^create\s+file\s+(.+?)\s+(?:with\s+)?(?:content\s+)?(.+)$',
                r'^(write|save)\s+(?:file\s+)?(.+?)\s+(?:with\s+)?(?:content\s+)?(.+)$',
                r'^(write|save)\s+(.+?)\s+to\s+(.+)$',
            ],
            'file_list': [
                r'^(list|ls|dir)\s+(?:files\b\s*)?(?:in\s+)?(.*)$',
                r'^(show|display)\s+(?:files|directory)\s+(?:in\s+)?(.*)$',
                r'^list files.*$',
                r'^(list|ls|dir)$',
            ],
            'code': [
                r'^(read|view|show)\s+code\s+(?:from\s+)?(.+)$',
                r'^(edit|patch|modify)\s+(.+?)\s+find\s+(.+?)\s+replace\s+(.+)$',
                r'^(run|execute)\s+(?:script\s+)?(.+\.py)$',
                r'^(create|make)\s+(?:python\s+)?(?:file\s+)?(.+\.py)\s+(?:with\s+)?(?:content\s+)?(.+)$',
                r'^open\s+(.+?)\s+in\s+(?:vs\s*code|vscode|code)$',
            ],
            'automation': [
                r'^(?:click|tap)\s+(?:at\s+)?(\d+)\s+(\d+)$',
                r'^(?:double\s+click)\s+(?:at\s+)?(\d+)\s+(\d+)$',
                r'^(?:right\s+click)\s+(?:at\s+)?(\d+)\s+(\d+)$',
                r'^type\s+(?:text\s+)?["\']?(.+?)["\']?$',
                r'^(?:take\s+(?:a\s+)?)?screenshot(?:\s+(?:as\s+)?(.+))?$',
                r'^press\s+(?:key\s+)?(.+)$',
                r'^hotkey\s+(.+)$',
                r'^scroll\s+(up|down)(?:\s+(\d+))?$',
                r'^(?:move\s+mouse\s+(?:to\s+)?)(\d+)\s+(\d+)$',
                r'^(?:get\s+)?mouse\s+position$',
                r'^(?:get\s+)?screen\s+size$',
                r'^drag\s+(?:from\s+)?(\d+)\s+(\d+)\s+(?:to\s+)?(\d+)\s+(\d+)$',
            ],
        }
    
    def route(self, goal: str) -> Dict[str, Any]:
        """
        Route a goal to appropriate tool
        
        Returns:
            {
                'is_command': bool,
                'command_type': str (terminal/file/browser),
                'action': str (execute/read/write/list/open/search),
                'parameters': dict,
                'confidence': float (0-1),
            }
        """
        goal_lower = goal.strip().lower()
        logger.info(f"[ROUTE] Analyzing: {goal}")
        logger.info(f"[ROUTER INPUT] '{goal_lower}'")
        
        # ── Compound command detection ─────────────────────────────────────
        # If the user gives a multi-step command (uses commas, "and then",
        # "then", etc.), skip pattern matching and let the Planner handle it.
        compound_markers = [', ', ' and then ', ' then ', ' after that ', ' afterwards ']
        has_compound = any(marker in goal_lower for marker in compound_markers)
        # Also check for " and " but only if it's followed by an action verb
        action_verbs = ['sign', 'login', 'log in', 'post', 'open', 'click', 'type',
                        'search', 'create', 'write', 'read', 'run', 'take', 'send',
                        'delete', 'download', 'upload', 'close', 'save', 'share']
        if ' and ' in goal_lower:
            after_and = goal_lower.split(' and ', 1)[1].strip()
            if any(after_and.startswith(verb) for verb in action_verbs):
                has_compound = True
        
        if has_compound:
            logger.info(f"[ROUTE] Compound command detected, delegating to planner")
            return {
                'is_command': False,
                'needs_planner': True,
                'confidence': 0.0,
            }

        def _match(result: dict) -> dict:
            """Log a successful match and return the result unchanged."""
            if result.get('is_command'):
                logger.info(
                    f"[ROUTER MATCH] {result['command_type']}/{result['action']} "
                    f"← {goal!r}"
                )
            return result
        
        # VS Code open — check FIRST before browser patterns
        vscode_match = re.match(r'^open\s+(?:file\s+)?(.+?)\s+in\s+(?:vs\s*code|vscode|code)$', goal_lower)
        if vscode_match:
            filepath = vscode_match.group(1)
            logger.info(f"[ROUTE] VS Code open command detected")
            return _match({
                'is_command': True,
                'command_type': 'code',
                'action': 'open_vscode',
                'parameters': {'path': filepath},
                'confidence': 0.95,
            })
        
        # Check browser commands FIRST (before file commands)
        # Browser open
        for pattern in self.command_patterns['browser_open']:
            match = re.match(pattern, goal_lower)
            if match:
                logger.info(f"[ROUTE] Browser open command detected")
                groups = match.groups()
                
                # Check if browser is specified (group 3 is not None) or not
                if len(groups) >= 3 and groups[2] is not None:
                    url = groups[1].strip()
                    browser = groups[2].strip()
                else:
                    url = groups[1].strip()
                    browser = None
                
                # Add protocol if missing
                if not url.startswith(('http://', 'https://', 'ftp://')):
                    # Handle common domain names
                    domain_map = {
                        'youtube': 'youtube.com',
                        'google': 'google.com',
                        'github': 'github.com',
                        'stackoverflow': 'stackoverflow.com',
                        'reddit': 'reddit.com',
                        'twitter': 'twitter.com',
                        'facebook': 'facebook.com',
                        'instagram': 'instagram.com',
                        'linkedin': 'linkedin.com',
                    }
                    
                    # Check if it's a known domain
                    for key, domain in domain_map.items():
                        if url.lower() == key or url.lower().startswith(key + ' '):
                            url = domain
                            break
                    
                    url = 'https://' + url
                
                params = {'url': url}
                if browser:
                    params['browser'] = browser
                
                return {
                    'is_command': True,
                    'command_type': 'browser',
                    'action': 'open',
                    'parameters': params,
                    'confidence': 0.9,
                }
        
        # Browser image generation — must be before file_write (which also matches 'create ...')
        for pattern in self.command_patterns['browser_image']:
            match = re.match(pattern, goal_lower)
            if match:
                logger.info(f"[ROUTE] Image generation command detected")
                return {
                    'is_command': True,
                    'command_type': 'browser',
                    'action': 'generate_image',
                    'parameters': {'prompt': match.group(2) if len(match.groups()) > 1 else match.group(1), 'action': 'generate_image'},
                    'confidence': 0.9,
                }
        
        # LinkedIn post — check before web_search ('post' could match search patterns)
        for pattern in self.command_patterns['linkedin_post']:
            # Use original goal (not lowercased) to preserve file path case
            match = re.match(pattern, goal, re.IGNORECASE)
            if match:
                logger.info(f"[ROUTE] LinkedIn post command detected")
                groups = match.groups()
                params = {'text': groups[0].strip()}
                if len(groups) > 1 and groups[1]:
                    params['image_path'] = groups[1].strip()
                    logger.info(f"[LINKEDIN] Image path: {params['image_path']}")
                return {
                    'is_command': True,
                    'command_type': 'linkedin',
                    'action': 'post',
                    'parameters': params,
                    'confidence': 0.9,
                }

        # LinkedIn delete last post
        for pattern in self.command_patterns['linkedin_delete']:
            match = re.match(pattern, goal_lower)
            if match:
                logger.info(f"[ROUTE] LinkedIn delete post command detected")
                return {
                    'is_command': True,
                    'command_type': 'linkedin',
                    'action': 'delete',
                    'parameters': {},
                    'confidence': 0.95,
                }
        
        # Browser search (explicit "open browser and search" intent) — checked BEFORE web_search to capture direct browser search commands
        for pattern in self.command_patterns['browser_search']:
            match = re.match(pattern, goal_lower)
            if match:
                logger.info(f"[ROUTE] Browser search command detected")
                return {
                    'is_command': True,
                    'command_type': 'browser',
                    'action': 'search',
                    'parameters': {'query': match.group(2) or match.group(1)},
                    'confidence': 0.85,
                }

        # Web search — checked after browser_search
        for pattern in self.command_patterns['web_search']:
            match = re.match(pattern, goal_lower)
            if match:
                logger.info(f"[ROUTE] Web search command detected")
                return {
                    'is_command': True,
                    'command_type': 'search',
                    'action': 'search',
                    'parameters': {'query': match.group(2)},
                    'confidence': 0.9,
                }

        # Git commands
        for pattern in self.command_patterns['git_status']:
            match = re.match(pattern, goal_lower)
            if match:
                logger.info(f"[ROUTE] Git status command detected")
                return {
                    'is_command': True,
                    'command_type': 'git',
                    'action': 'status',
                    'parameters': {},
                    'confidence': 0.95,
                }

        for pattern in self.command_patterns['git_add']:
            match = re.match(pattern, goal_lower)
            if match:
                logger.info(f"[ROUTE] Git add command detected")
                return {
                    'is_command': True,
                    'command_type': 'git',
                    'action': 'add',
                    'parameters': {'path': match.group(1).strip()},
                    'confidence': 0.95,
                }

        for pattern in self.command_patterns['git_commit']:
            match = re.match(pattern, goal_lower)
            if match:
                message = match.group(1) or match.group(2)
                logger.info(f"[ROUTE] Git commit command detected")
                return {
                    'is_command': True,
                    'command_type': 'git',
                    'action': 'commit',
                    'parameters': {'message': message.strip() if message else ''},
                    'confidence': 0.95,
                }

        for pattern in self.command_patterns['git_push']:
            match = re.match(pattern, goal_lower)
            if match:
                remote = match.group(1) or 'origin'
                branch = match.group(2)
                logger.info(f"[ROUTE] Git push command detected")
                return {
                    'is_command': True,
                    'command_type': 'git',
                    'action': 'push',
                    'parameters': {'remote': remote.strip(), 'branch': branch.strip() if branch else None},
                    'confidence': 0.95,
                }

        for pattern in self.command_patterns['git_pull']:
            match = re.match(pattern, goal_lower)
            if match:
                remote = match.group(1) or 'origin'
                branch = match.group(2)
                logger.info(f"[ROUTE] Git pull command detected")
                return {
                    'is_command': True,
                    'command_type': 'git',
                    'action': 'pull',
                    'parameters': {'remote': remote.strip(), 'branch': branch.strip() if branch else None},
                    'confidence': 0.95,
                }

        for pattern in self.command_patterns['git_log']:
            match = re.match(pattern, goal_lower)
            if match:
                try:
                    count = match.group(1)
                except IndexError:
                    count = None
                logger.info(f"[ROUTE] Git log command detected")
                return {
                    'is_command': True,
                    'command_type': 'git',
                    'action': 'log',
                    'parameters': {'count': int(count) if count else 5},
                    'confidence': 0.95,
                }

        # Check terminal commands
        for pattern in self.command_patterns['terminal']:
            match = re.match(pattern, goal_lower)
            if match:
                logger.info(f"[ROUTE] Terminal command detected")
                return {
                    'is_command': True,
                    'command_type': 'terminal',
                    'action': 'execute',
                    'parameters': {'command': goal},
                    'confidence': 0.95,
                }
        
        # Check file read
        for pattern in self.command_patterns['file_read']:
            match = re.match(pattern, goal_lower)
            if match:
                logger.info(f"[ROUTE] File read command detected")
                return {
                    'is_command': True,
                    'command_type': 'file',
                    'action': 'read',
                    'parameters': {'path': match.group(2)},
                    'confidence': 0.9,
                }
        
        # Check file write
        for pattern in self.command_patterns['file_write']:
            match = re.match(pattern, goal_lower)
            if match:
                logger.info(f"[ROUTE] File write command detected")
                groups = match.groups()
                return {
                    'is_command': True,
                    'command_type': 'file',
                    'action': 'write',
                    'parameters': {
                        'path': groups[1] if len(groups) > 2 else groups[0],
                        'content': groups[-1],
                    },
                    'confidence': 0.9,
                }
        
        # Check file list
        for pattern in self.command_patterns['file_list']:
            match = re.match(pattern, goal_lower)
            if match:
                logger.info(f"[ROUTE] File list command detected")
                return {
                    'is_command': True,
                    'command_type': 'file',
                    'action': 'list',
                    'parameters': {'path': match.group(2) or '.'},
                    'confidence': 0.9,
                }
        
        # Code tool commands
        for pattern in self.command_patterns['code']:
            match = re.match(pattern, goal_lower)
            if match:
                logger.info(f"[ROUTE] Code command detected")
                groups = match.groups()
                # Determine action from the verb
                verb = groups[0] if groups else ''
                if verb in ('read', 'view', 'show'):
                    return _match({
                        'is_command': True,
                        'command_type': 'code',
                        'action': 'read',
                        'parameters': {'path': groups[1]},
                        'confidence': 0.9,
                    })
                elif verb in ('edit', 'patch', 'modify'):
                    return _match({
                        'is_command': True,
                        'command_type': 'code',
                        'action': 'patch',
                        'parameters': {'path': groups[1], 'find': groups[2], 'replace': groups[3]},
                        'confidence': 0.9,
                    })
                elif verb in ('run', 'execute'):
                    return _match({
                        'is_command': True,
                        'command_type': 'code',
                        'action': 'run',
                        'parameters': {'path': groups[1]},
                        'confidence': 0.9,
                    })
                elif verb in ('create', 'make'):
                    return _match({
                        'is_command': True,
                        'command_type': 'code',
                        'action': 'create',
                        'parameters': {'path': groups[1], 'content': groups[2]},
                        'confidence': 0.9,
                    })
                else:
                    # 'open ... in vscode' pattern has no verb group prefix
                    return _match({
                        'is_command': True,
                        'command_type': 'code',
                        'action': 'open_vscode',
                        'parameters': {'path': groups[0]},
                        'confidence': 0.95,
                    })

        # Automation commands
        for pattern in self.command_patterns['automation']:
            match = re.match(pattern, goal_lower)
            if match:
                logger.info(f"[ROUTE] Automation command detected")
                groups = match.groups()
                # Detect action from pattern
                if goal_lower.startswith(('click', 'tap')):
                    return _match({
                        'is_command': True,
                        'command_type': 'automation',
                        'action': 'click',
                        'parameters': {'x': int(groups[0]), 'y': int(groups[1])},
                        'confidence': 0.9,
                    })
                elif goal_lower.startswith('double click'):
                    return _match({
                        'is_command': True,
                        'command_type': 'automation',
                        'action': 'double_click',
                        'parameters': {'x': int(groups[0]), 'y': int(groups[1])},
                        'confidence': 0.9,
                    })
                elif goal_lower.startswith('right click'):
                    return _match({
                        'is_command': True,
                        'command_type': 'automation',
                        'action': 'right_click',
                        'parameters': {'x': int(groups[0]), 'y': int(groups[1])},
                        'confidence': 0.9,
                    })
                elif goal_lower.startswith('type'):
                    return _match({
                        'is_command': True,
                        'command_type': 'automation',
                        'action': 'type',
                        'parameters': {'text': groups[0]},
                        'confidence': 0.9,
                    })
                elif 'screenshot' in goal_lower:
                    return _match({
                        'is_command': True,
                        'command_type': 'automation',
                        'action': 'screenshot',
                        'parameters': {'filename': groups[0] if groups[0] else 'screenshot.png'},
                        'confidence': 0.95,
                    })
                elif goal_lower.startswith('press'):
                    return _match({
                        'is_command': True,
                        'command_type': 'automation',
                        'action': 'press_key',
                        'parameters': {'key': groups[0]},
                        'confidence': 0.9,
                    })
                elif goal_lower.startswith('hotkey'):
                    keys = [k.strip() for k in groups[0].split('+')]
                    return _match({
                        'is_command': True,
                        'command_type': 'automation',
                        'action': 'hotkey',
                        'parameters': {'keys': keys},
                        'confidence': 0.9,
                    })
                elif goal_lower.startswith('scroll'):
                    direction = groups[0]
                    amount = int(groups[1]) if groups[1] else 5
                    clicks = amount if direction == 'up' else -amount
                    return _match({
                        'is_command': True,
                        'command_type': 'automation',
                        'action': 'scroll',
                        'parameters': {'clicks': clicks},
                        'confidence': 0.9,
                    })
                elif 'mouse position' in goal_lower:
                    return _match({
                        'is_command': True,
                        'command_type': 'automation',
                        'action': 'get_mouse_position',
                        'parameters': {},
                        'confidence': 0.9,
                    })
                elif 'screen size' in goal_lower:
                    return _match({
                        'is_command': True,
                        'command_type': 'automation',
                        'action': 'get_screen_size',
                        'parameters': {},
                        'confidence': 0.9,
                    })
                elif goal_lower.startswith('move mouse'):
                    return _match({
                        'is_command': True,
                        'command_type': 'automation',
                        'action': 'move_mouse',
                        'parameters': {'x': int(groups[0]), 'y': int(groups[1])},
                        'confidence': 0.9,
                    })
                elif goal_lower.startswith('drag'):
                    return _match({
                        'is_command': True,
                        'command_type': 'automation',
                        'action': 'drag_drop',
                        'parameters': {'x1': int(groups[0]), 'y1': int(groups[1]), 'x2': int(groups[2]), 'y2': int(groups[3])},
                        'confidence': 0.9,
                    })

        # No command matched
        logger.info(f"[ROUTE] No command matched, needs planner")
        logger.info(f"[ROUTER FAIL] No pattern matched for: {goal!r}")
        return {
            'is_command': False,
            'command_type': None,
            'action': None,
            'parameters': {},
            'confidence': 0.0,
        }


def main():
    """Test router"""
    router = Router()
    
    test_goals = [
        "open chrome",
        "search google for python tutorials",
        "create a file called test.txt with content hello world",
        "list files in current directory",
        "run python script.py",
        "read file config.json",
    ]
    
    for goal in test_goals:
        print(f"\nGoal: {goal}")
        result = router.route(goal)
        print(f"Result: {result}")


if __name__ == '__main__':
    main()
