#!/usr/bin/env python3
"""
Voice Listener - Entry point interface for voice pipeline
Maintains backwards compatibility with existing callers.
Delegates to the decoupled `voice` package modules.
"""

import os
import sys
import logging
from typing import Optional, Callable
from dotenv import load_dotenv

load_dotenv(override=True)
logger = logging.getLogger('VOICE_LISTENER')

# Import package modules
from voice.normalizer import normalize_text
from voice.utils import save_debug_wav, calculate_audio_stats
from voice.audio_capture import select_mic_device, list_input_devices
from voice.vad import VADDetector
from voice.stt import STTTranscriber

class VoiceListener:
    """Capture and transcribe voice input"""
    
    def __init__(self, model_size: str = 'base'):
        """
        Initialize voice listener
        """
        logger.info(f"[VOICE] Whisper model: {model_size}")
        self.transcriber = STTTranscriber(model_size)
        
    def transcribe_audio(self, audio_path: str) -> Optional[str]:
        """
        Transcribe audio file to text.
        Applies confidence gates and diagnostic checks.
        
        Args:
            audio_path: Path to audio file.
            
        Returns:
            Transcribed text or None if error/rejected.
        """
        if not self.transcriber.model:
            logger.error("[VOICE] Model not initialized")
            return None
            
        # Transcribe using our STT engine
        res = self.transcriber.transcribe(audio_path)
        if not res.get('success'):
            return None
            
        text = res['text']
        confidence = res['confidence']
        avg_lp = res['avg_logprob']
        detected_lang = res['detected_lang']
        
        # Read config gates
        diagnostic_mode = os.getenv("VOICE_DIAGNOSTIC", "false").lower() == "true"
        confidence_threshold = float(os.getenv("VOICE_CONFIDENCE_THRESHOLD", "0.4"))
        
        # STT Diagnostic-only mode check
        if diagnostic_mode:
            logger.info(f"[VOICE] [DIAGNOSTIC] Skipping router/planner. Raw transcript: {text!r}")
            print(f"[JARVIS] STT Diagnostic: Detected: {text}", flush=True)
            print(f"[TASK COMPLETE] [OK] [none] [DIAGNOSTIC] Heard: {text}", flush=True)
            return None
            
        # Confidence threshold check
        if confidence < confidence_threshold:
            logger.warning(f"[VOICE] Transcription confidence ({confidence:.4f}, avg_logprob: {avg_lp:.4f}) below threshold ({confidence_threshold})")
            print("[JARVIS] Sorry, I didn't catch that clearly, can you repeat?", flush=True)
            print("[TASK COMPLETE] [OK] [none] Sorry, I didn't catch that clearly, can you repeat?", flush=True)
            
            try:
                from voice_output import VoiceOutput
                VO = VoiceOutput()
                VO.speak("Sorry, I didn't catch that clearly, can you repeat?")
            except Exception as tts_err:
                logger.warning(f"[VOICE] Failed to speak fallback error: {tts_err}")
            return None
            
        if not text or not text.strip():
            logger.warning("[VOICE] No speech detected in audio")
            return None
            
        return text

    def transcribe_bytes(self, audio_bytes: bytes) -> Optional[str]:
        """
        Transcribe audio from bytes
        """
        import tempfile
        try:
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                f.write(audio_bytes)
                temp_path = f.name
            try:
                return self.transcribe_audio(temp_path)
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
        except Exception as e:
            logger.error(f"[VOICE] Transcription error: {str(e)}")
            return None


# Module-level voice listener singleton
_voice_listener = None

def _get_voice_listener():
    """Get or create module-level voice listener instance."""
    global _voice_listener
    if _voice_listener is None:
        _voice_listener = VoiceListener(model_size='tiny')
    return _voice_listener

def _select_mic_device() -> int | None:
    """Enumerate available input devices and return selected device index."""
    return select_mic_device()


def listen_ptt(hotkey: str = "F9", stop_event=None, use_keyboard: bool = True) -> Optional[str]:
    """Push-to-talk: hold hotkey to record, release to transcribe.
    Maintains compatibility with caller signatures.
    """
    import time
    import sounddevice as sd
    import numpy as np
    import tempfile
    import soundfile as sf
    
    if sys.platform == 'win32':
        try:
            import ctypes
            ctypes.windll.ole32.CoInitialize(None)
        except Exception as com_err:
            logger.warning(f"[VOICE] CoInitialize failed: {com_err}")

    # 1. Microphone check
    selected_mic = _select_mic_device()
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

    keyboard_available = False
    if use_keyboard:
        try:
            import keyboard
            keyboard_available = True
        except Exception as kb_err:
            logger.warning(f"[VOICE] keyboard module unavailable: {kb_err} — using VAD fallback")

    recording_start = time.time()
    
    try:
        if keyboard_available:
            import keyboard
            keyboard.wait(hotkey)
            logger.info("[VOICE] Hotkey pressed — recording started")
            print("[JARVIS] Listening...")
            frames.clear()

            with sd.InputStream(samplerate=SAMPLE_RATE,
                                channels=1,
                                dtype='float32',
                                device=selected_mic,
                                callback=audio_callback,
                                blocksize=4096):
                while keyboard.is_pressed(hotkey):
                    if stop_event and stop_event.is_set():
                        break
                    sd.sleep(50)

            logger.info("[VOICE] Recording stopped")
        else:
            # Fallback/Server mode: Voice Activity Detection (VAD) loop
            logger.info("[VOICE] Recording started (VAD auto-stop)")
            print("[JARVIS] Listening... (will auto-stop after 1.5s of silence)")
            frames.clear()

            detector = VADDetector(sample_rate=SAMPLE_RATE)
            
            with sd.InputStream(samplerate=SAMPLE_RATE,
                                channels=1,
                                dtype='float32',
                                device=selected_mic,
                                callback=audio_callback,
                                blocksize=4096):
                
                chunk_duration = 4096 / SAMPLE_RATE
                while True:
                    if stop_event and stop_event.is_set():
                        logger.info("[VOICE] Stop event detected — stopping recording")
                        break
                        
                    sd.sleep(int(chunk_duration * 1000))
                    
                    if len(frames) > 0:
                        # Process latest frame via VAD state machine
                        if detector.process_frame(frames[-1]):
                            break

            logger.info("[VOICE] Recording stopped")

        recording_duration = time.time() - recording_start
        logger.info(f"[VOICE] Recording duration: {recording_duration:.2f}s")
        print("[JARVIS] Transcribing...")

        if not frames:
            logger.warning("[VOICE] No audio frames captured")
            return None

        # Convert to numpy array
        audio = np.concatenate(frames, axis=0).flatten()
        
        # Calculate & log audio stats (RMS, Peak, Silence%, Clipping warning)
        stats = calculate_audio_stats(audio, SAMPLE_RATE)
        
        if stats['rms'] < 0.003:
            logger.warning(f"[VOICE] Audio too quiet (RMS: {stats['rms']:.4f}), likely silence")
            print("[JARVIS] No speech detected. Try speaking louder.")
            return None

        # Save copy to voice_debug directory
        save_debug_wav(audio, SAMPLE_RATE)

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

            # Clean and normalize text transcript
            norm_start = time.time()
            result_normalized = normalize_text(raw)
            norm_time = (time.time() - norm_start) * 1000
            logger.info(f"[VOICE] Normalization duration: {norm_time:.2f} ms")
            
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
