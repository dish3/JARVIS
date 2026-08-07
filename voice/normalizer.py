#!/usr/bin/env python3
"""
JARVIS Voice Normalizer Module
Clean and normalize transcription output.
"""

import string
import logging

logger = logging.getLogger('VOICE.NORMALIZER')

def normalize_text(raw_text: str) -> str:
    """
    Cleans raw text by stripping leading/trailing whitespaces, 
    converting to lowercase, stripping punctuation, and collapsing multiple spaces.
    
    Args:
        raw_text: String to clean.
        
    Returns:
        Cleaned and normalized string.
    """
    if not raw_text:
        return ""
        
    result = raw_text.strip()
    result_lower = result.lower().strip(string.punctuation + ' ')
    result_normalized = ' '.join(result_lower.split())
    
    logger.info(f"[VOICE] Normalized transcript: {result_normalized!r}")
    return result_normalized
