#!/usr/bin/env python3
"""
Raw Microphone Diagnostics Tool.
Records exactly 5 seconds from the configured input device and prints detailed DSP metrics.
Allows analyzing raw_mic_test.wav to evaluate noise floor and signal quality.
"""

import os
import sys
import numpy as np
import sounddevice as sd
import soundfile as sf
from dotenv import load_dotenv

# Add VirtualAssistant to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def calculate_dsp_metrics(audio: np.ndarray, sr: int):
    peak = np.max(np.abs(audio))
    rms = np.sqrt(np.mean(audio ** 2))
    minimum = np.min(audio)
    maximum = np.max(audio)
    mean = np.mean(audio)
    std = np.std(audio)
    
    # Percentages
    near_zero = np.sum(np.abs(audio) < 1e-4) / len(audio) * 100
    above_01 = np.sum(np.abs(audio) > 0.01) / len(audio) * 100
    above_02 = np.sum(np.abs(audio) > 0.02) / len(audio) * 100
    above_05 = np.sum(np.abs(audio) > 0.05) / len(audio) * 100
    above_10 = np.sum(np.abs(audio) > 0.10) / len(audio) * 100
    
    print("\nDSP Signal Telemetry:")
    print(f"  - Peak Amplitude: {peak:.6f}")
    print(f"  - RMS Amplitude: {rms:.6f}")
    print(f"  - Minimum Sample: {minimum:.6f}")
    print(f"  - Maximum Sample: {maximum:.6f}")
    print(f"  - Mean Sample: {mean:.6f}")
    print(f"  - Standard Deviation: {std:.6f}")
    print(f"  - % Samples Near Zero (< 1e-4): {near_zero:.2f}%")
    print(f"  - % Samples Above 0.01: {above_01:.2f}%")
    print(f"  - % Samples Above 0.02: {above_02:.2f}%")
    print(f"  - % Samples Above 0.05: {above_05:.2f}%")
    print(f"  - % Samples Above 0.10: {above_10:.2f}%")
    
    # RMS in 100ms windows
    window_size = int(sr * 0.1) # 100ms
    num_windows = len(audio) // window_size
    print("\nRMS Timeline (100ms Windows):")
    print(f"  {'Time Window':<15} | {'RMS Energy':<12} | {'Visual Peak Indicator'}")
    print(f"  {'-'*55}")
    for w in range(num_windows):
        window_audio = audio[w * window_size : (w + 1) * window_size]
        w_rms = np.sqrt(np.mean(window_audio ** 2)) if len(window_audio) > 0 else 0
        w_time = w * 0.1
        bar = "#" * int(w_rms * 100)
        print(f"  {w_time:.1f}s - {w_time+0.1:.1f}s  | {w_rms:<12.5f} | {bar}")

def record_raw(device_idx: int, duration: float = 5.0, sr: int = 16000):
    print("\n" + "=" * 60)
    print(" RECORDING RAW MIC SIGNAL")
    print("=" * 60)
    
    # Query device info
    try:
        devices = sd.query_devices()
        dev_info = devices[device_idx]
        print(f"Configured Device:")
        print(f"  - Index: {device_idx}")
        print(f"  - Name: {dev_info['name']}")
        print(f"  - Default Sample Rate: {dev_info['default_samplerate']} Hz")
        print(f"  - Max Input Channels: {dev_info['max_input_channels']}")
    except Exception as e:
        print(f"[ERROR] Could not query device {device_idx}: {e}")
        return
        
    channels = 1
    dtype = 'float32'
    print(f"\nRecording Parameters:")
    print(f"  - Channels: {channels}")
    print(f"  - Sample Rate: {sr} Hz")
    print(f"  - Dtype: {dtype}")
    print(f"  - Duration: {duration} seconds")
    
    print("\n*** COUNTDOWN TO TEST ROUTINE ***")
    print("  0-1 seconds: SILENCE")
    print("  1-2 seconds: say loudly \"OPEN CHROME\"")
    print("  2-3 seconds: SILENCE")
    print("  3-4 seconds: say loudly \"TEST TEST TEST\"")
    print("  4-5 seconds: SILENCE")
    input("\nPress Enter to START recording...")
    
    print("\n>>> RECORDING STARTED <<<")
    try:
        recording = sd.rec(int(duration * sr), samplerate=sr, channels=channels, dtype=dtype, device=device_idx)
        sd.wait() # Wait until finished
        print(">>> RECORDING FINISHED <<<")
    except Exception as e:
        print(f"[ERROR] Recording failed: {e}")
        return
        
    audio = recording.flatten()
    
    # Save raw WAV
    save_dir = "voice_debug"
    os.makedirs(save_dir, exist_ok=True)
    filepath = os.path.join(save_dir, "raw_mic_test.wav")
    sf.write(filepath, audio, sr, subtype='PCM_16')
    print(f"\nSaved raw file to: {filepath}")
    
    calculate_dsp_metrics(audio, sr)

def analyze_raw_wav(filepath: str):
    if not os.path.exists(filepath):
        print(f"\n[ERROR] File not found: {filepath}")
        return
        
    print("\n" + "=" * 60)
    print(f" ANALYZING EXISTING FILE: {filepath}")
    print("=" * 60)
    
    info = sf.info(filepath)
    audio, sr = sf.read(filepath)
    if len(audio.shape) > 1:
        audio = audio.mean(axis=1)
        
    print(f"WAV Properties:")
    print(f"  - Sample Rate: {sr} Hz")
    print(f"  - Channels: {info.channels}")
    print(f"  - Duration: {info.duration:.2f}s")
    print(f"  - Format: {info.format} ({info.subtype})")
    
    calculate_dsp_metrics(audio, sr)

def main():
    load_dotenv(override=True)
    
    # Check if analysis only requested
    if len(sys.argv) > 1 and sys.argv[1] == '--analyze':
        analyze_raw_wav("voice_debug/raw_mic_test.wav")
        return
        
    # Get configured device from env
    try:
        device_idx = int(os.getenv("VOICE_INPUT_DEVICE", "1"))
    except ValueError:
        device_idx = 1
        
    record_raw(device_idx)

if __name__ == '__main__':
    main()
