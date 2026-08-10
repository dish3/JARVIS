#!/usr/bin/env python3
"""
Deep WAV Inspection, VAD State Machine Simulator, and Whisper Test Matrix.
Runs controlled experiments on saved voice debug recordings.
"""

import os
import sys
import numpy as np
import soundfile as sf
import math
from dotenv import load_dotenv

# Add VirtualAssistant to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from voice.stt import STTTranscriber

def run_whisper_test(filepath: str, transcriber: STTTranscriber, test_name: str, 
                     language: str, temperature: float, beam_size: int, vad_filter: bool):
    print(f"\n  --- {test_name} ---")
    print(f"    Parameters: language={language!r}, temperature={temperature}, beam_size={beam_size}, vad_filter={vad_filter}")
    
    try:
        # Call model.transcribe directly to have full parameter control
        segments, info = transcriber.model.transcribe(
            filepath,
            language=language,
            temperature=temperature,
            beam_size=beam_size,
            vad_filter=vad_filter,
            word_timestamps=True
        )
        
        segment_list = list(segments)
        text = " ".join([s.text for s in segment_list]).strip()
        
        if segment_list:
            avg_lp = sum(s.avg_logprob for s in segment_list) / len(segment_list)
            confidence = math.exp(avg_lp)
        else:
            avg_lp = 0.0
            confidence = 0.0
            
        print(f"    Result:")
        print(f"      - Model: {transcriber.model_size}")
        print(f"      - Language: {language}")
        print(f"      - Temperature: {temperature}")
        print(f"      - Beam Size: {beam_size}")
        print(f"      - VAD Filter: {vad_filter}")
        print(f"      - Duration: {info.duration:.2f}s")
        print(f"      - Segment Count: {len(segment_list)}")
        print(f"      - Transcript: {text!r}")
        print(f"      - Avg Logprob: {avg_lp:.4f}")
        print(f"      - Confidence Score: {confidence:.4f}")
    except Exception as e:
        print(f"    [ERROR] test failed: {e}")

def analyze_audio_deep(filepath: str, transcriber: STTTranscriber):
    if not os.path.exists(filepath):
        print(f"\n[ERROR] File not found: {filepath}")
        return
        
    print("\n" + "=" * 80)
    print(f" DEEP AUDIO ANALYSIS & STT EXPERIMENTS: {filepath}")
    print("=" * 80)
    
    # 1. Read WAV Properties
    info = sf.info(filepath)
    audio_data, sr = sf.read(filepath)
    if len(audio_data.shape) > 1:
        audio_data = audio_data.mean(axis=1)
        
    samples = len(audio_data)
    duration = samples / sr
    overall_rms = np.sqrt(np.mean(audio_data ** 2))
    overall_peak = np.max(np.abs(audio_data))
    
    print("WAV Info:")
    print(f"  - Filepath: {filepath}")
    print(f"  - Sample Rate: {sr} Hz")
    print(f"  - Channels: {info.channels}")
    print(f"  - Format: {info.format} ({info.subtype})")
    print(f"  - Duration: {duration:.2f} seconds")
    print(f"  - Peak Amplitude: {overall_peak:.4f}")
    print(f"  - Overall WAV RMS: {overall_rms:.4f}")
    
    # 2. Frame-Level Statistics (25 ms frames)
    frame_size_ms = 25
    frame_size = int(sr * (frame_size_ms / 1000.0))
    num_frames = samples // frame_size
    
    frame_rms = []
    frame_peaks = []
    
    for i in range(num_frames):
        frame = audio_data[i * frame_size : (i + 1) * frame_size]
        if len(frame) > 0:
            frame_rms.append(np.sqrt(np.mean(frame ** 2)))
            frame_peaks.append(np.max(np.abs(frame)))
            
    frame_rms = np.array(frame_rms)
    frame_peaks = np.array(frame_peaks)
    
    # Frame level metrics
    min_rms = np.min(frame_rms)
    median_rms = np.median(frame_rms)
    p90_rms = np.percentile(frame_rms, 90)
    max_rms = np.max(frame_rms)
    
    # Percentages
    pct_below_003 = np.sum(frame_rms < 0.003) / num_frames * 100
    pct_below_010 = np.sum(frame_rms < 0.010) / num_frames * 100
    pct_below_020 = np.sum(frame_rms < 0.020) / num_frames * 100
    pct_above_026 = np.sum(frame_rms > 0.026) / num_frames * 100
    
    # Estimate Noise Floor from silence regions (bottom 10% energy frames)
    sorted_rms = np.sort(frame_rms)
    noise_floor_estimate = np.mean(sorted_rms[:max(1, int(num_frames * 0.10))])
    
    # Find longest active / silence regions (threshold = 0.003)
    active_mask = frame_rms >= 0.003
    longest_active_frames = 0
    longest_silence_frames = 0
    
    current_active = 0
    current_silence = 0
    
    for act in active_mask:
        if act:
            current_active += 1
            longest_silence_frames = max(longest_silence_frames, current_silence)
            current_silence = 0
        else:
            current_silence += 1
            longest_active_frames = max(longest_active_frames, current_active)
            current_active = 0
            
    longest_active_frames = max(longest_active_frames, current_active)
    longest_silence_frames = max(longest_silence_frames, current_silence)
    
    longest_active_duration = (longest_active_frames * frame_size_ms) / 1000.0
    longest_silence_duration = (longest_silence_frames * frame_size_ms) / 1000.0
    
    print("\nFrame-Level Distribution:")
    print(f"  - Minimum Frame RMS: {min_rms:.5f}")
    print(f"  - Median Frame RMS: {median_rms:.5f}")
    print(f"  - 90th Percentile Frame RMS: {p90_rms:.5f}")
    print(f"  - Maximum Frame RMS: {max_rms:.5f}")
    print(f"  - Estimated Noise Floor: {noise_floor_estimate:.5f}")
    print(f"  - % of frames below 0.003: {pct_below_003:.1f}%")
    print(f"  - % of frames below 0.010: {pct_below_010:.1f}%")
    print(f"  - % of frames below 0.020: {pct_below_020:.1f}%")
    print(f"  - % of frames above 0.026: {pct_above_026:.1f}%")
    print(f"  - Longest Continuous Active Region (RMS >= 0.003): {longest_active_duration:.2f}s")
    print(f"  - Longest Continuous Silence Region (RMS < 0.003): {longest_silence_duration:.2f}s")
    
    # 3. Whisper Test Matrix
    print("\nWhisper STT Experiment Matrix:")
    
    # TEST A
    run_whisper_test(filepath, transcriber, "TEST A", 
                     language="en", temperature=0.0, beam_size=1, vad_filter=False)
                     
    # TEST B
    run_whisper_test(filepath, transcriber, "TEST B", 
                     language="en", temperature=0.0, beam_size=1, vad_filter=True)
                     
    # TEST C
    run_whisper_test(filepath, transcriber, "TEST C", 
                     language="en", temperature=0.2, beam_size=1, vad_filter=False)
                     
    # TEST D
    run_whisper_test(filepath, transcriber, "TEST D", 
                     language="en", temperature=0.0, beam_size=5, vad_filter=False)

def main():
    load_dotenv(override=True)
    
    print("Loading Whisper STT model...")
    transcriber = STTTranscriber(model_size='tiny')
    
    files = [
        "voice_debug/voice_20260808_230041.wav",
        "voice_debug/voice_20260808_230220.wav"
    ]
    
    for f in files:
        analyze_audio_deep(f, transcriber)

if __name__ == '__main__':
    main()
