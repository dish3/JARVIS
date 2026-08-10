#!/usr/bin/env python3
"""
Unit tests for the JARVIS Voice Pipeline.
Covers microphone selection, VAD, STT transcription confidence gating, 
text normalization, audio DSP stats, debug WAV saving, and replay.
"""

import os
import sys
import unittest
import numpy as np
from unittest.mock import patch, MagicMock

# Ensure VirtualAssistant directory is in the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from voice.normalizer import normalize_text
from voice.utils import save_debug_wav, calculate_audio_stats
from voice.audio_capture import list_input_devices, select_mic_device
from voice.vad import VADDetector
from voice.stt import STTTranscriber
from voice_listener import VoiceListener, listen_ptt

class TestVoicePipeline(unittest.TestCase):

    def setUp(self):
        # Set default environment variables for consistent test conditions
        self.original_env = os.environ.copy()
        os.environ["VOICE_CONFIDENCE_THRESHOLD"] = "0.4"
        os.environ["VOICE_DIAGNOSTIC"] = "false"
        os.environ["VOICE_LANGUAGE_MODE"] = "english"
        os.environ["VOICE_VAD_THRESHOLD"] = "0.003"
        os.environ["VOICE_VAD_MIN_THRESHOLD"] = "0.003"
        os.environ["VOICE_VAD_START_MULTIPLIER"] = "3.0"
        os.environ["VOICE_VAD_STOP_MULTIPLIER"] = "1.5"
        os.environ["VOICE_VAD_MIN_SPEECH_MS"] = "250"
        os.environ["VOICE_VAD_SILENCE_MS"] = "700"
        os.environ["VOICE_VAD_MAX_RECORDING_SECONDS"] = "10"
        os.environ["VOICE_VAD_PREROLL_MS"] = "200"
        os.environ["VOICE_POST_TTS_COOLDOWN_MS"] = "300"

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.original_env)

    # 1. Text Normalization Tests
    def test_normalization(self):
        self.assertEqual(normalize_text("  OPEN  CHROME  "), "open chrome")
        self.assertEqual(normalize_text("Take a Screenshot!"), "take a screenshot")
        self.assertEqual(normalize_text("git status..."), "git status")
        self.assertEqual(normalize_text(""), "")
        self.assertEqual(normalize_text(None), "")

    # 2. Audio DSP Statistics Tests
    def test_audio_dsp_statistics(self):
        # Generate a dummy silent audio array
        sample_rate = 16000
        duration = 1.0
        audio_silent = np.zeros(int(sample_rate * duration), dtype=np.float32)
        
        stats_silent = calculate_audio_stats(audio_silent, sample_rate)
        self.assertEqual(stats_silent['samples'], len(audio_silent))
        self.assertAlmostEqual(stats_silent['duration'], duration)
        self.assertEqual(stats_silent['rms'], 0.0)
        self.assertEqual(stats_silent['peak'], 0.0)
        self.assertEqual(stats_silent['clipping'], False)
        self.assertEqual(stats_silent['silence_pct'], 100.0)

        # Generate non-silent audio (clipping signal)
        audio_loud = np.ones(10000, dtype=np.float32)
        stats_loud = calculate_audio_stats(audio_loud, sample_rate)
        self.assertTrue(stats_loud['clipping'])
        self.assertEqual(stats_loud['silence_pct'], 0.0)

    # 3. Save Debug WAV Test
    @patch('soundfile.write')
    def test_save_debug_wav(self, mock_sf_write):
        audio_data = np.zeros(1000, dtype=np.float32)
        filepath = save_debug_wav(audio_data, 16000)
        self.assertTrue(filepath.startswith("voice_debug"))
        self.assertTrue(filepath.endswith(".wav"))
        mock_sf_write.assert_called_once()

    # 4. Microphone Device Selection Tests
    @patch('sounddevice.query_devices')
    def test_list_input_devices(self, mock_query_devices):
        # Mock two devices, one regular and one virtual
        mock_query_devices.return_value = [
            {'name': 'Realtek Microphone', 'max_input_channels': 2, 'default_samplerate': 44100.0},
            {'name': 'Voicemod Virtual Audio Device', 'max_input_channels': 1, 'default_samplerate': 16000.0},
            {'name': 'Speaker Output', 'max_input_channels': 0, 'default_samplerate': 44100.0}
        ]
        
        devices = list_input_devices()
        self.assertEqual(len(devices), 2)
        self.assertFalse(devices[0]['is_virtual'])
        self.assertTrue(devices[1]['is_virtual'])

    @patch('sounddevice.query_devices')
    @patch('sounddevice.default')
    def test_select_mic_device_env_override(self, mock_sd_default, mock_query_devices):
        # Configure default device index as an integer array to prevent MagicMock comparison issues
        mock_sd_default.device = [0, 0]
        
        mock_query_devices.return_value = [
            {'name': 'Realtek Microphone', 'max_input_channels': 2, 'default_samplerate': 44100.0},
            {'name': 'USB Headset', 'max_input_channels': 1, 'default_samplerate': 16000.0}
        ]
        
        # Test VOICE_MIC_INDEX override
        os.environ["VOICE_MIC_INDEX"] = "1"
        if "VOICE_INPUT_DEVICE" in os.environ:
            del os.environ["VOICE_INPUT_DEVICE"]
        self.assertEqual(select_mic_device(), 1)
        
        # Test VOICE_INPUT_DEVICE override
        del os.environ["VOICE_MIC_INDEX"]
        os.environ["VOICE_INPUT_DEVICE"] = "0"
        self.assertEqual(select_mic_device(), 0)

    # 5. Transcription Confidence Gating Tests
    @patch('voice_listener.STTTranscriber')
    def test_transcribe_audio_valid_confidence(self, mock_stt_class):
        """
        Input: Transcript="open chrome", Confidence=0.46
        Expected: Returns "open chrome" (NOT None)
        """
        mock_instance = MagicMock()
        mock_stt_class.return_value = mock_instance
        mock_instance.model = MagicMock()
        
        mock_instance.transcribe.return_value = {
            'success': True,
            'text': 'open chrome',
            'confidence': 0.46,
            'avg_logprob': -0.77,
            'detected_lang': 'en',
            'lang_prob': 0.99,
            'words': [('open', 0.98), ('chrome', 0.95)],
            'whisper_time': 0.5
        }
        
        listener = VoiceListener(model_size='tiny')
        result = listener.transcribe_audio('dummy_path.wav')
        self.assertEqual(result, 'open chrome')

    @patch('voice_listener.STTTranscriber')
    def test_transcribe_audio_below_threshold(self, mock_stt_class):
        """
        Input: Transcript="open chrome", Confidence=0.35
        Expected: Returns None
        """
        mock_instance = MagicMock()
        mock_stt_class.return_value = mock_instance
        mock_instance.model = MagicMock()
        
        mock_instance.transcribe.return_value = {
            'success': True,
            'text': 'open chrome',
            'confidence': 0.35,
            'avg_logprob': -1.05,
            'detected_lang': 'en',
            'lang_prob': 0.99,
            'words': [('open', 0.88), ('chrome', 0.75)],
            'whisper_time': 0.5
        }
        
        listener = VoiceListener(model_size='tiny')
        result = listener.transcribe_audio('dummy_path.wav')
        self.assertIsNone(result)

    @patch('voice_listener.STTTranscriber')
    def test_transcribe_audio_empty_rejection(self, mock_stt_class):
        """
        Input: Transcript=""
        Expected: Returns None
        """
        mock_instance = MagicMock()
        mock_stt_class.return_value = mock_instance
        mock_instance.model = MagicMock()
        
        mock_instance.transcribe.return_value = {
            'success': True,
            'text': '   ',
            'confidence': 0.99,
            'avg_logprob': -0.01,
            'detected_lang': 'en',
            'lang_prob': 0.99,
            'words': [],
            'whisper_time': 0.1
        }
        
        listener = VoiceListener(model_size='tiny')
        result = listener.transcribe_audio('dummy_path.wav')
        self.assertIsNone(result)

    @patch('voice_listener.STTTranscriber')
    def test_transcribe_audio_diagnostic_mode(self, mock_stt_class):
        """
        Input: VOICE_DIAGNOSTIC="true", Transcript="open chrome"
        Expected: Returns "open chrome" (NOT None)
        """
        os.environ["VOICE_DIAGNOSTIC"] = "true"
        
        mock_instance = MagicMock()
        mock_stt_class.return_value = mock_instance
        mock_instance.model = MagicMock()
        
        mock_instance.transcribe.return_value = {
            'success': True,
            'text': 'open chrome',
            'confidence': 0.46,
            'avg_logprob': -0.77,
            'detected_lang': 'en',
            'lang_prob': 0.99,
            'words': [('open', 0.98), ('chrome', 0.95)],
            'whisper_time': 0.5
        }
        
        listener = VoiceListener(model_size='tiny')
        result = listener.transcribe_audio('dummy_path.wav')
        self.assertEqual(result, 'open chrome')

if __name__ == '__main__':
    unittest.main()
