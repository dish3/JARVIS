#!/usr/bin/env python3
"""
JARVIS Voice Utilities
Audio DSP statistics calculation and WAV debug recording.
"""

import os
import datetime
import logging
import numpy as np
import soundfile as sf

logger = logging.getLogger('VOICE.UTILS')

def save_debug_wav(audio_data: np.ndarray, sample_rate: int) -> str:
    """
    Saves the recorded audio array into voice_debug/voice_YYYYMMDD_HHMMSS.wav
    
    Args:
        audio_data: Floating-point numpy array of audio samples.
        sample_rate: Recording sample rate (e.g. 16000).
        
    Returns:
        The path where the debug file was saved.
    """
    try:
        os.makedirs("voice_debug", exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join("voice_debug", f"voice_{timestamp}.wav")
        sf.write(filepath, audio_data, sample_rate)
        logger.info(f"[VOICE] Saved debug recording: {filepath}")
        return filepath
    except Exception as e:
        logger.error(f"[VOICE] Failed to save debug WAV: {e}")
        return ""

def calculate_audio_stats(audio_data: np.ndarray, sample_rate: int, silence_threshold: float = 0.003) -> dict:
    """
    Computes and logs DSP telemetry on audio data:
    RMS, Peak, Average, Silence %, Sample count, Duration, Clipping detection.
    
    Args:
        audio_data: Floating-point numpy array.
        sample_rate: Recording sample rate.
        silence_threshold: RMS amplitude threshold for silence.
        
    Returns:
        A dictionary with calculated metrics.
    """
    if len(audio_data) == 0:
        return {
            'samples': 0, 'duration': 0.0, 'rms': 0.0,
            'peak': 0.0, 'average': 0.0, 'silence_pct': 100.0, 'clipping': False
        }
        
    samples = len(audio_data)
    duration = samples / sample_rate
    rms = np.sqrt(np.mean(audio_data ** 2))
    peak = np.max(np.abs(audio_data))
    average = np.mean(np.abs(audio_data))
    clipping = peak >= 0.99
    
    # Calculate silence % in chunks of 4096 samples
    chunk_size = 4096
    num_chunks = samples // chunk_size
    silent_chunks = 0
    for i in range(num_chunks):
        chunk = audio_data[i * chunk_size : (i + 1) * chunk_size]
        chunk_rms = np.sqrt(np.mean(chunk ** 2)) if len(chunk) > 0 else 0
        if chunk_rms < silence_threshold:
            silent_chunks += 1
            
    silence_pct = (silent_chunks / num_chunks) * 100 if num_chunks > 0 else (100.0 if rms < silence_threshold else 0.0)
    
    logger.info(f"[VOICE] Audio Stats:")
    logger.info(f"  - Sample count: {samples}")
    logger.info(f"  - Duration: {duration:.2f}s")
    logger.info(f"  - Audio RMS: {rms:.4f}")
    logger.info(f"  - Peak amplitude: {peak:.4f}")
    logger.info(f"  - Average amplitude: {average:.4f}")
    logger.info(f"  - Silence %: {silence_pct:.1f}%")
    logger.info(f"  - Clipping detected: {clipping}")
    
    if clipping:
        logger.warning("[VOICE] Clipping detected: Input level is too high, audio may be distorted.")
    if rms < 0.001:
        logger.warning("[VOICE] Low volume warning: Audio level is extremely quiet. Check microphone levels.")
        
    return {
        'samples': samples,
        'duration': duration,
        'rms': rms,
        'peak': peak,
        'average': average,
        'silence_pct': silence_pct,
        'clipping': clipping
    }
