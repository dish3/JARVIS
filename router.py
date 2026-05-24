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
                r'^(open|go to|visit|browse)\s+(?:https?://)?(.+)$',
                r'^(open|launch)\s+(?:browser|chrome|firefox|edge)\s+(.+)$',
            ],
            'browser_image': [
                r'^(generate|create|make)\s+(?:an?\s+)?image\s+(?:of\s+)?(.+)$',
                r'^(generate|create|make)\s+(?:a\s+)?picture\s+(?:of\s+)?(.+)$',
                r'^(generate|create)\s+(?:an?\s+)?photo\s+(?:of\s+)?(.+)$',
                r'^draw\s+(?:a\s+|an\s+)?(.+)$',
                r'^(generate|create|make|draw|paint|sketch)\s+(.+)$',
            ],
            'browser_search': [
                r'^(search|google|find)\s+(?:for\s+)?(.+)$',
                r'^(search\s+)?(?:google|web)\s+(?:for\s+)?(.+)$',
            ],
            'terminal': [
                r'^(run|execute|cmd|command)\s+(.+)$',
                r'^(python|node|npm|pip)\s+(.+)$',
                r'^(ls|dir|cd|mkdir|rm|cp|mv)\s+(.+)$',
            ],
            'file_read': [
                r'^(read|view|cat)\s+file\s+(.+)$',
                r'^(read|view|cat)\s+(?!file)(.+)$',
                r'^(show|display)\s+file\s+(.+)$',
                r'^read\s+(.+)$',
            ],
            'file_write': [
                r'^(create|write|save)\s+(?:file\s+)?(.+?)\s+(?:with\s+)?(?:content\s+)?(.+)$',
                r'^(write|save)\s+(.+?)\s+to\s+(.+)$',
            ],
            'file_list': [
                r'^(list|ls|dir)\s+(?:files\s+)?(?:in\s+)?(.*)$',
                r'^(show|display)\s+(?:files|directory)\s+(.*)$',
                r'^list files.*$',
                r'^(list|ls|dir)$',
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
        logger.info(f"[ROUTE] Analyzing: {goal}")
        
        goal_lower = goal.lower().strip()
        
        # Check browser commands FIRST (before file commands)
        # Browser open
        for pattern in self.command_patterns['browser_open']:
            match = re.match(pattern, goal_lower)
            if match:
                logger.info(f"[ROUTE] Browser open command detected")
                groups = match.groups()
                
                # Check if browser is specified (3 groups) or not (2 groups)
                if len(groups) == 3:
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
        
        # Browser search
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
        
        # No command matched
        logger.info(f"[ROUTE] No command matched, needs planner")
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
