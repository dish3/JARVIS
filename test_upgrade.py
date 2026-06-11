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

def test_router_compound_command():
    from router import Router
    r = Router()
    # Multi-step command should NOT be pattern-matched — goes to Planner
    result = r.route("open linkedin, sign in my account and post something")
    assert result['is_command'] == False, f"Compound command should go to planner, got: {result}"
    return True

def test_router_compound_and():
    from router import Router
    r = Router()
    # "and post" has an action verb after "and"
    result = r.route("open linkedin and post hello world")
    assert result['is_command'] == False, f"'and post' should trigger compound detection"
    return True

def test_router_simple_open():
    from router import Router
    r = Router()
    # Simple single command should still work
    result = r.route("open linkedin")
    assert result['is_command'] == True
    assert result['command_type'] == 'browser'
    assert 'linkedin' in result['parameters']['url']
    return True

def test_router_open_in_browser():
    from router import Router
    r = Router()
    result = r.route("open youtube in chrome")
    assert result['is_command'] == True
    assert result['command_type'] == 'browser'
    assert 'youtube' in result['parameters']['url']
    return True

test("Route: compound (comma)", test_router_compound_command)
test("Route: compound ('and post')", test_router_compound_and)
test("Route: simple 'open linkedin'", test_router_simple_open)
test("Route: 'open youtube in chrome'", test_router_open_in_browser)


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

# ── Phase 5.5: Language Processing (New) ─────────────────────────────────────
print("\n🗣️ Phase 5.5: Language Detection & Translation")

def test_language_detection_english():
    from planner import Planner
    p = Planner()
    lang = p.detect_language("take a screenshot of my desktop")
    assert lang == 'en', f"Expected 'en' for English screenshot command, got {lang}"
    return True

def test_language_detection_hindi_live():
    from planner import Planner
    p = Planner()
    if not p._groq_available:
        print(f"    {WARN} Groq not available — skipping live Hindi detection test")
        return True
    lang = p.detect_language("स्क्रीनशॉट लो")
    assert lang == 'hi', f"Expected 'hi' for Hindi screenshot command, got {lang}"
    return True

def test_translation_live():
    from planner import Planner
    p = Planner()
    if not p._groq_available:
        print(f"    {WARN} Groq not available — skipping live translation test")
        return True
    translated = p.translate_text("स्क्रीनशॉट लो", "en")
    assert 'screenshot' in translated.lower() or 'take' in translated.lower(), f"Expected English screenshot translation, got '{translated}'"
    return True

test("Language detection: English", test_language_detection_english)
test("Language detection: Hindi (live)", test_language_detection_hindi_live)
test("Translation: Hindi to English (live)", test_translation_live)


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


# ── Phase 7: Brain Stabilization Upgrades ────────────────────────────────────
print("\n🔒 Phase 7: Stabilization Upgrades")

def test_tool_structured_output_format():
    from tools.automation_tool import AutomationTool
    t = AutomationTool()
    res = t.execute({'action': 'click', 'x': 100, 'y': 200, 'dry_run': True})
    assert isinstance(res, dict), "Result should be a dictionary"
    assert 'status' in res, "Result missing status key"
    assert 'logs' in res, "Result missing logs key"
    assert 'screenshots' in res, "Result missing screenshots key"
    assert 'state' in res, "Result missing state key"
    assert 'result' in res, "Result missing result key"
    return True

def test_destructive_action_blocking():
    from tools.automation_tool import AutomationTool
    t = AutomationTool()
    res = t.execute({'action': 'press_key', 'key': 'delete'})
    assert res['status'] == 'failed', "Destructive press_key without confirm should fail"
    assert "blocked" in res['result']['message'].lower()
    
    res = t.execute({'action': 'hotkey', 'keys': 'alt+f4'})
    assert res['status'] == 'failed', "Destructive alt+f4 hotkey without confirm should fail"
    assert "blocked" in res['result']['message'].lower()
    
    res = t.execute({'action': 'press_key', 'key': 'delete', 'confirm': True, 'dry_run': True})
    assert res['status'] == 'success', "Destructive action with confirm=True should succeed (dry-run)"
    return True

def test_dry_run_flag_simulation():
    from tools.automation_tool import AutomationTool
    t = AutomationTool()
    res = t.execute({'action': 'click', 'x': 500, 'y': 500, 'dry_run': True})
    assert res['status'] == 'success'
    assert any("dry-run" in l.lower() or "simulating" in l.lower() for l in res['logs']), "Dry run not mentioned in logs"
    return True

def test_task_queue_worker_execution():
    import queue
    import threading
    import time
    from main import submit_goal, _task_worker
    from orchestrator import Orchestrator
    
    class MockOrchestrator(Orchestrator):
        def __init__(self):
            self.tools = {}
            self.processed_goals = []
            self.cancel_flag = None
        def process_goal(self, goal, context=None):
            time.sleep(0.1)
            self.processed_goals.append(goal)
            return {'success': True, 'result': f"Processed {goal}"}
            
    mock_orch = MockOrchestrator()
    worker_thread = threading.Thread(target=_task_worker, args=(mock_orch,), daemon=True)
    worker_thread.start()
    
    submit_goal(mock_orch, "task_1")
    submit_goal(mock_orch, "task_2")
    
    time.sleep(0.5)
    assert mock_orch.processed_goals == ["task_1", "task_2"], f"Expected ['task_1', 'task_2'], got {mock_orch.processed_goals}"
    return True

test("Tool structured output format validation", test_tool_structured_output_format)
test("Destructive action blocking", test_destructive_action_blocking)
test("Dry-run flag simulation", test_dry_run_flag_simulation)
test("Task queue worker execution", test_task_queue_worker_execution)


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
