#!/usr/bin/env python3
"""
JARVIS Orchestrator - Central Controller
Receives goals from voice/text input
Calls planner, router, executes tools, updates memory
"""

import json
import sys
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import asyncio
import os

# Fix encoding for Windows console - must be first
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(name)s] %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler('jarvis.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('ORCHESTRATOR')

# Import components
from planner import Planner
from router import Router
from memory import Memory
from tools.terminal_tool import TerminalTool
from tools.file_tool import FileTool
from tools.browser_tool import BrowserTool
from tools.search_tool import SearchTool
from tools.linkedin_tool import LinkedInTool
from tools.git_tool import GitTool
from tools.code_tool import CodeTool
from tools.automation_tool import AutomationTool


class Orchestrator:
    """Central controller that orchestrates all components"""
    
    def __init__(self):
        logger.info("Initializing JARVIS Orchestrator...")
        
        self.planner = Planner()
        self.router = Router()
        self.memory = Memory()
        
        # Initialize tools
        self.terminal_tool = TerminalTool()
        self.file_tool = FileTool()
        self.browser_tool = BrowserTool()
        self.search_tool = SearchTool()
        self.linkedin_tool = LinkedInTool()
        self.git_tool = GitTool()
        self.code_tool = CodeTool()
        self.automation_tool = AutomationTool()
        
        self.tools = {
            'terminal': self.terminal_tool,
            'file': self.file_tool,
            'browser': self.browser_tool,
            'search': self.search_tool,
            'linkedin': self.linkedin_tool,
            'git': self.git_tool,
            'code': self.code_tool,
            'automation': self.automation_tool,
        }
        self._cancel_flag = None
        
        logger.info("[OK] Orchestrator initialized successfully")

    @property
    def cancel_flag(self):
        return getattr(self, '_cancel_flag', None)
        
    @cancel_flag.setter
    def cancel_flag(self, val):
        self._cancel_flag = val
        # Propagate to all tools
        for tool in self.tools.values():
            if hasattr(tool, 'cancel_flag'):
                tool.cancel_flag = val
            try:
                tool._cancel_flag = val
            except Exception:
                pass
                
    def check_cancellation(self):
        if self.cancel_flag and self.cancel_flag.is_set():
            raise Exception("__CANCEL__ received. Aborting task execution.")
    
    def process_goal(self, goal: str, user_context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Main entry point: Process a user goal
        
        Args:
            goal: User's spoken/typed goal
            user_context: Optional context about user
            
        Returns:
            Response dict with result, logs, memory updates
        """
        logger.info(f"[GOAL] Processing: {goal}")
        
        response = {
            'goal': goal,
            'timestamp': datetime.now().isoformat(),
            'success': False,
            'result': None,
            'tool_used': None,
            'logs': [],
            'memory_updated': False,
        }
        
        try:
            self.check_cancellation()
            # Step 0: Detect language and translate to English if non-English
            detected_lang = 'en'
            original_goal = goal
            try:
                detected_lang = self.planner.detect_language(goal)
                if detected_lang != 'en':
                    logger.info(f"[LANGUAGE] Non-English input detected ({detected_lang}). Translating to English...")
                    goal = self.planner.translate_text(goal, 'en')
                    logger.info(f"[LANGUAGE] Translated goal: '{goal}'")
                    response['logs'].append(f"[LANGUAGE] Translated goal from {detected_lang}: '{goal}'")
            except Exception as lang_err:
                logger.warning(f"[LANGUAGE] Language detection/translation failed: {lang_err}")

            self.check_cancellation()
            # Step 1: Check if it's a pure routing task (no AI needed)
            logger.info("[STEP 1] Checking router for pure logic tasks...")
            route_result = self.router.route(goal)
            
            if route_result['is_command']:
                self.check_cancellation()
                logger.info(f"[ROUTER] Command detected: {route_result['command_type']}")
                response['tool_used'] = route_result['command_type']
                
                # Ensure action is set for file and browser tools
                tool_type = route_result['command_type']
                parameters = route_result['parameters']
                
                # Add action from router if available
                router_action = route_result.get('action', '')
                if router_action:
                    parameters['action'] = router_action
                
                if 'file' in tool_type:
                    # Fallback: guess from command_type if action not set
                    if 'action' not in parameters:
                        cmd = route_result.get('command_type', '')
                        if 'read' in cmd:
                            parameters['action'] = 'read'
                        elif 'write' in cmd:
                            parameters['action'] = 'write'
                        else:
                            parameters['action'] = 'list'
                    
                    if parameters.get('path') in ('current directory', '', None):
                        import os
                        parameters['path'] = os.getcwd()
                
                # Execute the command
                base_tool = tool_type.split('_')[0]  # 'file_read' -> 'file'
                tool_result = self._execute_tool(
                    base_tool,
                    parameters
                )
                
                response['success'] = tool_result['success']
                response['result'] = tool_result['result']
                if 'logs' in tool_result and tool_result['logs']:
                    response['logs'].extend(tool_result['logs'])
                if 'screenshots' in tool_result and tool_result['screenshots']:
                    if 'screenshots' not in response:
                        response['screenshots'] = []
                    response['screenshots'].extend(tool_result['screenshots'])
                response['logs'].append(f"[COMMAND EXECUTED] {route_result['command_type']}")

                # Persist this interaction to memory (router path)
                self.memory.store_interaction(original_goal, response['result'])
                response['memory_updated'] = True

                # Translate response back to original language if needed
                if detected_lang != 'en' and response['result']:
                    try:
                        logger.info(f"[LANGUAGE] Translating response back to {detected_lang}...")
                        translated_res = self.planner.translate_text(response['result'], detected_lang)
                        response['result'] = translated_res
                    except Exception as translate_err:
                        logger.warning(f"[LANGUAGE] Response translation failed: {translate_err}")

                return response
            
            self.check_cancellation()
            # Step 2: If not a pure command, use planner (Ollama)
            logger.info("[STEP 2] Calling planner for reasoning...")
            plan = self.planner.plan(goal, self.memory.get_context())
            
            tool_type = plan.get('tool_type', 'none')
            requires_tool = plan.get('requires_tool', False)
            
            if requires_tool and tool_type and not any(tool_type.lower().startswith(x) for x in ('none', 'unknown') if x):
                self.check_cancellation()
                logger.info(f"[PLANNER] Tool needed: {tool_type}")
                response['tool_used'] = tool_type
                
                # Execute the tool
                tool_result = self._execute_tool(tool_type, plan.get('parameters', {}))
                
                response['success'] = tool_result['success']
                response['result'] = tool_result['result']
                if 'logs' in tool_result and tool_result['logs']:
                    response['logs'].extend(tool_result['logs'])
                if 'screenshots' in tool_result and tool_result['screenshots']:
                    if 'screenshots' not in response:
                        response['screenshots'] = []
                    response['screenshots'].extend(tool_result['screenshots'])
                response['logs'].append(f"[TOOL EXECUTED] {tool_type}")
            else:
                # No tool needed — return planner's text response directly
                response['success'] = True
                response['result'] = plan.get('response') or plan.get('result') or "Done."
                response['logs'].append("[PLANNER] Text response returned")
            
            self.check_cancellation()
            # Step 3: Update memory
            logger.info("[STEP 3] Updating memory...")
            self.memory.store_interaction(original_goal, response['result'], assistant_response=plan.get('reasoning'))
            response['memory_updated'] = True
            
            # Translate response back to original language if needed
            if detected_lang != 'en' and response['result']:
                try:
                    logger.info(f"[LANGUAGE] Translating response back to {detected_lang}...")
                    translated_res = self.planner.translate_text(response['result'], detected_lang)
                    response['result'] = translated_res
                except Exception as translate_err:
                    logger.warning(f"[LANGUAGE] Response translation failed: {translate_err}")

            logger.info(f"[SUCCESS] Goal processed: {goal}")
            return response
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to process goal: {str(e)}", exc_info=True)
            response['success'] = False
            response['result'] = f"Error: {str(e)}"
            response['logs'].append(f"[ERROR] {str(e)}")
            return response
    
    def _verify_execution(self, tool_type: str, parameters: Dict, return_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Verify that a tool execution had the expected physical/process effect."""
        # If execution already failed, don't overwrite the error with verification
        if not return_dict.get('success', False):
            return {'success': True}

        import time

        try:
            import psutil
        except ImportError:
            logger.warning("[VERIFY] psutil not installed — skipping process verification checks")
            return {'success': True}

        try:
            if tool_type == 'browser':
                action = parameters.get('action')
                if action == 'open':
                    # Allow browser window a moment to spawn/register
                    time.sleep(1.0)
                    browser_name = parameters.get('browser', '')
                    expected_procs = []
                    if browser_name:
                        name_lower = browser_name.lower()
                        if 'chrome' in name_lower:
                            expected_procs.append('chrome.exe')
                        elif 'edge' in name_lower:
                            expected_procs.append('msedge.exe')
                        elif 'firefox' in name_lower:
                            expected_procs.append('firefox.exe')
                    else:
                        # Fallback list of common browsers
                        expected_procs = ['chrome.exe', 'msedge.exe', 'firefox.exe', 'browser']

                    # Scan processes
                    running_procs = []
                    for p in psutil.process_iter(['name']):
                        try:
                            name = p.info['name']
                            if name:
                                running_procs.append(name.lower())
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue

                    found = False
                    for exp in expected_procs:
                        if any(exp in r for r in running_procs):
                            found = True
                            break

                    if not found:
                        return {
                            'success': False,
                            'error': f"Browser process not found. Expected: {expected_procs}"
                        }

                    # Optional: Verify active window matches browser
                    try:
                        import pyautogui
                        active_win = pyautogui.getActiveWindowTitle() or ""
                        logger.info(f"[VERIFY] Browser open active window: '{active_win}'")
                    except Exception as e:
                        logger.warning(f"Could not check active window: {e}")

            elif tool_type in ('vscode', 'code'):
                action = parameters.get('action')
                if action == 'open_vscode':
                    time.sleep(1.0)
                    running = False
                    for p in psutil.process_iter(['name']):
                        try:
                            name = p.info['name']
                            if name and 'code.exe' in name.lower():
                                running = True
                                break
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue
                    if not running:
                        return {
                            'success': False,
                            'error': "VS Code process (code.exe) not found running"
                        }

            elif tool_type == 'file':
                action = parameters.get('action')
                path = parameters.get('path')
                if action == 'write' and path:
                    if not os.path.exists(path):
                        return {
                            'success': False,
                            'error': f"File not found on disk after write: {path}"
                        }
                    if os.path.getsize(path) == 0:
                        content = parameters.get('content', '')
                        if content:
                            return {
                                'success': False,
                                'error': f"File is empty (0 bytes) after write: {path}"
                            }

        except Exception as err:
            logger.warning(f"[VERIFY] Post-execution verification encountered error: {err}")
            # Do not fail verification on unexpected internal code errors
            return {'success': True}

        return {'success': True}

    def _execute_tool(self, tool_type: str, parameters: Dict) -> Dict[str, Any]:
        """Execute a specific tool"""
        logger.info(f"[TOOL] Executing {tool_type} with params: {parameters}")
        
        self.check_cancellation()
        
        if tool_type not in self.tools and tool_type != 'vscode':
            return {
                'success': False,
                'result': f"Unknown tool: {tool_type}",
                'logs': [f"[ERROR] Unknown tool: {tool_type}"],
                'screenshots': [],
                'state': ''
            }
        
        tool = self.tools.get(tool_type)
        
        try:
            if tool_type == 'terminal':
                result = tool.execute(parameters.get('command', ''))
            elif tool_type == 'file':
                action = parameters.get('action', '')
                if action == 'read':
                    result = tool.read(parameters.get('path', ''))
                elif action == 'write':
                    result = tool.write(parameters.get('path', ''), parameters.get('content', ''))
                elif action == 'list':
                    result = tool.list_files(parameters.get('path', '.'))
                else:
                    result = f"Unknown file action: {action}"
            elif tool_type == 'browser':
                action = parameters.get('action', '')
                if action == 'open':
                    browser = parameters.get('browser', None)
                    result = tool.open_url(parameters.get('url', ''), browser=browser)
                elif action == 'search':
                    result = tool.search(parameters.get('query', ''))
                elif action == 'generate_image':
                    result = tool.generate_image(parameters.get('prompt', ''))
                else:
                    result = f"Unknown browser action: {action}"
            elif tool_type == 'git':
                action = parameters.get('action', '')
                if action == 'status':
                    result = tool.status()
                elif action == 'add':
                    result = tool.add(parameters.get('path', '.'))
                elif action == 'commit':
                    message = parameters.get('message', '')
                    if not message:
                        return {
                            'success': False,
                            'result': 'Error: Git commit requires a commit message.',
                            'logs': ['[ERROR] Git commit missing message'],
                            'screenshots': [],
                            'state': ''
                        }
                    result = tool.commit(message)
                elif action == 'push':
                    result = tool.push(parameters.get('remote', 'origin'), parameters.get('branch'))
                elif action == 'pull':
                    result = tool.pull(parameters.get('remote', 'origin'), parameters.get('branch'))
                elif action == 'log':
                    count = parameters.get('count', 5)
                    result = tool.log(count)
                else:
                    result = f"Unknown git action: {action}"
            elif tool_type == 'vscode':
                # Legacy — delegate to code tool
                parameters['action'] = 'open_vscode'
                result = self.code_tool.execute(parameters)
            elif tool_type == 'code':
                result = self.code_tool.execute(parameters)
            elif tool_type == 'automation':
                logger.warning(f"[AUTOMATION] Executing desktop action: {parameters.get('action', 'unknown')}")
                result = self.automation_tool.execute(parameters)
            elif tool_type == 'search':
                result = tool.search(parameters.get('query', ''))
            elif tool_type == 'linkedin':
                action = parameters.get('action', '')
                if action == 'delete':
                    result = tool.delete_last_post()
                else:
                    result = tool.post(
                        parameters.get('text', ''),
                        parameters.get('image_path', None)
                    )
            else:
                result = "Tool not implemented"
            
            # Map structured tool outputs and verify
            if isinstance(result, dict) and 'status' in result:
                success = result.get('status') == 'success'
                res_val = result.get('result')
                if isinstance(res_val, dict) and 'message' in res_val:
                    res_val = res_val['message']
                logs = result.get('logs', [])
                screenshots = result.get('screenshots', [])
                state = result.get('state', '')
            else:
                success = True
                res_val = result
                logs = []
                screenshots = []
                state = ''
                
            return_dict = {
                'success': success,
                'result': res_val,
                'logs': logs,
                'screenshots': screenshots,
                'state': state
            }
            
            # Run post-execution verification checks
            verify_res = self._verify_execution(tool_type, parameters, return_dict)
            if not verify_res['success']:
                return_dict['success'] = False
                err_msg = f"Verification failed: {verify_res.get('error')}"
                return_dict['result'] = err_msg
                return_dict['logs'].append(f"[VERIFY] {err_msg}")
                
            return return_dict
            
        except Exception as e:
            logger.error(f"[TOOL ERROR] {tool_type}: {str(e)}")
            return {
                'success': False,
                'result': f"Tool error: {str(e)}",
                'logs': [f"[TOOL ERROR] {str(e)}"],
                'screenshots': [],
                'state': ''
            }
    
    def get_status(self) -> Dict[str, Any]:
        """Get current system status"""
        return {
            'status': 'running',
            'timestamp': datetime.now().isoformat(),
            'memory_size': len(self.memory.interactions),
            'tools_available': list(self.tools.keys()),
        }


def main():
    """Main entry point for testing"""
    orchestrator = Orchestrator()
    
    # Test goals
    test_goals = [
        "open chrome",
        "create a file called test.txt with content hello world",
        "search google for python tutorials",
        "list files in current directory",
    ]
    
    for goal in test_goals:
        print(f"\n{'='*60}")
        print(f"Goal: {goal}")
        print('='*60)
        
        result = orchestrator.process_goal(goal)
        print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
