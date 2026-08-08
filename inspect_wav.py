#!/usr/bin/env python3
"""
WAV Inspection & Whisper STT Diagnostics Tool.
Analyzes the saved voice debug recordings to determine:
1. Audio format, RMS, peak amplitude, and clipping.
2. Whisper segments, transcripts, and confidence levels.
3. Recommendations for VAD and noise gate tuning.
"""

import os
import sys
import numpy as np
import soundfile as sf
from dotenv import load_dotenv

# Add VirtualAssistant to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from voice.utils import calculate_audio_stats
from voice.stt import STTTranscriber

def inspect_wav_file(filepath: str, transcriber: STTTranscriber):
    if not os.path.exists(filepath):
        print(f"\n[ERROR] File not found: {filepath}")
        return
        
    print("\n" + "=" * 60)
    print(f" FILE: {filepath}")
    print("=" * 60)
    
    # 1. Read file and properties
    info = sf.info(filepath)
    print(f"Properties:")
    print(f"  - Sample Rate: {info.samplerate} Hz")
    print(f"  - Channels: {info.channels}")
    print(f"  - Format: {info.format} ({info.subtype})")
    print(f"  - Duration: {info.duration:.2f}s")
    print(f"  - Frames: {info.frames}")
    
    audio_data, sr = sf.read(filepath)
    # Convert to mono if stereo
    if len(audio_data.shape) > 1:
        audio_data = audio_data.mean(axis=1)
        
    # 2. Audio Stats
    print("\nDSP Audio Telemetry:")
    stats = calculate_audio_stats(audio_data, sr)
    
    # 3. Whisper STT
    print("\nWhisper STT Transcription:")
    res = transcriber.transcribe(filepath)
    if res.get('success'):
        print(f"  - Detected Language: {res['detected_lang']} (prob={res['lang_prob']:.4f})")
        print(f"  - Raw Transcript: {res['text']!r}")
        print(f"  - Confidence: {res['confidence']:.4f} (avg_logprob={res['avg_logprob']:.4f})")
        print(f"  - Words & Confidences:")
        for w, p in res.get('words', []):
            print(f"    * '{w}': {p:.4f}")
    else:
        print(f"  - Transcription failed: {res.get('error')}")
        
    # 4. Recommendations
    print("\nRecommendations:")
    rms = stats['rms']
    peak = stats['peak']
    if rms < 0.003:
        print("  [VAD] Audio is extremely quiet. Check physical mic gain or select device 1.")
    elif 0.010 <= rms <= 0.025:
        suggested_vad = max(0.015, rms * 1.5)
        print(f"  [VAD] Background noise floor is high (RMS: {rms:.4f}).")
        print(f"        VAD silence threshold (default 0.003) is likely treating noise as active speech.")
        print(f"        RECOMMENDED: Add `VOICE_VAD_THRESHOLD={suggested_vad:.3f}` to your .env file.")
    else:
        print("  [VAD] Audio levels appear normal.")
        
    if stats['clipping']:
        print("  [CLIPPING] Input signal is clipping. Reduce microphone gain.")

def main():
    load_dotenv(override=True)
    
    # Initialize Whisper model
    print("Initializing Whisper model...")
    transcriber = STTTranscriber(model_size='tiny')
    
    files_to_inspect = [
        "voice_debug/voice_20260808_230041.wav",
        "voice_debug/voice_20260808_230220.wav"
    ]
    
    for f in files_to_inspect:
        inspect_wav_file(f, transcriber)

if __name__ == '__main__':
    main()
