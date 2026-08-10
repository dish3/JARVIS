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
from voice.vad import VADDetector

def run_whisper_test(filepath: str, transcriber: STTTranscriber, test_name: str, 
                     language: str, temperature: float, beam_size: int, vad_filter: bool):
    print(f"\n  --- {test_name} ---")
    print(f"    Parameters: language={language!r}, temperature={temperature}, beam_size={beam_size}, vad_filter={vad_filter}")
    
    try:
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
    
    # Run VAD Simulation to find speech start/end boundaries and noise floor calibration
    chunk_size = 4096
    detector = VADDetector(sample_rate=sr)
    num_chunks = samples // chunk_size
    
    for i in range(num_chunks):
        chunk = audio_data[i * chunk_size : (i + 1) * chunk_size]
        detector.process_frame(chunk)
        
    # Calibration details
    cal_size = int(0.5 * sr)
    calibration_audio = audio_data[0:cal_size]
    cal_noise_rms = np.sqrt(np.mean(calibration_audio ** 2)) if len(calibration_audio) > 0 else 0.003
    
    # Derived thresholds
    min_threshold = float(os.getenv("VOICE_VAD_MIN_THRESHOLD", "0.003"))
    start_mult = float(os.getenv("VOICE_VAD_START_MULTIPLIER", "3.0"))
    stop_mult = float(os.getenv("VOICE_VAD_STOP_MULTIPLIER", "1.5"))
    derived_start = max(min_threshold, cal_noise_rms * start_mult)
    derived_stop = max(min_threshold / 2.0, cal_noise_rms * stop_mult)
    
    # Speech Segment Metrics
    if detector.speech_start_time is not None:
        start_sample = int(detector.speech_start_time * sr)
        end_sample = int(detector.speech_end_time * sr) if detector.speech_end_time is not None else samples
        speech_audio = audio_data[start_sample:end_sample]
    else:
        speech_audio = audio_data
        
    speech_rms = np.sqrt(np.mean(speech_audio ** 2)) if len(speech_audio) > 0 else 0
    speech_peak = np.max(np.abs(speech_audio)) if len(speech_audio) > 0 else 0
    
    print("WAV Info:")
    print(f"  - Filepath: {filepath}")
    print(f"  - Sample Rate: {sr} Hz")
    print(f"  - Channels: {info.channels}")
    print(f"  - Format: {info.format} ({info.subtype})")
    print(f"  - Duration: {duration:.2f} seconds")
    print(f"  - Overall WAV RMS: {overall_rms:.6f}")
    
    print("\nCalibration & VAD Metrics:")
    print(f"  - Calibration Noise RMS (first 0.5s): {cal_noise_rms:.6f}")
    print(f"  - Speech RMS (active segment): {speech_rms:.6f}")
    print(f"  - Peak RMS (active segment peak): {speech_peak:.6f}")
    print(f"  - Derived Start Threshold: {derived_start:.6f}")
    print(f"  - Derived Stop Threshold: {derived_stop:.6f}")
    print(f"  - Speech Detected: {detector.has_spoken}")
    if detector.has_spoken:
        print(f"    * Speech Start: {detector.speech_start_time:.3f}s")
        print(f"    * Speech End: {detector.speech_end_time:.3f}s" if detector.speech_end_time is not None else "    * Speech End: N/A (reached end)")
    
    # 2. Frame-Level Statistics (25 ms frames)
    frame_size_ms = 25
    frame_size = int(sr * (frame_size_ms / 1000.0))
    num_frames = samples // frame_size
    
    frame_rms = []
    
    for i in range(num_frames):
        frame = audio_data[i * frame_size : (i + 1) * frame_size]
        if len(frame) > 0:
            frame_rms.append(np.sqrt(np.mean(frame ** 2)))
            
    frame_rms = np.array(frame_rms)
    
    min_rms = np.min(frame_rms)
    median_rms = np.median(frame_rms)
    p90_rms = np.percentile(frame_rms, 90)
    max_rms = np.max(frame_rms)
    
    pct_below_003 = np.sum(frame_rms < 0.003) / num_frames * 100
    pct_below_010 = np.sum(frame_rms < 0.010) / num_frames * 100
    pct_below_020 = np.sum(frame_rms < 0.020) / num_frames * 100
    pct_above_026 = np.sum(frame_rms > 0.026) / num_frames * 100
    
    print("\nFrame-Level Distribution:")
    print(f"  - Minimum Frame RMS: {min_rms:.5f}")
    print(f"  - Median Frame RMS: {median_rms:.5f}")
    print(f"  - 90th Percentile Frame RMS: {p90_rms:.5f}")
    print(f"  - Maximum Frame RMS: {max_rms:.5f}")
    print(f"  - % of frames below 0.003: {pct_below_003:.1f}%")
    print(f"  - % of frames below 0.010: {pct_below_010:.1f}%")
    print(f"  - % of frames below 0.020: {pct_below_020:.1f}%")
    print(f"  - % of frames above 0.026: {pct_above_026:.1f}%")
    
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
