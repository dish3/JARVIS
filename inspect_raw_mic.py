#!/usr/bin/env python3
"""
Text Mode Diagnostic Test Suite for Application vs URL Routing
"""

import os
import sys
import json
from dotenv import load_dotenv

# Add VirtualAssistant to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from orchestrator import Orchestrator

def main():
    load_dotenv(override=True)
    
    print("=" * 60)
    print("   JARVIS APPLICATION VS WEBSITE ROUTING TEST RUNNER   ")
    print("=" * 60)
    
    orchestrator = Orchestrator()
    
    test_commands = [
        "open chrome",
        "open edge",
        "open firefox",
        "open notepad",
        "open calculator",
        "open youtube",
        "open github",
        "open github.com",
        "open https://google.com"
    ]
    
    for cmd in test_commands:
        print(f"\n----------------------------------------")
        print(f"INPUT: {cmd}")
        
        # Route first to check classification
        route_res = orchestrator.router.route(cmd)
        
        classification = route_res.get('classification', 'unknown')
        tool_type = route_res.get('command_type', 'unknown')
        params = route_res.get('parameters', {})
        
        # Determine classification label
        print(f"CLASSIFICATION: {classification}")
        print(f"TOOL: {tool_type}")
        print(f"PARAMETERS: {json.dumps(params)}")
        
        # Execute command through orchestrator
        res = orchestrator.process_goal(cmd)
        
        success = res.get('success', False)
        result_text = res.get('result', 'None')
        
        print(f"EXECUTION: {'success' if success else 'failed'}")
        print(f"VERIFICATION: {'success' if success else 'failed'}")
        print(f"FINAL RESULT: {result_text}")
        print(f"----------------------------------------")

if __name__ == '__main__':
    main()
