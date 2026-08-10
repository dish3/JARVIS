#!/usr/bin/env python3
"""
JARVIS Voice Activity Detection (VAD)
Manages dynamic silence limits, hysteresis thresholding, and auto-stop boundaries.
"""

import numpy as np
import logging
import os

logger = logging.getLogger('VOICE.VAD')

class VADDetector:
    """
    Decoupled state machine for monitoring silence thresholds and VAD limits.
    Implements dynamic noise floor calibration and start/stop hysteresis.
    """
    def __init__(self, sample_rate: int, silence_threshold: float = 0.003, 
                 initial_silence_limit: float = 4.0, active_silence_limit: float = 1.5,
                 max_duration: float = 15.0, chunk_size: int = 4096):
        """
        Initialize VAD Detector parameters.
        Loads environment overrides if available.
        """
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.chunk_duration = chunk_size / sample_rate
        
        # Load environment configurations with defaults
        self.min_threshold = float(os.getenv("VOICE_VAD_MIN_THRESHOLD", "0.003"))
        self.start_multiplier = float(os.getenv("VOICE_VAD_START_MULTIPLIER", "3.0"))
        self.stop_multiplier = float(os.getenv("VOICE_VAD_STOP_MULTIPLIER", "1.5"))
        
        self.min_speech_ms = float(os.getenv("VOICE_VAD_MIN_SPEECH_MS", "250"))
        self.silence_ms = float(os.getenv("VOICE_VAD_SILENCE_MS", "700"))
        self.max_recording_seconds = float(os.getenv("VOICE_VAD_MAX_RECORDING_SECONDS", "10"))
        self.preroll_ms = float(os.getenv("VOICE_VAD_PREROLL_MS", "200"))
        
        # Derived values
        self.min_speech_chunks = max(1, int(self.min_speech_ms / 1000.0 / self.chunk_duration))
        self.silence_chunks_limit = max(1, int(self.silence_ms / 1000.0 / self.chunk_duration))
        self.max_chunks = int(self.max_recording_seconds / self.chunk_duration)
        self.preroll_chunks = max(1, int(self.preroll_ms / 1000.0 / self.chunk_duration))
        
        # Calibration state
        self.is_calibrated = False
        self.calibration_rms_list = []
        self.calibration_chunks_needed = int(0.5 / self.chunk_duration)  # 0.5 seconds calibration
        
        self.noise_rms = silence_threshold
        self.start_threshold = silence_threshold
        self.stop_threshold = silence_threshold / 2.0
        
        # State machine tracking
        self.has_spoken = False
        self.speech_start_time = None
        self.speech_end_time = None
        
        self.consecutive_active_chunks = 0
        self.consecutive_silent_chunks = 0
        self.chunks_processed = 0
        
        # Rolling buffer for pre-roll
        self.preroll_buffer = []
        
    def process_frame(self, frame: np.ndarray) -> bool:
        """
        Applies RMS calculation and tracks VAD state transitions.
        
        Returns:
            True if the VAD engine decides the recording should stop.
        """
        self.chunks_processed += 1
        
        # Guard max duration
        if self.chunks_processed >= self.max_chunks:
            logger.info(f"[VOICE] Max duration reached ({self.max_recording_seconds}s) — forcing stop")
            return True
            
        flat_frame = frame.flatten()
        rms = np.sqrt(np.mean(flat_frame ** 2)) if len(flat_frame) > 0 else 0
        
        # 1. Calibration phase
        if not self.is_calibrated:
            self.calibration_rms_list.append(rms)
            if len(self.calibration_rms_list) >= self.calibration_chunks_needed:
                self.noise_rms = np.mean(self.calibration_rms_list)
                self.start_threshold = max(self.min_threshold, self.noise_rms * self.start_multiplier)
                self.stop_threshold = max(self.min_threshold / 2.0, self.noise_rms * self.stop_multiplier)
                self.is_calibrated = True
                
                logger.info(f"[VOICE] Noise RMS: {self.noise_rms:.6f}")
                logger.info(f"[VOICE] VAD threshold: {self.start_threshold:.6f} (start), {self.stop_threshold:.6f} (stop)")
                logger.info(f"[VOICE] VAD multiplier: {self.start_multiplier} (start), {self.stop_multiplier} (stop)")
            return False
            
        # 2. VAD processing phase
        if not self.has_spoken:
            # Check for speech start
            if rms >= self.start_threshold:
                self.consecutive_active_chunks += 1
                if self.consecutive_active_chunks >= self.min_speech_chunks:
                    self.has_spoken = True
                    self.speech_start_time = self.chunks_processed * self.chunk_duration
                    logger.info(f"[VOICE] Speech detected at: {self.speech_start_time:.3f}s")
            else:
                self.consecutive_active_chunks = 0
        else:
            # Check for speech stop
            if rms < self.stop_threshold:
                self.consecutive_silent_chunks += 1
                if self.consecutive_silent_chunks >= self.silence_chunks_limit:
                    self.speech_end_time = self.chunks_processed * self.chunk_duration
                    logger.info(f"[VOICE] Speech ended at: {self.speech_end_time:.3f}s")
                    return True
            else:
                self.consecutive_silent_chunks = 0
                
        return False
