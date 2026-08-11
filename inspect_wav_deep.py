#!/usr/bin/env python3
"""
Controlled STT Experiments: A/B Test Matrix for Audio Amplification & Decoding Context.
Runs Whisper transcription on different gain/context modifications of a captured WAV.
"""

import os
import sys
import numpy as np
import soundfile as sf
import math
import tempfile
from dotenv import load_dotenv

# Add VirtualAssistant to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from voice.stt import STTTranscriber

def run_controlled_experiment(audio_data, sr, transcriber, test_label, condition_on_prev=True):
    # Calculate audio metrics
    samples = len(audio_data)
    duration = samples / sr
    rms = np.sqrt(np.mean(audio_data ** 2)) if samples > 0 else 0
    peak = np.max(np.abs(audio_data)) if samples > 0 else 0
    
    # Save to temp WAV file
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        temp_path = f.name
    try:
        sf.write(temp_path, audio_data, sr)
        
        # Transcribe with faster-whisper model
        segments, info = transcriber.model.transcribe(
            temp_path,
            language="en",
            beam_size=5,
            best_of=5,
            word_timestamps=True,
            condition_on_previous_text=condition_on_prev
        )
        
        segment_list = list(segments)
        text = " ".join([s.text for s in segment_list]).strip()
        
        if segment_list:
            avg_lp = sum(s.avg_logprob for s in segment_list) / len(segment_list)
            confidence = math.exp(avg_lp)
            no_speech_prob = sum(s.no_speech_prob for s in segment_list) / len(segment_list)
        else:
            avg_lp = 0.0
            confidence = 0.0
            no_speech_prob = 1.0

        print(f"\n========================================")
        print(f" {test_label}")
        print(f"========================================")
        print(f" RMS: {rms:.6f}")
        print(f" peak: {peak:.6f}")
        print(f" duration: {duration:.2f}s")
        print(f" transcript: {text!r}")
        print(f" confidence: {confidence:.4f}")
        print(f" avg_logprob: {avg_lp:.4f}")
        print(f" no_speech_probability: {no_speech_prob:.4f}")

    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)

def main():
    load_dotenv(override=True)
    
    target_file = "voice_debug/whisper_input_20260811_200029.wav"
    if not os.path.exists(target_file):
        # Find most recent whisper_input WAV file
        debug_dir = "voice_debug"
        if os.path.exists(debug_dir):
            files = sorted([f for f in os.listdir(debug_dir) if f.startswith("whisper_input_") and f.endswith(".wav")])
            if files:
                target_file = os.path.join(debug_dir, files[-1])
                print(f"Specified file not found. Auto-selected latest: {target_file}")
            else:
                print("Error: No whisper_input_*.wav file found in voice_debug/")
                return
        else:
            print("Error: voice_debug/ directory does not exist.")
            return

    print(f"Loading target audio file: {target_file}")
    audio_data, sr = sf.read(target_file)
    if len(audio_data.shape) > 1:
        audio_data = audio_data.mean(axis=1)

    print("Initializing Whisper STT model...")
    transcriber = STTTranscriber(model_size='tiny')

    # TEST A: Original WAV + current faster-whisper configuration
    run_controlled_experiment(audio_data, sr, transcriber, "TEST A: Original Audio")

    # TEST B: Same WAV peak-normalized to 0.9
    peak = np.max(np.abs(audio_data))
    audio_b = (audio_data / peak) * 0.9 if peak > 0 else audio_data
    run_controlled_experiment(audio_b, sr, transcriber, "TEST B: Peak-Normalized (0.9)")

    # TEST C: Same WAV amplified by +6 dB (+6 dB = scale by factor of ~2)
    audio_c = audio_data * (10 ** (6 / 20))
    run_controlled_experiment(audio_c, sr, transcriber, "TEST C: Amplified +6 dB")

    # TEST D: Same WAV amplified by +12 dB (+12 dB = scale by factor of ~4)
    audio_d = audio_data * (10 ** (12 / 20))
    run_controlled_experiment(audio_d, sr, transcriber, "TEST D: Amplified +12 dB")

    # TEST E: Original WAV with condition_on_previous_text=False
    run_controlled_experiment(audio_data, sr, transcriber, "TEST E: Original Audio (condition_on_previous_text=False)", condition_on_prev=False)

if __name__ == '__main__':
    main()
