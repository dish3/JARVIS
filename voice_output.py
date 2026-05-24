#!/usr/bin/env python3
"""
Voice Output - Text-to-Speech using pyttsx3
Converts text to speech and plays audio
"""

import logging
from typing import Optional

logger = logging.getLogger('VOICE_OUTPUT')


class VoiceOutput:
    """Convert text to speech and play audio"""
    
    def __init__(self, rate: int = 150, volume: float = 0.9):
        """
        Initialize voice output
        
        Args:
            rate: Speech rate (words per minute)
            volume: Volume level (0.0 to 1.0)
        """
        logger.info(f"Initializing Voice Output (rate: {rate}, volume: {volume})...")
        
        try:
            import pyttsx3
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', rate)
            self.engine.setProperty('volume', volume)
            self.muted = False
            logger.info("[OK] Voice Output initialized with pyttsx3")
        except ImportError:
            logger.warning("pyttsx3 not installed. Install with: pip install pyttsx3")
            self.engine = None
            self.muted = False
    
    def speak(self, text: str, wait: bool = True) -> bool:
        """
        Speak text
        
        Args:
            text: Text to speak
            wait: Wait for speech to finish
            
        Returns:
            True if successful, False otherwise
        """
        if self.muted:
            logger.info(f"[VOICE] Muted - skipping: {text[:100]}...")
            return True
        
        logger.info(f"[VOICE] Speaking: {text[:100]}...")
        
        if not self.engine:
            logger.error("[VOICE] Engine not initialized")
            return False
        
        try:
            self.engine.say(text)
            if wait:
                self.engine.runAndWait()
            logger.info("[VOICE] Speech completed")
            return True
        
        except Exception as e:
            logger.error(f"[VOICE] Speech error: {str(e)}")
            return False
    
    def save_to_file(self, text: str, filename: str) -> bool:
        """
        Save speech to audio file
        
        Args:
            text: Text to convert
            filename: Output filename
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"[VOICE] Saving to file: {filename}")
        
        if not self.engine:
            logger.error("[VOICE] Engine not initialized")
            return False
        
        try:
            self.engine.save_to_file(text, filename)
            self.engine.runAndWait()
            logger.info(f"[VOICE] Saved to: {filename}")
            return True
        
        except Exception as e:
            logger.error(f"[VOICE] Save error: {str(e)}")
            return False
    
    def set_voice(self, voice_id: int = 0) -> bool:
        """
        Set voice (0=default, 1=alternative if available)
        
        Args:
            voice_id: Voice index
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"[VOICE] Setting voice: {voice_id}")
        
        if not self.engine:
            logger.error("[VOICE] Engine not initialized")
            return False
        
        try:
            voices = self.engine.getProperty('voices')
            if voice_id < len(voices):
                self.engine.setProperty('voice', voices[voice_id].id)
                logger.info(f"[VOICE] Voice set to: {voices[voice_id].name}")
                return True
            else:
                logger.warning(f"[VOICE] Voice {voice_id} not available")
                return False
        
        except Exception as e:
            logger.error(f"[VOICE] Voice set error: {str(e)}")
            return False
    
    def mute(self) -> None:
        """Mute voice output"""
        self.muted = True
        logger.info("[VOICE] Muted")
    
    def unmute(self) -> None:
        """Unmute voice output"""
        self.muted = False
        logger.info("[VOICE] Unmuted")


def main():
    """Test voice output"""
    output = VoiceOutput(rate=150, volume=0.9)
    
    # Test speak
    print("\n=== Test Speak ===")
    output.speak("Hello! This is JARVIS speaking.")
    
    # Test save to file
    print("\n=== Test Save to File ===")
    output.save_to_file("This is a test audio file.", "test_output.mp3")
    
    # List available voices
    print("\n=== Available Voices ===")
    try:
        import pyttsx3
        engine = pyttsx3.init()
        voices = engine.getProperty('voices')
        for i, voice in enumerate(voices):
            print(f"{i}: {voice.name}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == '__main__':
    main()
