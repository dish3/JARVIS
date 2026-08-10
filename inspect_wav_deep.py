#!/usr/bin/env python3
"""
Deep WAV Inspection & VAD Simulator.
Analyzes voice_debug WAV files in detail to diagnose transcription and VAD failure modes.
"""

import os
import sys
import numpy as np
import soundfile as sf
from dotenv import load_dotenv

# Add VirtualAssistant to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from voice.stt import STTTranscriber
from voice.vad import VADDetector

def analyze_audio_deep(filepath: str, transcriber: STTTranscriber):
    if not os.path.exists(filepath):
        print(f"\n[ERROR] File not found: {filepath}")
        return
        
    print("\n" + "=" * 80)
    print(f" DEEP ANALYSIS: {filepath}")
    print("=" * 80)
    
    # --- TASK 3: AUDIO PROPERTIES ---
    info = sf.info(filepath)
    audio_data, sr = sf.read(filepath)
    if len(audio_data.shape) > 1:
        # If stereo, check channels separately
        print(f"Warning: Audio is stereo. Inspecting both channels:")
        ch1 = audio_data[:, 0]
        ch2 = audio_data[:, 1]
        print(f"  Channel 1: RMS={np.sqrt(np.mean(ch1**2)):.4f}, Peak={np.max(np.abs(ch1)):.4f}")
        print(f"  Channel 2: RMS={np.sqrt(np.mean(ch2**2)):.4f}, Peak={np.max(np.abs(ch2)):.4f}")
        # Convert to mono for VAD simulation
        audio_data = audio_data.mean(axis=1)
    
    samples = len(audio_data)
    duration = samples / sr
    overall_rms = np.sqrt(np.mean(audio_data ** 2))
    overall_peak = np.max(np.abs(audio_data))
    
    print("WAV Properties:")
    print(f"  - Sample Rate: {sr} Hz")
    print(f"  - Channels: {info.channels}")
    print(f"  - Duration: {duration:.2f}s")
    print(f"  - Peak Amplitude: {overall_peak:.4f}")
    print(f"  - Overall RMS: {overall_rms:.4f}")
    
    # --- TASK 1: FRAME-LEVEL ANALYSIS ---
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
    
    # Percentages
    pct_003 = np.sum(frame_rms > 0.003) / num_frames * 100
    pct_010 = np.sum(frame_rms > 0.010) / num_frames * 100
    pct_020 = np.sum(frame_rms > 0.020) / num_frames * 100
    pct_026 = np.sum(frame_rms > 0.026) / num_frames * 100
    
    # Estimate noise floor (bottom 10% energy frames)
    sorted_rms = np.sort(frame_rms)
    noise_floor_estimate = np.mean(sorted_rms[:max(1, int(num_frames * 0.10))])
    
    print("\nFrame-Level Distribution (25ms frames):")
    print(f"  - Frame RMS: Mean={np.mean(frame_rms):.4f}, Std={np.std(frame_rms):.4f}, Min={np.min(frame_rms):.4f}, Max={np.max(frame_rms):.4f}")
    print(f"  - Frame Peaks: Mean={np.mean(frame_peaks):.4f}, Std={np.std(frame_peaks):.4f}, Max={np.max(frame_peaks):.4f}")
    print(f"  - Estimated Noise Floor: {noise_floor_estimate:.4f}")
    print(f"  - Frames > 0.003: {pct_003:.1f}%")
    print(f"  - Frames > 0.010: {pct_010:.1f}%")
    print(f"  - Frames > 0.020: {pct_020:.1f}%")
    print(f"  - Frames > 0.026: {pct_026:.1f}%")
    
    # --- TASK 2: VAD SIMULATION ---
    print("\nVAD State Machine Simulation (silence_threshold=0.003):")
    # Simulate VADDetector chunk by chunk (chunk size 4096 frames = 256 ms at 16kHz)
    chunk_size = 4096
    detector = VADDetector(sample_rate=sr, silence_threshold=0.003)
    num_chunks = samples // chunk_size
    
    timeline = []
    auto_stop_idx = -1
    
    print(f"  Timeline of chunk states:")
    print(f"    {'Time (s)':<10} | {'Chunk RMS':<10} | {'State':<15} | {'Silence Count':<15}")
    print(f"    {'-'*58}")
    
    for i in range(num_chunks):
        chunk = audio_data[i * chunk_size : (i + 1) * chunk_size]
        t = (i * chunk_size) / sr
        
        # VAD status
        rms = np.sqrt(np.mean(chunk ** 2)) if len(chunk) > 0 else 0
        should_stop = detector.process_frame(chunk)
        
        state_str = "ACTIVE (speech)" if detector.has_spoken else "INITIAL"
        if rms < detector.silence_threshold:
            state_str += " (silent)"
            
        print(f"    {t:<10.2f} | {rms:<10.4f} | {state_str:<15} | {detector.silence_count:<15}")
        
        if should_stop and auto_stop_idx == -1:
            auto_stop_idx = i
            print(f"    >>> VAD TRIGGERED AUTO-STOP AT {t:.2f}s <<<")
            
    if auto_stop_idx == -1:
        print(f"    >>> VAD NEVER AUTO-STOPPED (reached max duration) <<<")
        
    # --- TASK 4: WHISPER DECODING CONFIGURATIONS ---
    print("\nWhisper STT Configuration Matrix:")
    
    # Configuration 1: Current settings (language default English)
    print("  1. Current settings:")
    res1 = transcriber.transcribe(filepath)
    if res1.get('success'):
        print(f"     Transcript: {res1['text']!r}")
        print(f"     Confidence: {res1['confidence']:.4f} (avg_logprob={res1['avg_logprob']:.4f})")
    else:
        print(f"     Failed: {res1.get('error')}")
        
    # Configuration 2: English, Temperature 0
    print("  2. Language='en', Temperature=0:")
    try:
        # Inject config overrides for transcribe method
        orig_transcribe = transcriber.model.transcribe
        def mock_transcribe(*args, **kwargs):
            kwargs['language'] = 'en'
            kwargs['temperature'] = 0.0
            return orig_transcribe(*args, **kwargs)
            
        transcriber.model.transcribe = mock_transcribe
        res2 = transcriber.transcribe(filepath)
        print(f"     Transcript: {res2.get('text')!r}")
        print(f"     Confidence: {res2.get('confidence'):.4f} (avg_logprob={res2.get('avg_logprob'):.4f})")
        # Restore
        transcriber.model.transcribe = orig_transcribe
    except Exception as e:
        print(f"     Config 2 failed: {e}")
        
    # Configuration 3: Whisper's internal VAD disabled
    print("  3. VAD Disabled:")
    try:
        orig_transcribe = transcriber.model.transcribe
        def mock_transcribe_no_vad(*args, **kwargs):
            kwargs['vad_filter'] = False
            return orig_transcribe(*args, **kwargs)
        transcriber.model.transcribe = mock_transcribe_no_vad
        res3 = transcriber.transcribe(filepath)
        print(f"     Transcript: {res3.get('text')!r}")
        print(f"     Confidence: {res3.get('confidence'):.4f} (avg_logprob={res3.get('avg_logprob'):.4f})")
        transcriber.model.transcribe = orig_transcribe
    except Exception as e:
        print(f"     Config 3 failed: {e}")

    # Configuration 4: Whisper's internal VAD enabled
    print("  4. VAD Enabled (faster-whisper internal VAD):")
    try:
        orig_transcribe = transcriber.model.transcribe
        def mock_transcribe_vad(*args, **kwargs):
            kwargs['vad_filter'] = True
            return orig_transcribe(*args, **kwargs)
        transcriber.model.transcribe = mock_transcribe_vad
        res4 = transcriber.transcribe(filepath)
        print(f"     Transcript: {res4.get('text')!r}")
        print(f"     Confidence: {res4.get('confidence'):.4f} (avg_logprob={res4.get('avg_logprob'):.4f})")
        transcriber.model.transcribe = orig_transcribe
    except Exception as e:
        print(f"     Config 4 failed: {e}")

def main():
    load_dotenv(override=True)
    
    print("Pre-loading STT model...")
    transcriber = STTTranscriber(model_size='tiny')
    
    files = [
        "voice_debug/voice_20260808_230041.wav",
        "voice_debug/voice_20260808_230220.wav"
    ]
    
    for f in files:
        if os.path.exists(f):
            analyze_audio_deep(f, transcriber)
        else:
            print(f"File {f} not found on disk.")

if __name__ == '__main__':
    main()
