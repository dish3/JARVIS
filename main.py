#!/usr/bin/env python3
import sys
import os
import threading
import queue
import time

# Fix encoding for Windows console - must be first
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from orchestrator import Orchestrator

# ── Task runner ────────────────────────────────────────────────────────────────

# Shared result queue — background thread puts results here, main loop reads them
_result_queue = queue.Queue()

# Flag so voice mode knows a task is already running
_task_running = threading.Event()

# Flag to stop voice listening loop
_voice_stop = threading.Event()


def _run_task(orchestrator: Orchestrator, goal: str) -> None:
    """
    Execute process_goal() in a background thread.
    Puts status strings and the final result dict into _result_queue.
    Never raises — all exceptions are caught and queued as error results.
    """
    _task_running.set()
    _result_queue.put(('[TASK STARTED]', goal))

    try:
        _result_queue.put(('[TASK RUNNING]', goal))
        result = orchestrator.process_goal(goal)
        _result_queue.put(('[TASK COMPLETE]', result))
    except Exception as e:
        _result_queue.put(('[TASK COMPLETE]', {
            'success': False,
            'result': f"Error: {str(e)}",
            'tool_used': None,
        }))
    finally:
        _task_running.clear()


def submit_goal(orchestrator: Orchestrator, goal: str) -> None:
    """
    Spawn a daemon thread to run process_goal().
    Returns immediately — UI stays responsive.
    """
    t = threading.Thread(target=_run_task, args=(orchestrator, goal), daemon=True)
    t.start()


# ── Output helpers ─────────────────────────────────────────────────────────────

def _emit(tag: str, payload) -> None:
    """
    Print a structured status line to stdout.
    Electron main.js reads these lines and forwards them to the renderer.
    Format is kept simple so renderer-v2.js can parse with startsWith().
    """
    if tag == '[TASK STARTED]':
        print(f'[TASK STARTED] {payload}', flush=True)
    elif tag == '[TASK RUNNING]':
        print(f'[TASK RUNNING] {payload}', flush=True)
    elif tag == '[TASK COMPLETE]':
        result = payload
        status = 'OK' if result.get('success') else 'FAIL'
        text = result.get('result', '').replace('\n', ' ')
        tool = result.get('tool_used') or 'none'
        print(f'[TASK COMPLETE] [{status}] [{tool}] {text}', flush=True)
    elif tag == '[VOICE]':
        print(f'[VOICE] {payload}', flush=True)
    elif tag == '[TRANSCRIPTION]':
        print(f'[TRANSCRIPTION] {payload}', flush=True)
    elif tag == '[ROUTER]':
        print(f'[ROUTER] {payload}', flush=True)


def _drain_queue(tts=None) -> None:
    """Drain all pending items from _result_queue without blocking."""
    while not _result_queue.empty():
        try:
            tag, payload = _result_queue.get_nowait()
            _emit(tag, payload)

            # Speak result in voice mode — only on completion, max 2 sentences
            if tts and tag == '[TASK COMPLETE]':
                result = payload
                text = result.get('result', '')
                if text and result.get('success'):
                    sentences = [s.strip() for s in text.replace('\n', ' ').split('.') if s.strip()]
                    spoken = '. '.join(sentences[:2])
                    if spoken:
                        time.sleep(0.5)
                        tts.speak(spoken)
                        time.sleep(0.5)
        except queue.Empty:
            break


# ── Voice pipeline ─────────────────────────────────────────────────────────────

def _voice_listen_once(orchestrator: Orchestrator, tts=None) -> None:
    """
    Capture microphone → transcribe → log → submit to orchestrator.
    Runs in a background thread so it never blocks stdin reading.
    """
    try:
        from voice_listener import listen_ptt

        _emit('[VOICE]', 'Listening... hold F9 to speak')
        goal = listen_ptt(hotkey='F9')

        if not goal or not goal.strip():
            _emit('[VOICE]', 'No speech detected')
            return

        _emit('[TRANSCRIPTION]', goal)

        # Route log — show what the router will do before submitting
        from router import Router
        route = Router().route(goal)
        cmd_type = route.get('command_type') or 'planner'
        action = route.get('action') or 'reason'
        _emit('[ROUTER]', f'{cmd_type}/{action} → "{goal}"')

        # Submit to background task runner
        submit_goal(orchestrator, goal)

    except Exception as e:
        _emit('[VOICE]', f'Error: {e}')


def _start_voice_thread(orchestrator: Orchestrator, tts=None) -> None:
    """Spawn a single voice listen cycle in a daemon thread."""
    t = threading.Thread(
        target=_voice_listen_once,
        args=(orchestrator, tts),
        daemon=True
    )
    t.start()


# ── Modes ──────────────────────────────────────────────────────────────────────

def print_banner():
    print("""╔══════════════════════════════╗
║      JARVIS  ONLINE          ║
║   Personal AI Operator       ║
╚══════════════════════════════╝""", flush=True)


def run_text_mode(orchestrator: Orchestrator) -> None:
    """
    Text mode — reads goals from stdin line by line.
    Works for both interactive terminal use and Electron pipe.
    """
    print('Text mode. Type your goal. Ctrl+C to exit.\n', flush=True)

    while True:
        try:
            _drain_queue()
            goal = input('> ').strip()
            if not goal:
                continue
            submit_goal(orchestrator, goal)
        except KeyboardInterrupt:
            print('\n[JARVIS] Waiting for running task...')
            _task_running.wait(timeout=5)
            _drain_queue()
            print('[JARVIS] Offline.')
            break
        except EOFError:
            # stdin closed (e.g. Electron killed the process)
            _task_running.wait(timeout=5)
            _drain_queue()
            break


def run_text_server(orchestrator: Orchestrator) -> None:
    """
    Server mode — called by Electron via --text-server flag.
    Reads newline-delimited goals from stdin.
    Special tokens:
      __VOICE__       → trigger one voice listen cycle
      __STOP_VOICE__  → no-op (voice is already one-shot)
    Emits structured lines to stdout that renderer-v2.js parses.
    """
    import logging
    # In server mode suppress verbose INFO logs — Electron reads stdout only
    logging.getLogger().setLevel(logging.WARNING)
    for name in ['ORCHESTRATOR', 'ROUTER', 'PLANNER', 'MEMORY',
                 'TERMINAL_TOOL', 'FILE_TOOL', 'BROWSER_TOOL',
                 'SEARCH_TOOL', 'LINKEDIN_TOOL', 'GIT_TOOL', 'VOICE_LISTENER']:
        logging.getLogger(name).setLevel(logging.WARNING)

    print('[JARVIS SERVER] Ready', flush=True)

    try:
        from voice_output import VoiceOutput
        tts = VoiceOutput()
    except Exception:
        tts = None

    for raw_line in sys.stdin:
        goal = raw_line.strip()
        if not goal:
            continue

        # Drain any completed results before processing new input
        _drain_queue(tts=tts)

        if goal == '__VOICE__':
            # Trigger one voice listen cycle in background
            _start_voice_thread(orchestrator, tts=tts)
            continue

        if goal == '__STOP_VOICE__':
            # Voice is one-shot per trigger — nothing to stop
            continue

        # Regular text goal — log route before submitting
        from router import Router
        route = Router().route(goal)
        cmd_type = route.get('command_type') or 'planner'
        action = route.get('action') or 'reason'
        _emit('[ROUTER]', f'{cmd_type}/{action} → "{goal}"')

        submit_goal(orchestrator, goal)

        # Give the background thread a moment to emit [TASK STARTED]
        time.sleep(0.05)
        _drain_queue(tts=tts)

    # stdin closed — wait for last task
    _task_running.wait(timeout=10)
    _drain_queue(tts=tts)


def run_voice_mode(orchestrator: Orchestrator) -> None:
    """
    Voice mode — terminal push-to-talk loop.
    Voice listening and task execution run concurrently.
    """
    from voice_listener import listen_ptt
    from voice_output import VoiceOutput

    tts = VoiceOutput()
    print('Voice mode. Hold F9 to speak. Ctrl+C to exit.\n', flush=True)

    while True:
        try:
            _drain_queue(tts=tts)

            _emit('[VOICE]', 'Hold F9 to speak...')
            goal = listen_ptt(hotkey='F9')

            if not goal or not goal.strip():
                continue

            _emit('[TRANSCRIPTION]', goal)

            from router import Router
            route = Router().route(goal)
            cmd_type = route.get('command_type') or 'planner'
            action = route.get('action') or 'reason'
            _emit('[ROUTER]', f'{cmd_type}/{action} → "{goal}"')

            submit_goal(orchestrator, goal)

        except KeyboardInterrupt:
            print('\n[JARVIS] Waiting for running task...')
            _task_running.wait(timeout=5)
            _drain_queue(tts=tts)
            print('[JARVIS] Offline.')
            break


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    print_banner()
    orchestrator = Orchestrator()

    if '--text-server' in sys.argv:
        run_text_server(orchestrator)
    elif '--voice' in sys.argv:
        run_voice_mode(orchestrator)
    else:
        run_text_mode(orchestrator)


if __name__ == '__main__':
    main()
