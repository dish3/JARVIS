#!/usr/bin/env python3
"""
JARVIS Voice Speech-to-Text (STT)
Interfaces with Faster-Whisper to transcribe audio files with word confidence tracking.
"""

import os
import math
import time
import logging
from dotenv import load_dotenv

load_dotenv(override=True)
logger = logging.getLogger('VOICE.STT')

class STTTranscriber:
    """
    Handles local Whisper inference and word-level probability extraction.
    """
    def __init__(self, model_size: str = 'base'):
        """
        Initialize the Faster-Whisper engine.
        """
        self.model_size = model_size
        logger.info(f"[VOICE] Whisper model: {model_size} (Initializing...)")
        try:
            from faster_whisper import WhisperModel
            # Load model on CPU with Int8 quantization for fast local execution
            self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
            logger.info("[VOICE] Whisper model: Initialized successfully")
        except ImportError:
            logger.warning("[VOICE] Whisper model: faster-whisper not installed.")
            self.model = None

    def transcribe(self, audio_path: str) -> dict:
        """
        Transcribes the target audio file.
        
        Returns:
            A dictionary containing:
            - success (bool)
            - text (str)
            - confidence (float)
            - avg_logprob (float)
            - detected_lang (str)
            - lang_prob (float)
            - words (list of tuples: (word, probability))
            - whisper_time (float)
        """
        if not self.model:
            logger.error("[VOICE] STT model is not initialized.")
            return {'success': False, 'error': 'Model not initialized'}
            
        start_time = time.time()
        
        # Read language configurations
        lang_mode = os.getenv("VOICE_LANGUAGE_MODE", "english").lower()
        whisper_lang = "en" if lang_mode == "english" else None
        
        try:
            # Transcribe with word timestamps enabled to fetch per-word probabilities
            segments, info = self.model.transcribe(
                audio_path,
                language=whisper_lang,
                beam_size=5,
                best_of=5,
                word_timestamps=True
            )
            
            segment_list = list(segments)
            text = " ".join([s.text for s in segment_list])
            
            whisper_time = time.time() - start_time
            logger.info(f"[VOICE] Whisper transcription duration: {whisper_time:.3f}s")
            
            # Extract word confidence logs
            words_confidence = []
            for segment in segment_list:
                if segment.words:
                    for w in segment.words:
                        word_text = w.word.strip()
                        word_prob = w.probability
                        words_confidence.append((word_text, word_prob))
                        logger.info(f"[VOICE] Word confidence: '{word_text}' (prob={word_prob:.4f})")
                        
            # Compute confidence score from avg_logprob of segments
            if segment_list:
                avg_lp = sum(s.avg_logprob for s in segment_list) / len(segment_list)
                confidence = math.exp(avg_lp)
            else:
                avg_lp = 0.0
                confidence = 0.0
                
            detected_lang = info.language if info else "unknown"
            lang_prob = info.language_probability if info else 0.0
            
            # Log exact metrics required by pipeline diagnostics
            logger.info(f"[VOICE] Detected language: {detected_lang} (prob: {lang_prob:.4f})")
            logger.info(f"[VOICE] Raw transcript: {text!r}")
            logger.info(f"[VOICE] Confidence: {confidence:.4f} (avg_logprob: {avg_lp:.4f})")
            
            return {
                'success': True,
                'text': text,
                'confidence': confidence,
                'avg_logprob': avg_lp,
                'detected_lang': detected_lang,
                'lang_prob': lang_prob,
                'words': words_confidence,
                'whisper_time': whisper_time
            }
            
        except Exception as e:
            logger.error(f"[VOICE] Whisper transcription failure: {e}")
            return {'success': False, 'error': str(e)}
