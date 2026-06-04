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
        
        logger.info("[OK] Orchestrator initialized successfully")
    
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
            # Step 1: Check if it's a pure routing task (no AI needed)
            logger.info("[STEP 1] Checking router for pure logic tasks...")
            route_result = self.router.route(goal)
            
            if route_result['is_command']:
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
                response['logs'].append(f"[COMMAND EXECUTED] {route_result['command_type']}")

                # Persist this interaction to memory (router path)
                self.memory.store_interaction(goal, response['result'])
                response['memory_updated'] = True

                return response
            
            # Step 2: If not a pure command, use planner (Ollama)
            logger.info("[STEP 2] Calling planner for reasoning...")
            plan = self.planner.plan(goal, self.memory.get_context())
            
            tool_type = plan.get('tool_type', 'none')
            requires_tool = plan.get('requires_tool', False)
            
            if requires_tool and tool_type and not any(tool_type.lower().startswith(x) for x in ('none', 'unknown', '')):
                logger.info(f"[PLANNER] Tool needed: {tool_type}")
                response['tool_used'] = tool_type
                
                # Execute the tool
                tool_result = self._execute_tool(tool_type, plan.get('parameters', {}))
                
                response['success'] = tool_result['success']
                response['result'] = tool_result['result']
                response['logs'].append(f"[TOOL EXECUTED] {tool_type}")
            else:
                # No tool needed — return planner's text response directly
                response['success'] = True
                response['result'] = plan.get('response') or plan.get('result') or "Done."
                response['logs'].append("[PLANNER] Text response returned")
            
            # Step 3: Update memory
            logger.info("[STEP 3] Updating memory...")
            self.memory.store_interaction(goal, response['result'])
            response['memory_updated'] = True
            
            logger.info(f"[SUCCESS] Goal processed: {goal}")
            return response
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to process goal: {str(e)}", exc_info=True)
            response['success'] = False
            response['result'] = f"Error: {str(e)}"
            response['logs'].append(f"[ERROR] {str(e)}")
            return response
    
    def _execute_tool(self, tool_type: str, parameters: Dict) -> Dict[str, Any]:
        """Execute a specific tool"""
        logger.info(f"[TOOL] Executing {tool_type} with params: {parameters}")
        
        if tool_type not in self.tools and tool_type != 'vscode':
            return {
                'success': False,
                'result': f"Unknown tool: {tool_type}"
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
                        return {'success': False, 'result': 'Error: Git commit requires a commit message.'}
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
            
            return {
                'success': True,
                'result': result
            }
        except Exception as e:
            logger.error(f"[TOOL ERROR] {tool_type}: {str(e)}")
            return {
                'success': False,
                'result': f"Tool error: {str(e)}"
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
