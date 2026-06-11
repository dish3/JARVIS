#!/usr/bin/env python3
"""
test_jarvis.py
Comprehensive end-to-end test runner for JARVIS.
Uses only stdlib + existing project modules. No external test framework imports.
Prints clear PASS/FAIL for each test case and a summary at the end.
"""

import os
import sys
import tempfile
import webbrowser
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ensure we can import modules from this directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from router import Router
from tools.file_tool import FileTool
from tools.search_tool import SearchTool
from tools.browser_tool import BrowserTool
from tools.linkedin_tool import LinkedInTool
from memory import Memory
from planner import Planner
from orchestrator import Orchestrator

# Counters
total_tests = 0
passed_tests = 0


def run_test(name, func, is_net=False, is_slow=False):
    """Helper to run a test function, catch exceptions, and print results."""
    global total_tests, passed_tests
    total_tests += 1
    
    prefix = ""
    if is_slow:
        prefix += "[SLOW] "
    if is_net:
        prefix += "[NET] "
        
    try:
        success, message = func()
        if success:
            passed_tests += 1
            print(f"[PASS] {prefix}{name}")
        else:
            print(f"[FAIL] {prefix}{name}: {message}")
    except Exception as e:
        print(f"[FAIL] {prefix}{name}: Unhandled exception: {str(e)}")


# ── 1. ROUTER TESTS ────────────────────────────────────────────────────────────

def test_router_list_files():
    router = Router()
    res = router.route("list files in current directory")
    if not res.get("is_command"):
        return False, "Not detected as command"
    if "file" not in str(res.get("command_type")):
        return False, f"Expected file command, got: {res.get('command_type')}"
    if res.get("action") != "list":
        return False, f"Expected action 'list', got: {res.get('action')}"
    return True, ""

def test_router_read_file():
    router = Router()
    res = router.route("read file planner.py")
    if not res.get("is_command"):
        return False, "Not detected as command"
    if "file" not in str(res.get("command_type")):
        return False, f"Expected file command, got: {res.get('command_type')}"
    if res.get("action") != "read":
        return False, f"Expected action 'read', got: {res.get('action')}"
    return True, ""

def test_router_open_youtube():
    router = Router()
    res = router.route("open youtube")
    if not res.get("is_command"):
        return False, "Not detected as command"
    if res.get("command_type") != "browser":
        return False, f"Expected browser command, got: {res.get('command_type')}"
    if res.get("action") != "open":
        return False, f"Expected action 'open', got: {res.get('action')}"
    return True, ""

def test_router_open_chrome():
    router = Router()
    res = router.route("open github in chrome")
    if not res.get("is_command"):
        return False, "Not detected as command"
    if res.get("command_type") != "browser":
        return False, f"Expected browser command, got: {res.get('command_type')}"
    params = res.get("parameters", {})
    if params.get("browser") != "chrome":
        return False, f"Expected browser parameter 'chrome', got: {params.get('browser')}"
    return True, ""

def test_router_search_news():
    router = Router()
    res = router.route("search latest AI news")
    if not res.get("is_command"):
        return False, "Not detected as command"
    if res.get("command_type") != "search":
        return False, f"Expected search command, got: {res.get('command_type')}"
    return True, ""

def test_router_look_up_tutorials():
    router = Router()
    res = router.route("look up python tutorials")
    if not res.get("is_command"):
        return False, "Not detected as command"
    if res.get("command_type") != "search":
        return False, f"Expected search command, got: {res.get('command_type')}"
    return True, ""

def test_router_draw_dragon():
    router = Router()
    res = router.route("draw a dragon")
    if not res.get("is_command"):
        return False, "Not detected as command"
    if res.get("command_type") != "browser":
        return False, f"Expected browser command, got: {res.get('command_type')}"
    if res.get("action") != "generate_image":
        return False, f"Expected action 'generate_image', got: {res.get('action')}"
    return True, ""

def test_router_generate_sunset():
    router = Router()
    res = router.route("generate image of a sunset")
    if not res.get("is_command"):
        return False, "Not detected as command"
    if res.get("command_type") != "browser":
        return False, f"Expected browser command, got: {res.get('command_type')}"
    if res.get("action") != "generate_image":
        return False, f"Expected action 'generate_image', got: {res.get('action')}"
    return True, ""

def test_router_post_linkedin_simple():
    router = Router()
    res = router.route("post to linkedin: hello world")
    if not res.get("is_command"):
        return False, "Not detected as command"
    if res.get("command_type") != "linkedin":
        return False, f"Expected linkedin command, got: {res.get('command_type')}"
    return True, ""

def test_router_post_linkedin_image():
    router = Router()
    res = router.route(r"post to linkedin: test | image: E:\test.jpg")
    if not res.get("is_command"):
        return False, "Not detected as command"
    if res.get("command_type") != "linkedin":
        return False, f"Expected linkedin command, got: {res.get('command_type')}"
    params = res.get("parameters", {})
    if not params.get("image_path"):
        return False, f"Expected image_path parameter, got params: {params}"
    return True, ""

def test_router_git_status():
    router = Router()
    res = router.route("git status")
    if not res.get("is_command"):
        return False, "Not detected as command"
    if res.get("command_type") != "git":
        return False, f"Expected git command, got: {res.get('command_type')}"
    return True, ""

def test_router_vscode_open():
    router = Router()
    res = router.route("open file orchestrator.py in vscode")
    if not res.get("is_command"):
        return False, "Not detected as command"
    if res.get("command_type") != "code":
        return False, f"Expected code command, got: {res.get('command_type')}"
    if res.get("action") != "open_vscode":
        return False, f"Expected action 'open_vscode', got: {res.get('action')}"
    return True, ""


# ── 2. FILE TOOL TESTS ──────────────────────────────────────────────────────────

def test_file_tool_list():
    tool = FileTool()
    assistant_dir = str(Path(__file__).parent)
    res = tool.execute({"action": "list", "path": assistant_dir})
    if "planner.py" not in res:
        return False, f"Expected planner.py to be in listing. Directory content: {res}"
    return True, ""

def test_file_tool_read():
    tool = FileTool()
    planner_path = str(Path(__file__).parent / "planner.py")
    res = tool.execute({"action": "read", "path": planner_path})
    if "def plan" not in res:
        return False, f"Expected file content containing 'def plan', got: {res[:200]}"
    return True, ""

def test_file_tool_write_read_delete():
    tool = FileTool()
    temp_path = str(Path(__file__).parent / "test_temp.txt")
    try:
        # Write
        res_w = tool.execute({"action": "write", "path": temp_path, "content": "test content 123"})
        if "written successfully" not in res_w:
            return False, f"Write failed: {res_w}"
        
        # Read back
        res_r = tool.execute({"action": "read", "path": temp_path})
        if res_r != "test content 123":
            return False, f"Read back content mismatch, got: {res_r}"
    finally:
        # Clean up
        if os.path.exists(temp_path):
            os.unlink(temp_path)
            
    return True, ""


# ── 3. SEARCH TOOL TEST ─────────────────────────────────────────────────────────

def test_search_tool():
    tool = SearchTool()
    res = tool.search("python programming")
    if not res:
        return False, "Search returned empty string"
    if "http" not in res.lower():
        return False, f"Expected search results to contain at least one URL (http/https), got: {res}"
    return True, ""


# ── 4. BROWSER TOOL TEST ────────────────────────────────────────────────────────

def test_browser_tool_generate_image():
    tool = BrowserTool()
    res = tool.generate_image("a simple red circle")
    if "Image saved: " not in res:
        return False, f"Unexpected return string: {res}"
    
    # Parse path and check on disk
    path_str = res.replace("Image saved: ", "").strip()
    path = Path(path_str)
    
    if not path.exists():
        return False, f"File does not exist on disk: {path_str}"
        
    # Clean up file
    try:
        path.unlink()
    except:
        pass
        
    return True, ""

@patch('webbrowser.open')
def test_browser_tool_open_url(mock_web_open):
    tool = BrowserTool()
    res = tool.open_url("https://example.com")
    mock_web_open.assert_called_once_with("https://example.com")
    if "example.com" not in res:
        return False, f"Expected output containing 'example.com', got: {res}"
    return True, ""


# ── 5. MEMORY TEST ─────────────────────────────────────────────────────────────

def test_memory():
    temp_mem = tempfile.mktemp(suffix='.json')
    try:
        # Use temp memory file
        with patch('memory._MEMORY_FILE', Path(temp_mem)):
            mem = Memory()
            mem.store_interaction("test goal", "test result")
            ctx = mem.get_context()
            ctx_str = str(ctx)
            if not ctx_str:
                return False, "Context string is empty"
            if "test goal" not in ctx_str or "test result" not in ctx_str:
                return False, f"Context did not contain stored interaction: {ctx_str}"
    finally:
        # Cleanup
        for path in [temp_mem, temp_mem + '.tmp', temp_mem + '.bak']:
            try:
                os.unlink(path)
            except:
                pass
    return True, ""


# ── 6. OLLAMA HEALTH TEST ──────────────────────────────────────────────────────

def test_ollama_health():
    planner = Planner()
    # Fast non-blocking health check
    is_ok = planner._is_ollama_available()
    if not is_ok:
        return False, "Ollama is not running (Fast check failed)"
    return True, ""


# ── 7. ORCHESTRATOR INTEGRATION TEST ───────────────────────────────────────────

def test_orchestrator_web_search():
    temp_mem = tempfile.mktemp(suffix='.json')
    try:
        with patch('memory._MEMORY_FILE', Path(temp_mem)):
            orchestrator = Orchestrator()
            res = orchestrator.process_goal("what is 2 + 2")
            if not res.get("success"):
                return False, f"Goal failed: {res.get('result')}"
            if not res.get("result"):
                return False, "Result is empty"
    finally:
        try: os.unlink(temp_mem)
        except: pass
    return True, ""

def test_orchestrator_file_list():
    temp_mem = tempfile.mktemp(suffix='.json')
    try:
        with patch('memory._MEMORY_FILE', Path(temp_mem)):
            orchestrator = Orchestrator()
            # Set FileTool base directory to this assistant dir
            orchestrator.file_tool.base_path = str(Path(__file__).parent)
            
            res = orchestrator.process_goal("list files in current directory")
            if not res.get("success"):
                return False, f"Goal failed: {res.get('result')}"
            
            result_str = str(res.get("result", ""))
            # Accept planner.py (if cwd is VirtualAssistant) or VirtualAssistant/package.json (if cwd is root)
            if not any(x in result_str for x in ["planner.py", "VirtualAssistant", "package.json"]):
                return False, f"Expected result to list project files, got: {result_str}"
    finally:
        try: os.unlink(temp_mem)
        except: pass
    return True, ""


# ── 8. LINKEDIN STATE CONSTANTS TEST ───────────────────────────────────────────

def test_linkedin_constants():
    # Verify constants exist
    for attr in ["STATE_COMPOSER", "STATE_IMAGE_PREVIEW", "STATE_TRANSITIONING", "STATE_POST_READY", "STATE_UNKNOWN"]:
        if not hasattr(LinkedInTool, attr):
            return False, f"LinkedInTool missing constant: {attr}"
            
    # Verify detect_linkedin_post_state is callable
    tool = LinkedInTool()
    if not hasattr(tool, "detect_linkedin_post_state") or not callable(getattr(tool, "detect_linkedin_post_state")):
        return False, "detect_linkedin_post_state is missing or not callable"
        
    return True, ""


# ── 9. SLOW OLLAMA PLANNING TEST ───────────────────────────────────────────────

def test_ollama_planning_slow():
    planner = Planner()
    # Attempt a full plan, unmocked
    res = planner.plan("tell me a joke")
    if "Ollama is not running" in res.get("response", "") or "Ollama health check failed" in res.get("reasoning", ""):
        return False, "Ollama is offline (returned fallback response)"
    if not res.get("response"):
        return False, "Planner returned empty response"
    return True, ""


# ── MAIN RUNNER ────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("            JARVIS END-TO-END TEST SUITE")
    print("=" * 60)
    
    # ── Group 1: Router Tests
    run_test("Router: list files", test_router_list_files)
    run_test("Router: read file", test_router_read_file)
    run_test("Router: open youtube", test_router_open_youtube)
    run_test("Router: open github in chrome", test_router_open_chrome)
    run_test("Router: search latest AI news", test_router_search_news)
    run_test("Router: look up python tutorials", test_router_look_up_tutorials)
    run_test("Router: draw a dragon", test_router_draw_dragon)
    run_test("Router: generate sunset image", test_router_generate_sunset)
    run_test("Router: post to linkedin simple", test_router_post_linkedin_simple)
    run_test("Router: post to linkedin with image", test_router_post_linkedin_image)
    run_test("Router: git status", test_router_git_status)
    run_test("Router: open file in vscode", test_router_vscode_open)
    
    # ── Group 2: File Tool Tests
    run_test("File Tool: list files", test_file_tool_list)
    run_test("File Tool: read file", test_file_tool_read)
    run_test("File Tool: write, read & delete file", test_file_tool_write_read_delete)
    
    # ── Group 3: Search Tool Test
    run_test("Search Tool: query", test_search_tool, is_net=True)
    
    # ── Group 4: Browser Tool Test
    run_test("Browser Tool: generate image", test_browser_tool_generate_image, is_net=True)
    run_test("Browser Tool: open url", test_browser_tool_open_url)
    
    # ── Group 5: Memory Test
    run_test("Memory: store and load context", test_memory)
    
    # ── Group 6: Ollama Health Test
    run_test("Ollama: fast health check", test_ollama_health)
    
    # ── Group 7: Orchestrator Integration Test
    run_test("Orchestrator: web search goal", test_orchestrator_web_search, is_net=True)
    run_test("Orchestrator: file list goal", test_orchestrator_file_list)
    
    # ── Group 8: LinkedIn Constants Test
    run_test("LinkedIn: state constants and method presence", test_linkedin_constants)
    
    # ── Group 9: Slow Ollama Planning Test (separate section at the end)
    print("\n" + "=" * 60)
    print("            SLOW TESTS SECTION (Ollama Planning)")
    print("=" * 60)
    run_test("Ollama: full planning query", test_ollama_planning_slow, is_slow=True)
    
    print("\n" + "=" * 60)
    print("            TEST RUN SUMMARY")
    print("=" * 60)
    print(f"{passed_tests}/{total_tests} tests passed")
    print("=" * 60)
    
    sys.exit(0 if passed_tests == total_tests else 1)


if __name__ == "__main__":
    main()
