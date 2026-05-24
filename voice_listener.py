#!/usr/bin/env python3
"""
Voice Listener - Speech-to-Text using Faster-Whisper
Captures audio and transcribes to text
"""

import logging
import numpy as np
from typing import Optional, Callable

logger = logging.getLogger('VOICE_LISTENER')


class VoiceListener:
    """Capture and transcribe voice input"""
    
    def __init__(self, model_size: str = 'base'):
        """
        Initialize voice listener
        
        Args:
            model_size: Faster-Whisper model size (tiny, base, small, medium, large)
        """
        logger.info(f"Initializing Voice Listener (model: {model_size})...")
        
        try:
            from faster_whisper import WhisperModel
            self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
            logger.info("[OK] Voice Listener initialized with Faster-Whisper")
        except ImportError:
            logger.warning("Faster-Whisper not installed. Install with: pip install faster-whisper")
            self.model = None
    
    def transcribe_audio(self, audio_path: str) -> Optional[str]:
        """
        Transcribe audio file to text
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Transcribed text or None if error
        """
        logger.info(f"[VOICE] Transcribing: {audio_path}")
        
        if not self.model:
            logger.error("[VOICE] Model not initialized")
            return None
        
        try:
            # Use language detection and beam search for better accuracy
            segments, info = self.model.transcribe(
                audio_path, 
                language="en",
                beam_size=5,
                best_of=5
            )
            
            # Combine all segments
            text = " ".join([segment.text for segment in segments])
            
            if not text or not text.strip():
                logger.warning("[VOICE] No speech detected in audio")
                return None
            
            logger.info(f"[VOICE] Transcribed: {text[:100]}...")
            return text
        
        except Exception as e:
            logger.error(f"[VOICE] Transcription error: {str(e)}")
            return None
    
    def transcribe_bytes(self, audio_bytes: bytes) -> Optional[str]:
        """
        Transcribe audio from bytes
        
        Args:
            audio_bytes: Audio data as bytes
            
        Returns:
            Transcribed text or None if error
        """
        logger.info("[VOICE] Transcribing from bytes...")
        
        if not self.model:
            logger.error("[VOICE] Model not initialized")
            return None
        
        try:
            import tempfile
            import os
            
            # Write bytes to temporary file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                f.write(audio_bytes)
                temp_path = f.name
            
            try:
                # Transcribe
                segments, info = self.model.transcribe(temp_path, language="en")
                text = " ".join([segment.text for segment in segments])
                
                logger.info(f"[VOICE] Transcribed: {text[:100]}...")
                return text
            finally:
                # Clean up temp file
                if os.path.exists(temp_path):
                    os.remove(temp_path)
        
        except Exception as e:
            logger.error(f"[VOICE] Transcription error: {str(e)}")
            return None


def main():
    """Test voice listener"""
    listener = VoiceListener(model_size='base')
    
    # Test with a sample audio file if available
    import os
    if os.path.exists('sample_audio.wav'):
        print("\n=== Test Transcription ===")
        result = listener.transcribe_audio('sample_audio.wav')
        print(f"Result: {result}")
    else:
        print("No sample audio file found. Create one to test.")


if __name__ == '__main__':
    main()


# Module-level voice listener - initialized once to avoid reloading model
_voice_listener = None

def _get_voice_listener():
    """Get or create module-level voice listener instance."""
    global _voice_listener
    if _voice_listener is None:
        _voice_listener = VoiceListener(model_size='tiny')
    return _voice_listener


def listen_ptt(hotkey: str = "F9") -> Optional[str]:
    """Push-to-talk: hold hotkey to record, release to transcribe.
    Uses module-level VoiceListener to avoid reloading model.
    Returns transcribed text or None."""
    import keyboard
    import sounddevice as sd
    import numpy as np
    import tempfile
    import os
    import soundfile as sf
    
    SAMPLE_RATE = 16000
    
    # Use module-level listener (model loaded once)
    listener = _get_voice_listener()
    print(f"[JARVIS] Hold {hotkey} to speak. Release to process.")
    frames = []
    
    def audio_callback(indata, frame_count, time_info, status):
        if status:
            logger.warning(f"[VOICE] Audio callback status: {status}")
        frames.append(indata.copy())
    
    try:
        # Wait for key press
        keyboard.wait(hotkey)
        print("[JARVIS] Listening...")
        frames.clear()
        
        # Record while key is held
        with sd.InputStream(samplerate=SAMPLE_RATE,
                           channels=1,
                           dtype='float32',
                           device=1,
                           callback=audio_callback,
                           blocksize=4096):
            while keyboard.is_pressed(hotkey):
                sd.sleep(50)
        
        print("[JARVIS] Transcribing...")
        if not frames:
            logger.warning("[VOICE] No audio frames captured")
            return None
        
        # Convert to numpy array
        audio = np.concatenate(frames, axis=0).flatten()
        
        # Check if audio has sufficient volume (not just silence)
        rms = np.sqrt(np.mean(audio ** 2))
        if rms < 0.003:
            logger.warning(f"[VOICE] Audio too quiet (RMS: {rms:.4f}), likely silence")
            print("[JARVIS] No speech detected. Try speaking louder.")
            return None
        
        # Save to temp file and use existing transcribe method
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            temp_path = f.name
            sf.write(temp_path, audio, SAMPLE_RATE)
        
        try:
            result = listener.transcribe_audio(temp_path)
            if result:
                print(f"[JARVIS] Heard: {result}")
                return result
            else:
                print("[JARVIS] Could not understand. Try again.")
                return None
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    except Exception as e:
        logger.error(f"[VOICE] Voice error: {e}")
        print(f"[JARVIS] Voice error: {e}")
        return None
