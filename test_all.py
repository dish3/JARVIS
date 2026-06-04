#!/usr/bin/env python3
"""
Full system test — all non-LinkedIn cases.
LinkedIn image post tested separately (requires browser).
"""
import sys, os, time
sys.path.insert(0, '.')
os.environ['PYTHONIOENCODING'] = 'utf-8'

import logging
logging.disable(logging.CRITICAL)  # suppress log noise in test output

from orchestrator import Orchestrator

o = Orchestrator()

PASS = "[PASS]"
FAIL = "[FAIL]"
results = []

def run(label, goal, expect_success=True, expect_in_result=None):
    r = o.process_goal(goal)
    ok = r['success'] == expect_success
    if expect_in_result and ok:
        ok = expect_in_result.lower() in (r['result'] or '').lower()
    status = PASS if ok else FAIL
    results.append((status, label, r['result'][:80] if r['result'] else ''))
    print(f"{status} {label}")
    if not ok:
        print(f"       result: {r['result'][:120]}")

print("\n" + "="*60)
print("JARVIS SYSTEM TEST")
print("="*60 + "\n")

# ── Browser / URL ──────────────────────────────────────────────────────────────
print("--- Browser ---")
run("Open URL (default browser)",      "open github.com",                    expect_in_result="github.com")
run("Open URL with https",             "open https://www.python.org",        expect_in_result="python.org")
run("Visit shorthand",                 "visit google.com",                   expect_in_result="google.com")
run("Open in Chrome",                  "open github.com in chrome",          expect_in_result="chrome")
run("Open in Edge",                    "open stackoverflow.com in edge",     expect_in_result="edge")

# ── Image generation ──────────────────────────────────────────────────────────
print("\n--- Image Generation ---")
run("Generate image",                  "generate image of a blue robot",     expect_in_result="image saved")
run("Draw shorthand",                  "draw a sunset over the ocean",       expect_in_result="image saved")

# ── File operations ───────────────────────────────────────────────────────────
print("\n--- File Operations ---")
run("List files",                      "list files in current directory",    expect_in_result="[dir]")
run("Write file",                      "create file _test_jarvis.txt with content hello from jarvis", expect_in_result="written")
run("Read file",                       "read file _test_jarvis.txt",         expect_in_result="hello from jarvis")

# ── Terminal ──────────────────────────────────────────────────────────────────
print("\n--- Terminal ---")
run("Echo command",                    "echo JARVIS_TEST_OK",                expect_in_result="JARVIS_TEST_OK")
run("Python version",                  "python --version",                   expect_in_result="python")
run("Block dangerous command",         "run rm -rf /",                       expect_success=True, expect_in_result="not allowed")

# ── Git ───────────────────────────────────────────────────────────────────────
print("\n--- Git ---")
run("Git status",                      "git status",                         expect_in_result="stable-backup")
run("Git log",                         "git log last 3",                     expect_in_result="fix")

# ── Memory persistence ────────────────────────────────────────────────────────
print("\n--- Memory ---")
import json, pathlib
mf = pathlib.Path('memory.json')
mem_ok = mf.exists()
status = PASS if mem_ok else FAIL
results.append((status, "memory.json exists on disk", str(mf)))
print(f"{status} memory.json exists on disk")
if mem_ok:
    data = json.loads(mf.read_text(encoding='utf-8'))
    count = len(data.get('interactions', []))
    status2 = PASS if count > 0 else FAIL
    results.append((status2, f"memory has {count} interactions", ""))
    print(f"{status2} memory has {count} interactions")

# ── Ollama health check (Ollama is OFF — should fast-fail) ────────────────────
print("\n--- Ollama health check (Ollama OFF) ---")
start = time.time()
r = o.process_goal("tell me a joke")
elapsed = time.time() - start
ok = elapsed < 15  # must not hang for 120s
status = PASS if ok else FAIL
results.append((status, f"Ollama fast-fail in {elapsed:.1f}s (must be <15s)", r['result'][:60]))
print(f"{status} Ollama fast-fail in {elapsed:.1f}s")
if not ok:
    print(f"       result: {r['result'][:80]}")

# ── Router pattern checks ─────────────────────────────────────────────────────
print("\n--- Router patterns ---")
from router import Router
rtr = Router()

def check_route(label, goal, expected_type, expected_action=None):
    res = rtr.route(goal)
    ok = res['command_type'] == expected_type
    if expected_action and ok:
        ok = res['action'] == expected_action
    status = PASS if ok else FAIL
    results.append((status, label, f"{res['command_type']}/{res['action']}"))
    print(f"{status} {label}  →  {res['command_type']}/{res['action']}")

check_route("browser open",            "open github.com",                    "browser", "open")
check_route("browser in chrome",       "open google.com in chrome",          "browser", "open")
check_route("image generate",          "generate image of a cat",            "browser", "generate_image")
check_route("web search",              "what is machine learning",           "search",  "search")
check_route("file list",               "list files in current directory",    "file",    "list")
check_route("file read",               "read file main.py",                  "file",    "read")
check_route("terminal",                "run echo hello",                     "terminal","execute")
check_route("git status",              "git status",                         "git",     "status")
check_route("git log",                 "git log last 5",                     "git",     "log")
check_route("linkedin post",           "post to linkedin: hello world",      "linkedin","post")
check_route("linkedin post+image",     "post to linkedin: hi | image: E:\\test.png", "linkedin", "post")
check_route("linkedin delete",         "delete my last linkedin post",       "linkedin","delete")
check_route("vscode open",             "open file main.py in vscode",        "vscode",  "open")

# ── Cleanup ───────────────────────────────────────────────────────────────────
try:
    pathlib.Path('_test_jarvis.txt').unlink()
except: pass

# ── Summary ───────────────────────────────────────────────────────────────────
print("\n" + "="*60)
passed = sum(1 for s, _, _ in results if s == PASS)
failed = sum(1 for s, _, _ in results if s == FAIL)
print(f"RESULTS: {passed} passed, {failed} failed out of {len(results)} tests")
if failed:
    print("\nFailed tests:")
    for s, label, detail in results:
        if s == FAIL:
            print(f"  {FAIL} {label}")
            if detail:
                print(f"         {detail}")
print("="*60)
