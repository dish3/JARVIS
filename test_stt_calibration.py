#!/usr/bin/env python3
"""
STT Confidence Calibration Tool
Runs 10 recording trials to help calibrate VOICE_CONFIDENCE_THRESHOLD.
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Setup logging to console only
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
logger = logging.getLogger('CALIBRATION')

load_dotenv(override=True)

# Force VOICE_DIAGNOSTIC=false to run actual threshold logic
os.environ["VOICE_DIAGNOSTIC"] = "false"

try:
    from voice_listener import listen_ptt, _get_voice_listener
except ImportError as e:
    logger.error(f"Failed to import voice listener: {e}")
    sys.exit(1)

def main():
    print("=" * 60)
    print("        STT CONFIDENCE CALIBRATION TOOL (10 TRIALS)       ")
    print("=" * 60)
    print("This tool will guide you through 10 clear spoken commands.")
    print("For each command, speak clearly and note the confidence and logprob.")
    print("=" * 60)
    
    # Initialize listener
    print("Loading Whisper model...")
    listener = _get_voice_listener()
    if not listener or not listener.model:
        print("[ERROR] Could not initialize Whisper model.")
        sys.exit(1)
    
    current_threshold = float(os.getenv("VOICE_CONFIDENCE_THRESHOLD", "0.4"))
    print(f"Loaded Whisper model successfully. Current threshold: {current_threshold}")
    
    results = []
    
    for i in range(1, 11):
        print(f"\n--- TRIAL {i}/10 ---")
        input("Press Enter when ready, then speak your command...")
        print("Recording... Speak now. (Stop speaking to auto-stop VAD)")
        
        try:
            # We mock/temporarily patch voice_listener logging or hijack transcribe_audio
            # to capture the confidence and avg_lp values.
            # To do this safely, we can patch transcribe_audio output or read log outputs.
            # Even simpler: since transcribe_audio logs to the VOICE_LISTENER logger,
            # we can add a custom log handler or just look at stdout.
            # Let's wrap transcribe_audio dynamically to extract the calculated confidence.
            original_transcribe = listener.transcribe_audio
            captured_metrics = {}
            
            def wrapped_transcribe(audio_path):
                # Run the original
                res = original_transcribe(audio_path)
                # After running, we can re-load config variables and calculate metrics ourselves
                # from model segments to show them in the final summary.
                try:
                    lang_mode = os.getenv("VOICE_LANGUAGE_MODE", "english").lower()
                    whisper_lang = "en" if lang_mode == "english" else None
                    segments, info = listener.model.transcribe(audio_path, language=whisper_lang, beam_size=5, best_of=5)
                    segment_list = list(segments)
                    if segment_list:
                        import math
                        avg_lp = sum(s.avg_logprob for s in segment_list) / len(segment_list)
                        confidence = math.exp(avg_lp)
                    else:
                        avg_lp, confidence = 0.0, 0.0
                    captured_metrics['avg_lp'] = avg_lp
                    captured_metrics['confidence'] = confidence
                    captured_metrics['text'] = " ".join([s.text for s in segment_list])
                except Exception as e:
                    logger.warning(f"Failed to capture secondary metrics: {e}")
                return res

            listener.transcribe_audio = wrapped_transcribe
            
            # Run listen_ptt in auto-VAD mode
            goal = listen_ptt(use_keyboard=False)
            
            # Restore original method
            listener.transcribe_audio = original_transcribe
            
            if 'confidence' in captured_metrics:
                conf = captured_metrics['confidence']
                lp = captured_metrics['avg_lp']
                txt = captured_metrics['text']
                status = "PASSED" if conf >= current_threshold else "REJECTED (below threshold)"
                print(f"-> Text: {txt!r}")
                print(f"-> avg_logprob: {lp:.4f}")
                print(f"-> Confidence score: {conf:.4f} (Status: {status})")
                results.append((i, txt, lp, conf, status))
            else:
                print("-> No speech detected or transcription failed.")
                results.append((i, "None/Failed", 0.0, 0.0, "FAILED"))
                
        except KeyboardInterrupt:
            print("\nCalibration cancelled by user.")
            break
        except Exception as e:
            print(f"[ERROR] Trial failed: {e}")
            
    print("\n" + "=" * 60)
    print("                     CALIBRATION RESULTS                  ")
    print("=" * 60)
    print(f"{'Trial':<6} | {'Status':<10} | {'Logprob':<8} | {'Confidence':<10} | {'Text'}")
    print("-" * 60)
    for r in results:
        idx, txt, lp, conf, status = r
        print(f"{idx:<6} | {status:<10} | {lp:<8.4f} | {conf:<10.4f} | {txt[:30]}")
    print("=" * 60)
    print(f"Current VOICE_CONFIDENCE_THRESHOLD is set to: {current_threshold}")
    print("Based on the confidence scores above, you can adjust the threshold in your .env file.")
    print("=" * 60)

if __name__ == '__main__':
    main()
