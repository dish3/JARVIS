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
        confidence_threshold = float(os.getenv("VOICE_CONFIDENCE_THRESHOLD", "0.4"))
            
        logger.info(f"[VOICE] Whisper confidence: {confidence:.4f}")
        
        # Confidence threshold check
        if confidence < confidence_threshold:
            logger.warning(f"[VOICE] Transcript rejected: '{text}' (low confidence {confidence:.4f})")
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
            logger.warning("[VOICE] Transcript rejected: empty transcript")
            return None
            
        logger.info(f"[VOICE] Transcript accepted: '{text}' (confidence: {confidence:.4f})")
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
        
    raw_frames = []
    frames = []
    callback_count = 0
    
    def audio_callback(indata, frame_count, time_info, status):
        nonlocal callback_count
        if status:
            logger.warning(f"[VOICE] Audio callback status: {status}")
        raw_frames.append(indata.copy())
        callback_count += 1

    # Wait if TTS is speaking to prevent microphone loopback feedback
    from voice_output import is_tts_speaking
    post_tts_cooldown = float(os.getenv("VOICE_POST_TTS_COOLDOWN_MS", "300")) / 1000.0
    if is_tts_speaking():
        logger.info("[VOICE] TTS is currently active. Pausing listen start.")
        while is_tts_speaking():
            time.sleep(0.05)
        logger.info(f"[VOICE] TTS completed. Waiting post-TTS cooldown of {post_tts_cooldown}s...")
        time.sleep(post_tts_cooldown)

    keyboard_available = False
    if use_keyboard:
        try:
            import keyboard
            keyboard_available = True
        except Exception as kb_err:
            logger.warning(f"[VOICE] keyboard module unavailable: {kb_err} — using VAD fallback")

    recording_start = time.time()
    detector = VADDetector(sample_rate=SAMPLE_RATE)
    
    try:
        if keyboard_available:
            import keyboard
            keyboard.wait(hotkey)
            logger.info("[VOICE] Hotkey pressed — recording started")
            print("[JARVIS] Listening...")
            raw_frames.clear()

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
            frames = raw_frames.copy()
        else:
            # Fallback/Server mode: Voice Activity Detection (VAD) loop
            logger.info("[VOICE] Recording started (VAD auto-stop)")
            logger.info("[VOICE] Capture started")
            print("[JARVIS] Listening... (will auto-stop after speech ends)")
            raw_frames.clear()
            frames.clear()
            processed_count = 0
            speech_started = False
            
            with sd.InputStream(samplerate=SAMPLE_RATE,
                                channels=1,
                                dtype='float32',
                                device=selected_mic,
                                callback=audio_callback,
                                blocksize=4096) as stream:
                
                chunk_duration = 4096 / SAMPLE_RATE
                while True:
                    if stop_event and stop_event.is_set():
                        logger.info("[VOICE] Stop event detected — stopping recording")
                        break
                        
                    sd.sleep(int(chunk_duration * 1000))
                    
                    stop_loop = False
                    while processed_count < len(raw_frames):
                        chunk = raw_frames[processed_count]
                        processed_count += 1
                        
                        should_stop = detector.process_frame(chunk)
                        
                        if detector.has_spoken:
                            if not speech_started:
                                # Prepend pre-roll buffer to final frames
                                frames.extend(detector.preroll_buffer)
                                speech_started = True
                                print(f"[CALLBACK_STATUS] 1. VAD speech start: stream active={stream.active}", flush=True)
                            # Append current chunk to speech frames
                            frames.append(chunk)
                        else:
                            # Not speaking yet, maintain pre-roll buffer in detector
                            if len(detector.preroll_buffer) >= detector.preroll_chunks:
                                detector.preroll_buffer.pop(0)
                            detector.preroll_buffer.append(chunk)
                            
                        if should_stop:
                            print(f"[CALLBACK_STATUS] 2. VAD speech end: stream active={stream.active}", flush=True)
                            stop_loop = True
                            break
                    if stop_loop:
                        break

                print(f"[CALLBACK_STATUS] 3. Recording stop begins: stream active={stream.active}", flush=True)
                logger.info("[VOICE] Stopping capture")
                print(f"[CALLBACK_STATUS] 4. Before stream.stop(): stream active={stream.active}", flush=True)
                stream.stop()
                print(f"[CALLBACK_STATUS] 4. After stream.stop(): stream active={stream.active}", flush=True)
                print(f"[CALLBACK_STATUS] 5. Before stream.close(): stream active={stream.active}", flush=True)
                stream.close()
                print(f"[CALLBACK_STATUS] 5. After stream.close(): stream active={stream.active}", flush=True)
                logger.info("[VOICE] Waiting for capture buffer flush")
                sd.sleep(100) # Allow any last frame in progress to complete
                logger.info("[VOICE] Capture buffer flushed")
                logger.info("[VOICE] Recording stopped")

        recording_duration = time.time() - recording_start
        
        # Gather device info for telemetry
        dev_name = "Intel Smart Sound / Default Input"
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            if selected_mic is not None and selected_mic < len(devices):
                dev_name = devices[selected_mic]['name']
        except Exception:
            pass

        # Save stage 1: RAW_CAPTURE
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        os.makedirs("voice_debug", exist_ok=True)
        raw_wav_path = f"voice_debug/raw_capture_{timestamp}.wav"
        if raw_frames:
            raw_audio = np.concatenate(raw_frames, axis=0).flatten()
            sf.write(raw_wav_path, raw_audio, SAMPLE_RATE)
            logger.info(f"[VOICE] Saved raw capture: {raw_wav_path}")
            
        if not frames:
            logger.warning("[VOICE] No audio frames captured in final segment")
            print(f"\n[VOICE.CAPTURE]")
            print(f"callback_count: {callback_count}")
            print(f"callback_samples: {callback_count * 4096}")
            print("[VOICE] RESULT: CAPTURE_FAILED")
            return None

        # Convert final segment to numpy array
        audio = np.concatenate(frames, axis=0).flatten()
        stats = calculate_audio_stats(audio, SAMPLE_RATE)
        segment_duration = len(audio) / SAMPLE_RATE

        print(f"[CALLBACK_STATUS] 6. Final WAV construction: stream active={stream.active if 'stream' in locals() else False}", flush=True)

        # Save stage 2 & 3: VAD_SEGMENT and WHISPER_INPUT
        vad_wav_path = f"voice_debug/vad_segment_{timestamp}.wav"
        whisper_wav_path = f"voice_debug/whisper_input_{timestamp}.wav"
        sf.write(vad_wav_path, audio, SAMPLE_RATE)
        sf.write(whisper_wav_path, audio, SAMPLE_RATE)
        logger.info(f"[VOICE] Saved VAD segment: {vad_wav_path}")
        logger.info(f"[VOICE] Saved Whisper input: {whisper_wav_path}")

        # VAD Telemetry
        print(f"\n[VOICE.CAPTURE]")
        print(f"callback_count: {callback_count}")
        print(f"callback_samples: {callback_count * 4096}")
        
        print(f"\n[VOICE.VAD]")
        print(f"frames_received: {callback_count}")
        print(f"frames_examined: {processed_count}")
        print(f"frames_consumed: {processed_count - len(frames) if processed_count > len(frames) else 0}")
        
        print(f"\n[VOICE.RECORDING]")
        print(f"frames_saved: {len(frames)}")
        print(f"samples_saved: {len(audio)}")
        
        print(f"\n[VOICE.WAV]")
        print(f"samples_written: {len(audio)}")
        print(f"duration_written: {segment_duration:.2f}")

        # Maintain additional templates for diagnostic parsing
        print(f"\n[VOICE.CAPTURE] callback_frames: {len(raw_frames)}  samples: {len(raw_frames) * 4096}")
        print(f"[VOICE.WAV]     duration: {segment_duration:.2f}s  RMS: {stats['rms']:.6f}")

        # Check VAD speech detection state
        if not detector.has_spoken:
            print("[VOICE] RESULT: VAD_NO_SPEECH")
            print("[JARVIS] No speech detected. Try speaking louder.")
            return None

        # Save copy to voice_debug directory as the primary debug recording
        save_debug_wav(audio, SAMPLE_RATE)

        # Transcribe
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            temp_path = f.name
            sf.write(temp_path, audio, SAMPLE_RATE)

        try:
            print(f"\n[VOICE.STT]")
            print(f"input WAV duration: {segment_duration:.2f}s")
            print(f"input sample rate: {SAMPLE_RATE}")
            print(f"Whisper model: {listener.transcriber.model_size}")
            
            stt_start = time.time()
            res = listener.transcriber.transcribe(temp_path)
            stt_end = time.time()
            
            print(f"transcription start: {stt_start:.2f}s")
            print(f"transcription end: {stt_end:.2f}s")
            print(f"transcription duration: {stt_end - stt_start:.2f}s")
            
            if not res.get('success'):
                print(f"raw transcript: N/A")
                print(f"confidence: 0.0000")
                print("[VOICE] RESULT: CAPTURE_FAILED")
                return None
                
            raw = res['text']
            confidence = res['confidence']
            
            # Read config gates
            confidence_threshold = float(os.getenv("VOICE_CONFIDENCE_THRESHOLD", "0.4"))
            
            if not raw or not raw.strip():
                print("raw transcript: ''")
                print(f"confidence: {confidence:.4f}")
                print("[VOICE] RESULT: STT_EMPTY")
                return None
                
            print(f"raw transcript: {raw!r}")
            print(f"confidence: {confidence:.4f}")

            if confidence < confidence_threshold:
                print(f"[VOICE] Rejected transcript: {raw!r} (confidence={confidence:.4f})")
                print("[VOICE] RESULT: STT_LOW_CONFIDENCE")
                # Trigger speak out loud
                try:
                    from voice_output import VoiceOutput
                    VO = VoiceOutput()
                    VO.speak("Sorry, I didn't catch that clearly, can you repeat?")
                except Exception as tts_err:
                    logger.warning(f"[VOICE] Failed to speak fallback error: {tts_err}")
                return None

            print("[VOICE] RESULT: STT_SUCCESS")
            print(f"[VOICE] STT result: {raw}", flush=True)

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
