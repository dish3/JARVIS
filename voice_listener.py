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
                language=None,
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
                segments, info = self.model.transcribe(temp_path, language=None)
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


def _select_mic_device() -> int | None:
    """
    Enumerate available input devices and return the best one to use.

    Priority order:
      1. Default system input device (sounddevice.default.device[0])
      2. First device whose name contains 'microphone' or 'mic' (case-insensitive)
      3. First device with at least 1 input channel
      4. None  → sounddevice will use its own default (same as not passing device=)

    Logs every candidate and the final selection with [MIC DEVICE] tag.
    Never raises — all errors return None so recording still proceeds.
    """
    try:
        import sounddevice as sd

        devices = sd.query_devices()
        default_input_idx = sd.default.device[0]  # may be -1 if unset

        logger.info("[MIC DEVICE] Available input devices:")
        input_devices = []
        for idx, dev in enumerate(devices):
            if dev['max_input_channels'] > 0:
                marker = ' <-- default' if idx == default_input_idx else ''
                logger.info(
                    f"[MIC DEVICE]   [{idx}] {dev['name']} "
                    f"(channels={dev['max_input_channels']}){marker}"
                )
                input_devices.append((idx, dev))

        if not input_devices:
            logger.warning("[MIC DEVICE] No input devices found — using sounddevice default")
            return None

        # 1. Use system default if it is a valid input device
        if default_input_idx >= 0:
            default_dev = devices[default_input_idx]
            if default_dev['max_input_channels'] > 0:
                logger.info(
                    f"[MIC DEVICE] Selected default system mic: "
                    f"[{default_input_idx}] {default_dev['name']}"
                )
                return default_input_idx

        # 2. Prefer a device whose name contains 'microphone' or 'mic'
        for idx, dev in input_devices:
            name_lower = dev['name'].lower()
            if 'microphone' in name_lower or 'mic' in name_lower:
                logger.info(
                    f"[MIC DEVICE] Selected by name match: [{idx}] {dev['name']}"
                )
                return idx

        # 3. Fall back to first available input device
        idx, dev = input_devices[0]
        logger.info(
            f"[MIC DEVICE] Fallback to first input device: [{idx}] {dev['name']}"
        )
        return idx

    except Exception as e:
        logger.warning(f"[MIC DEVICE] Device enumeration failed: {e} — using sounddevice default")
        return None


# Defer mic device resolution to run on the active recording thread
_mic_device = None


def listen_ptt(hotkey: str = "F9", stop_event=None, use_keyboard: bool = True) -> Optional[str]:
    """Push-to-talk: hold hotkey to record, release to transcribe.
    Uses module-level VoiceListener to avoid reloading model.
    Returns transcribed text or None.

    Fallback/Server Mode: if use_keyboard is False or hooks are unavailable,
    records immediately and auto-stops on silence (VAD) or stop_event trigger.
    """
    import sys
    if sys.platform == 'win32':
        try:
            import ctypes
            ctypes.windll.ole32.CoInitialize(None)
        except Exception as com_err:
            logger.warning(f"[VOICE] CoInitialize failed: {com_err}")

    global _mic_device
    if _mic_device is None:
        _mic_device = _select_mic_device()

    import sounddevice as sd
    import numpy as np
    import tempfile
    import os
    import soundfile as sf

    SAMPLE_RATE = 16000
    listener = _get_voice_listener()

    if use_keyboard:
        logger.info(f"[VOICE] Waiting for {hotkey} (use_keyboard={use_keyboard})")
        print(f"[JARVIS] Hold {hotkey} to speak. Release to process.")
    else:
        logger.info("[VOICE] Microphone active")
    frames = []

    def audio_callback(indata, frame_count, time_info, status):
        if status:
            logger.warning(f"[VOICE] Audio callback status: {status}")
        frames.append(indata.copy())

    # ── Try keyboard hotkey mode ───────────────────────────────────────────────
    keyboard_available = False
    if use_keyboard:
        try:
            import keyboard
            keyboard_available = True
        except Exception as kb_err:
            logger.warning(f"[VOICE] keyboard module unavailable: {kb_err} — using timed fallback")

    try:
        if keyboard_available:
            # Wait for hotkey press
            keyboard.wait(hotkey)
            logger.info(f"[VOICE] F9 detected")
            logger.info(f"[VOICE] Recording started — device={_mic_device}")
            print("[JARVIS] Listening...")
            frames.clear()

            with sd.InputStream(samplerate=SAMPLE_RATE,
                               channels=1,
                               dtype='float32',
                               device=_mic_device,
                               callback=audio_callback,
                               blocksize=4096):
                while keyboard.is_pressed(hotkey):
                    if stop_event and stop_event.is_set():
                        break
                    sd.sleep(50)

            logger.info("[VOICE] Recording stopped")
        else:
            # Fallback: record with silence-based auto-stop (Voice Activity Detection)
            logger.info("[VOICE] Recording started — silence-based auto-stop fallback")
            print("[JARVIS] Listening... (will auto-stop after 1.5s of silence)")
            frames.clear()

            with sd.InputStream(samplerate=SAMPLE_RATE,
                               channels=1,
                               dtype='float32',
                               device=_mic_device,
                               callback=audio_callback,
                               blocksize=4096):
                
                silence_threshold = 0.003
                silence_duration_limit = 1.5  # seconds
                max_duration = 15.0  # seconds
                
                chunk_duration = 4096 / SAMPLE_RATE
                silence_chunks_needed = int(silence_duration_limit / chunk_duration)
                max_chunks = int(max_duration / chunk_duration)
                
                silence_count = 0
                chunks_recorded = 0
                
                while chunks_recorded < max_chunks:
                    if stop_event and stop_event.is_set():
                        logger.info("[VOICE] Stop event detected — stopping recording")
                        break
                        
                    sd.sleep(int(chunk_duration * 1000))
                    chunks_recorded = len(frames)
                    
                    if len(frames) > 0:
                        # Check last frame's root-mean-square (RMS) energy
                        last_frame = frames[-1].flatten()
                        rms = np.sqrt(np.mean(last_frame ** 2)) if len(last_frame) > 0 else 0
                        if rms < silence_threshold:
                            silence_count += 1
                        else:
                            silence_count = 0
                            
                    if silence_count >= silence_chunks_needed:
                        logger.info(f"[VOICE] Silence detected ({silence_duration_limit}s) — auto-stopping")
                        break
                        
            logger.info("[VOICE] Recording stopped (auto-stop)")

        print("[JARVIS] Transcribing...")

        if not frames:
            logger.warning("[VOICE] No audio frames captured")
            return None

        # Convert to numpy array
        audio = np.concatenate(frames, axis=0).flatten()
        logger.info(f"[VOICE] Audio captured — {len(audio)} samples, duration={len(audio)/SAMPLE_RATE:.1f}s")

        # Check if audio has sufficient volume (not just silence)
        rms = np.sqrt(np.mean(audio ** 2))
        logger.info(f"[VOICE] RMS level: {rms:.4f} (threshold=0.003)")
        if rms < 0.003:
            logger.warning(f"[VOICE] Audio too quiet (RMS: {rms:.4f}), likely silence")
            print("[JARVIS] No speech detected. Try speaking louder.")
            return None

        # Save to temp file and transcribe
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            temp_path = f.name
            sf.write(temp_path, audio, SAMPLE_RATE)

        try:
            raw = listener.transcribe_audio(temp_path)
            if not raw or not raw.strip():
                logger.warning("[TRANSCRIPTION] Empty result from Whisper")
                print("[JARVIS] Could not understand. Try again.")
                return None

            # Normalize: strip, lowercase, remove leading/trailing punctuation, collapse whitespace
            import string
            result = raw.strip()
            result_lower = result.lower().strip(string.punctuation + ' ')
            result_normalized = ' '.join(result_lower.split())
            logger.info(f"[TRANSCRIPTION] raw={result!r}")
            logger.info(f"[TRANSCRIPTION] normalized={result_normalized!r}")
            logger.info(f"[VOICE] Sending to router: {result_normalized!r}")
            print(f"[JARVIS] Heard: {result_normalized}")
            return result_normalized

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            if sys.platform == 'win32':
                try:
                    import ctypes
                    ctypes.windll.ole32.CoUninitialize()
                except:
                    pass

    except Exception as e:
        logger.error(f"[VOICE] Voice error: {e}")
        print(f"[JARVIS] Voice error: {e}")
        return None
