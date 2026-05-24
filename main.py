#!/usr/bin/env python3
import sys
import os

# Fix encoding for Windows console - must be first
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from orchestrator import Orchestrator

def print_banner():
    print("""╔══════════════════════════════╗
║      JARVIS  ONLINE          ║
║   Personal AI Operator       ║
╚══════════════════════════════╝""")

def run_text_mode(orchestrator):
    print("Text mode. Type your goal. Ctrl+C to exit.\n")
    while True:
        try:
            goal = input("> ").strip()
            if not goal:
                continue
            result = orchestrator.process_goal(goal)
            status = "OK" if result['success'] else "FAIL"
            print(f"[{status}] {result['result']}\n")
        except KeyboardInterrupt:
            print("\n[JARVIS] Offline.")
            break

def run_voice_mode(orchestrator):
    from voice_listener import listen_ptt
    from voice_output import VoiceOutput
    import time
    
    tts = VoiceOutput()
    print("Voice mode. Hold F9 to speak. Ctrl+C to exit.\n")
    while True:
        try:
            goal = listen_ptt(hotkey="F9")
            if not goal or not goal.strip():
                continue
            print(f"[JARVIS] Goal: {goal}")
            result = orchestrator.process_goal(goal)
            status = "OK" if result['success'] else "FAIL"
            print(f"[{status}] {result['result']}\n")
            
            # Add delay before speaking to prevent microphone from picking up TTS
            time.sleep(0.5)
            tts.speak(result['result'])
            # Add delay after speaking before listening again
            time.sleep(0.5)
        except KeyboardInterrupt:
            print("\n[JARVIS] Offline.")
            break

def main():
    print_banner()
    orchestrator = Orchestrator()
    
    if "--voice" in sys.argv:
        run_voice_mode(orchestrator)
    else:
        run_text_mode(orchestrator)

if __name__ == "__main__":
    main()
