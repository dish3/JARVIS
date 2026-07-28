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

# Task queue for sequential processing
_task_queue = queue.Queue()

# Flag to request cancellation of current running task
_cancel_flag = threading.Event()

# Flag to stop background queue drainer loop
_drain_stop = threading.Event()


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
    Queue a goal for sequential processing by the background worker.
    """
    _task_queue.put(goal)


def _task_worker(orchestrator: Orchestrator) -> None:
    """
    Sequentially process goals from the task queue.
    """
    while True:
        try:
            goal = _task_queue.get()
            if goal is None:
                break
            _cancel_flag.clear()
            _run_task(orchestrator, goal)
            _task_queue.task_done()
        except Exception as e:
            sys.stderr.write(f"[TASK WORKER ERROR] {e}\n")
            sys.stderr.flush()


def cancel_current_task() -> None:
    """
    Instantly clear the task queue, set cancel flag to abort the active task,
    and log cancellation.
    """
    # Drain the task queue
    while not _task_queue.empty():
        try:
            _task_queue.get_nowait()
            _task_queue.task_done()
        except (queue.Empty, ValueError):
            break
    _cancel_flag.set()
    _result_queue.put(('[ROUTER]', 'Task execution cancelled.'))
    print('[CANCELLED] Task queue cleared and running task cancelled.', flush=True)


def _queue_drainer_thread(tts_enabled: bool = False) -> None:
    """
    Dedicated loop running in background thread to drain the result queue
    and print logs/speak output immediately.
    """
    tts = None
    if tts_enabled:
        import sys
        if sys.platform == 'win32':
            try:
                import ctypes
                ctypes.windll.ole32.CoInitialize(None)
            except Exception as com_err:
                sys.stderr.write(f"[VOICE] CoInitialize failed in drainer: {com_err}\n")
        
        try:
            from voice_output import VoiceOutput
            tts = VoiceOutput()
        except Exception as e:
            sys.stderr.write(f"Warning: Could not initialize voice output in background thread: {e}\n")

    try:
        while not _drain_stop.is_set():
            _drain_queue(tts=tts)
            time.sleep(0.05)
    finally:
        if tts and sys.platform == 'win32':
            try:
                import ctypes
                ctypes.windll.ole32.CoUninitialize()
            except:
                pass


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

            # Speak result in voice mode — speak on completion (success or error), max 2 sentences
            if tts and tag == '[TASK COMPLETE]':
                result = payload
                text = result.get('result', '')
                if text:
                    sentences = [s.strip() for s in text.replace('\n', ' ').split('.') if s.strip()]
                    spoken = '. '.join(sentences[:2])
                    if spoken:
                        time.sleep(0.3)
                        tts.speak(spoken)
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

        _emit('[VOICE]', 'Listening... speak now')
        # Disable keyboard hotkey hooks in server mode to prevent access violation crashes on Windows
        use_keyboard = '--text-server' not in sys.argv
        _voice_stop.clear()
        goal = listen_ptt(hotkey='F9', stop_event=_voice_stop, use_keyboard=use_keyboard)

        if not goal or not goal.strip():
            _emit('[VOICE]', 'No speech detected')
            return

        if goal == '__CANCEL__':
            cancel_current_task()
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
            goal = input('> ').strip()
            if not goal:
                continue
            if goal == '__CANCEL__':
                cancel_current_task()
                continue
            submit_goal(orchestrator, goal)
        except KeyboardInterrupt:
            print('\n[JARVIS] Cancelling and exiting...')
            cancel_current_task()
            break
        except EOFError:
            # stdin closed (e.g. Electron killed the process)
            break


def run_text_server(orchestrator: Orchestrator, tts=None) -> None:
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
                 'SEARCH_TOOL', 'LINKEDIN_TOOL', 'GIT_TOOL', 'VOICE_LISTENER', 'AUTOMATION_TOOL']:
        logging.getLogger(name).setLevel(logging.WARNING)

    print('[JARVIS SERVER] Ready', flush=True)

    for raw_line in sys.stdin:
        goal = raw_line.strip()
        if not goal:
            continue

        if goal == '__CANCEL__':
            cancel_current_task()
            continue

        if goal == '__VOICE__':
            # Trigger one voice listen cycle in background
            _start_voice_thread(orchestrator, tts=tts)
            continue

        if goal == '__STOP_VOICE__':
            _voice_stop.set()
            continue

        # Regular text goal — log route before submitting
        from router import Router
        route = Router().route(goal)
        cmd_type = route.get('command_type') or 'planner'
        action = route.get('action') or 'reason'
        _emit('[ROUTER]', f'{cmd_type}/{action} → "{goal}"')

        submit_goal(orchestrator, goal)


def run_voice_mode(orchestrator: Orchestrator, tts=None) -> None:
    """
    Voice mode — terminal push-to-talk loop.
    Voice listening and task execution run concurrently.
    """
    from voice_listener import listen_ptt

    print('Voice mode. Hold F9 to speak. Ctrl+C to exit.\n', flush=True)

    while True:
        try:
            _emit('[VOICE]', 'Hold F9 to speak...')
            goal = listen_ptt(hotkey='F9')

            if not goal or not goal.strip():
                continue

            if goal == '__CANCEL__':
                cancel_current_task()
                continue

            _emit('[TRANSCRIPTION]', goal)

            from router import Router
            route = Router().route(goal)
            cmd_type = route.get('command_type') or 'planner'
            action = route.get('action') or 'reason'
            _emit('[ROUTER]', f'{cmd_type}/{action} → "{goal}"')

            submit_goal(orchestrator, goal)

        except KeyboardInterrupt:
            print('\n[JARVIS] Cancelling and exiting...')
            cancel_current_task()
            break


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    print_banner()
    orchestrator = Orchestrator()

    # Setup cancel flag
    orchestrator.cancel_flag = _cancel_flag

    # Spawn sequential worker thread
    worker_thread = threading.Thread(target=_task_worker, args=(orchestrator,), daemon=True)
    worker_thread.start()

    # Instantiate TTS if in server/voice mode or try to instantiate always
    tts_enabled = '--voice' in sys.argv or '--text-server' in sys.argv

    # Spawn background queue drainer thread
    drainer_thread = threading.Thread(target=_queue_drainer_thread, args=(tts_enabled,), daemon=True)
    drainer_thread.start()

    if '--text-server' in sys.argv:
        run_text_server(orchestrator, tts=None)
    elif '--voice' in sys.argv:
        run_voice_mode(orchestrator, tts=None)
    else:
        run_text_mode(orchestrator)

    # Stop the drainer loop when main exits
    _drain_stop.set()


if __name__ == '__main__':
    main()
