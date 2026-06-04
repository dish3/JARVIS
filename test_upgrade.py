#!/usr/bin/env python3
"""
JARVIS Brain Upgrade - Verification Script
Tests all changes: Planner (Groq/Ollama), Router, Memory, Tools
Run: python test_upgrade.py
"""

import sys
import os
import json

# Ensure we're in the right directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Suppress verbose logging during tests
import logging
logging.basicConfig(level=logging.WARNING, format='[%(name)s] %(message)s')

PASS = "✅"
FAIL = "❌"
WARN = "⚠️"
results = []


def test(name, func):
    """Run a test and record result."""
    try:
        result = func()
        if result:
            results.append((PASS, name))
            print(f"  {PASS} {name}")
        else:
            results.append((FAIL, name))
            print(f"  {FAIL} {name}")
    except Exception as e:
        results.append((FAIL, f"{name}: {e}"))
        print(f"  {FAIL} {name}: {e}")


# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("  JARVIS BRAIN UPGRADE — VERIFICATION")
print("=" * 60)

# ── Phase 1: Planner ─────────────────────────────────────────────────────────
print("\n📦 Phase 1: Planner (Groq + Ollama)")

def test_planner_import():
    from planner import Planner, GROQ_API_KEY, GROQ_MODEL, AI_BACKEND
    return True

def test_planner_config():
    from planner import GROQ_API_KEY, GROQ_MODEL, AI_BACKEND
    assert GROQ_MODEL == 'llama-3.3-70b-versatile', f"Expected llama-3.3-70b-versatile, got {GROQ_MODEL}"
    assert AI_BACKEND in ('groq', 'ollama', 'auto'), f"Invalid AI_BACKEND: {AI_BACKEND}"
    return True

def test_groq_sdk():
    try:
        from groq import Groq
        return True
    except ImportError:
        print(f"    {WARN} groq SDK not installed — run: pip install groq")
        return False

def test_planner_init():
    from planner import Planner
    p = Planner()
    # Check it has the right attributes
    assert hasattr(p, '_groq_client'), "Missing _groq_client"
    assert hasattr(p, '_groq_available'), "Missing _groq_available"
    assert hasattr(p, '_ollama_available'), "Missing _ollama_available"
    return True

def test_planner_json_parse():
    from planner import Planner
    p = Planner()
    # Test JSON response parsing
    fake_json = '{"tool": "browser", "action": "open", "parameters": {"url": "https://google.com"}, "response": "Opening Google"}'
    result = p._parse_json_response(fake_json, "open google")
    assert result['requires_tool'] == True
    assert result['tool_type'] == 'browser'
    assert result['response'] == 'Opening Google'
    return True

def test_planner_json_parse_no_tool():
    from planner import Planner
    p = Planner()
    fake_json = '{"tool": null, "action": null, "parameters": {}, "response": "Python is a programming language."}'
    result = p._parse_json_response(fake_json, "what is python")
    assert result['requires_tool'] == False
    assert result['tool_type'] is None
    assert 'Python' in result['response']
    return True

def test_planner_json_parse_markdown_fenced():
    from planner import Planner
    p = Planner()
    # Some LLMs wrap JSON in markdown code fences
    fenced = '```json\n{"tool": "terminal", "action": "execute", "parameters": {"command": "ls"}, "response": "Listing files"}\n```'
    result = p._parse_json_response(fenced, "list files")
    assert result['requires_tool'] == True
    assert result['tool_type'] == 'terminal'
    return True

def test_planner_text_fallback():
    from planner import Planner
    p = Planner()
    # Test old-style text format fallback
    text = "TOOL: browser\nACTION: open\nPARAMETERS: {}\nRESPONSE: Opening browser"
    result = p._parse_text_fallback(text, "open browser")
    assert result['requires_tool'] == True
    assert result['tool_type'] == 'browser'
    return True

test("Planner imports", test_planner_import)
test("Planner config (model, backend)", test_planner_config)
test("Groq SDK installed", test_groq_sdk)
test("Planner initialization", test_planner_init)
test("JSON parse (tool response)", test_planner_json_parse)
test("JSON parse (no-tool response)", test_planner_json_parse_no_tool)
test("JSON parse (markdown-fenced)", test_planner_json_parse_markdown_fenced)
test("Text fallback parser", test_planner_text_fallback)


# ── Phase 2: Tools ───────────────────────────────────────────────────────────
print("\n🔧 Phase 2: New Tools")

def test_automation_tool_import():
    from tools.automation_tool import AutomationTool
    return True

def test_automation_tool_init():
    from tools.automation_tool import AutomationTool
    t = AutomationTool()
    assert hasattr(t, 'execute'), "Missing execute method"
    assert hasattr(t, '_available'), "Missing _available flag"
    return True

def test_code_tool_import():
    from tools.code_tool import CodeTool
    return True

def test_code_tool_read():
    from tools.code_tool import CodeTool
    t = CodeTool()
    result = t.execute({'action': 'read', 'path': os.path.abspath(__file__)})
    assert 'JARVIS BRAIN UPGRADE' in result, "Should read this test file"
    return True

test("AutomationTool imports", test_automation_tool_import)
test("AutomationTool init", test_automation_tool_init)
test("CodeTool imports", test_code_tool_import)
test("CodeTool read (self)", test_code_tool_read)


# ── Phase 3: Router ──────────────────────────────────────────────────────────
print("\n🔀 Phase 3: Router (new patterns)")

def test_router_import():
    from router import Router
    return True

def test_router_code_patterns():
    from router import Router
    r = Router()
    assert 'code' in r.command_patterns, "Missing 'code' pattern category"
    assert 'automation' in r.command_patterns, "Missing 'automation' pattern category"
    return True

def test_router_screenshot():
    from router import Router
    r = Router()
    result = r.route("take a screenshot")
    assert result['is_command'] == True, f"Expected command, got: {result}"
    assert result['command_type'] == 'automation'
    assert result['action'] == 'screenshot'
    return True

def test_router_click():
    from router import Router
    r = Router()
    result = r.route("click at 500 300")
    assert result['is_command'] == True
    assert result['command_type'] == 'automation'
    assert result['action'] == 'click'
    assert result['parameters']['x'] == 500
    assert result['parameters']['y'] == 300
    return True

def test_router_read_code():
    from router import Router
    r = Router()
    result = r.route("read code from planner.py")
    assert result['is_command'] == True
    assert result['command_type'] == 'code'
    assert result['action'] == 'read'
    return True

def test_router_vscode():
    from router import Router
    r = Router()
    result = r.route("open main.py in vscode")
    assert result['is_command'] == True
    assert result['command_type'] == 'code'
    assert result['action'] == 'open_vscode'
    return True

def test_router_existing_commands():
    from router import Router
    r = Router()
    # These should still work as before
    result = r.route("open youtube")
    assert result['is_command'] == True
    assert result['command_type'] == 'browser'
    
    result = r.route("list files")
    assert result['is_command'] == True
    assert result['command_type'] == 'file'
    
    result = r.route("git status")
    assert result['is_command'] == True
    assert result['command_type'] == 'git'
    return True

def test_router_scroll():
    from router import Router
    r = Router()
    result = r.route("scroll down 10")
    assert result['is_command'] == True
    assert result['command_type'] == 'automation'
    assert result['action'] == 'scroll'
    return True

def test_router_hotkey():
    from router import Router
    r = Router()
    result = r.route("hotkey ctrl+c")
    assert result['is_command'] == True
    assert result['command_type'] == 'automation'
    assert result['action'] == 'hotkey'
    return True

def test_router_press_key():
    from router import Router
    r = Router()
    result = r.route("press enter")
    assert result['is_command'] == True
    assert result['command_type'] == 'automation'
    assert result['action'] == 'press_key'
    return True

test("Router imports", test_router_import)
test("Router has code+automation patterns", test_router_code_patterns)
test("Route: 'take a screenshot'", test_router_screenshot)
test("Route: 'click at 500 300'", test_router_click)
test("Route: 'read code from planner.py'", test_router_read_code)
test("Route: 'open main.py in vscode'", test_router_vscode)
test("Route: existing commands still work", test_router_existing_commands)
test("Route: 'scroll down 10'", test_router_scroll)
test("Route: 'hotkey ctrl+c'", test_router_hotkey)
test("Route: 'press enter'", test_router_press_key)


# ── Phase 4: Memory ──────────────────────────────────────────────────────────
print("\n💾 Phase 4: Memory (upgraded)")

def test_memory_import():
    from memory import Memory, _MAX_INTERACTIONS
    assert _MAX_INTERACTIONS == 500, f"Expected 500, got {_MAX_INTERACTIONS}"
    return True

def test_memory_context():
    from memory import Memory
    m = Memory()
    # Store 15 interactions
    for i in range(15):
        m.store_interaction(f"goal_{i}", f"result_{i}")
    
    ctx = m.get_context()
    assert 'recent_interactions' in ctx
    assert 'older_summary' in ctx
    assert len(ctx['recent_interactions']) == 10, f"Expected 10 recent, got {len(ctx['recent_interactions'])}"
    assert ctx['older_summary'] != "", "Should have older summary with 15 interactions"
    
    # Clean up
    m.clear()
    return True

def test_memory_summarize():
    from memory import Memory
    m = Memory()
    # Store 25 interactions to trigger summarization
    for i in range(25):
        m.store_interaction(f"test_goal_{i}", f"test_result_{i}")
    
    summary = m._summarize_old_interactions()
    assert "older interactions" in summary
    assert "test_goal_" in summary
    
    # Clean up
    m.clear()
    return True

test("Memory import + max=500", test_memory_import)
test("Memory context (10 recent + summary)", test_memory_context)
test("Memory summarization", test_memory_summarize)


# ── Phase 5: Orchestrator ────────────────────────────────────────────────────
print("\n🧠 Phase 5: Orchestrator (integration)")

def test_orchestrator_import():
    # Temporarily enable logging for orchestrator init
    from orchestrator import Orchestrator
    return True

def test_orchestrator_tools():
    from orchestrator import Orchestrator
    o = Orchestrator()
    assert 'code' in o.tools, "Missing 'code' tool"
    assert 'automation' in o.tools, "Missing 'automation' tool"
    assert 'terminal' in o.tools, "Missing 'terminal' tool"
    assert 'browser' in o.tools, "Missing 'browser' tool"
    assert 'search' in o.tools, "Missing 'search' tool"
    assert 'linkedin' in o.tools, "Missing 'linkedin' tool"
    assert 'git' in o.tools, "Missing 'git' tool"
    assert 'file' in o.tools, "Missing 'file' tool"
    assert len(o.tools) == 8, f"Expected 8 tools, got {len(o.tools)}"
    return True

test("Orchestrator imports", test_orchestrator_import)
test("Orchestrator has 8 tools", test_orchestrator_tools)


# ── Phase 6: Live Groq Test ──────────────────────────────────────────────────
print("\n🌐 Phase 6: Live AI Test")

def test_groq_live():
    from planner import Planner
    p = Planner()
    if not p._groq_available:
        print(f"    {WARN} Groq not available — skipping live test")
        return False
    
    result = p.plan("What is 2+2?")
    assert result['response'], "Should have a response"
    assert result['requires_tool'] == False, "Simple math shouldn't need a tool"
    print(f"    → Groq responded: \"{result['response'][:60]}...\"")
    return True

def test_groq_tool_selection():
    from planner import Planner
    p = Planner()
    if not p._groq_available:
        print(f"    {WARN} Groq not available — skipping")
        return False
    
    result = p.plan("take a screenshot of my desktop")
    print(f"    → Tool: {result.get('tool_type')}, Action: {result.get('action')}")
    print(f"    → Response: \"{result.get('response', '')[:60]}...\"")
    # The AI should pick automation or at least respond intelligently
    return True

test("Groq live: 'What is 2+2?'", test_groq_live)
test("Groq live: tool selection", test_groq_tool_selection)


# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
passed = sum(1 for r in results if r[0] == PASS)
failed = sum(1 for r in results if r[0] == FAIL)
total = len(results)
print(f"  Results: {passed}/{total} passed, {failed} failed")
if failed == 0:
    print(f"  {PASS} ALL TESTS PASSED!")
else:
    print(f"\n  Failed tests:")
    for status, name in results:
        if status == FAIL:
            print(f"    {FAIL} {name}")
print("=" * 60 + "\n")

sys.exit(0 if failed == 0 else 1)
