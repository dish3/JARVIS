#!/usr/bin/env python3
"""
JARVIS Voice Activity Detection (VAD)
Manages silence limits and triggers auto-stop thresholding.
"""

import numpy as np
import logging

logger = logging.getLogger('VOICE.VAD')

class VADDetector:
    """
    Decoupled state machine for monitoring silence thresholds and VAD limits.
    """
    def __init__(self, sample_rate: int, silence_threshold: float = 0.003, 
                 initial_silence_limit: float = 4.0, active_silence_limit: float = 1.5,
                 max_duration: float = 15.0, chunk_size: int = 4096):
        """
        Initialize VAD Detector parameters.
        """
        self.sample_rate = sample_rate
        self.silence_threshold = silence_threshold
        self.initial_silence_limit = initial_silence_limit
        self.active_silence_limit = active_silence_limit
        self.max_duration = max_duration
        self.chunk_size = chunk_size
        
        self.has_spoken = False
        self.silence_count = 0
        self.chunk_duration = chunk_size / sample_rate
        self.max_chunks = int(max_duration / self.chunk_duration)
        self.chunks_recorded = 0
        
    def process_frame(self, frame: np.ndarray) -> bool:
        """
        Applies RMS calculation on a single audio chunk.
        
        Returns:
            True if the VAD engine decides the recording should auto-stop.
        """
        self.chunks_recorded += 1
        
        # Guard max duration
        if self.chunks_recorded >= self.max_chunks:
            logger.info(f"[VOICE] Max duration reached ({self.max_duration}s) — forcing stop")
            return True
            
        flat_frame = frame.flatten()
        rms = np.sqrt(np.mean(flat_frame ** 2)) if len(flat_frame) > 0 else 0
        
        if rms >= self.silence_threshold:
            if not self.has_spoken:
                logger.info("[VOICE] Active speech detected — switching to active silence threshold")
            self.has_spoken = True
            self.silence_count = 0
        else:
            self.silence_count += 1
            
        limit = self.active_silence_limit if self.has_spoken else self.initial_silence_limit
        chunks_needed = int(limit / self.chunk_duration)
        
        if self.silence_count >= chunks_needed:
            logger.info(f"[VOICE] Silence detected ({limit}s) — VAD auto-stopping")
            return True
            
        return False
