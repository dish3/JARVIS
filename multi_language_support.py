#!/usr/bin/env python3
"""
JARVIS Multi-Language Support
Handles translation, language-specific responses, and localization
"""

import json
import sys
from typing import Dict, List, Optional
from datetime import datetime

try:
    from google.cloud import translate_v2
    GOOGLE_TRANSLATE_AVAILABLE = True
except ImportError:
    GOOGLE_TRANSLATE_AVAILABLE = False
    print("[Warning] Google Cloud Translation not available", file=sys.stderr)

try:
    from textblob import TextBlob
    TEXTBLOB_AVAILABLE = True
except ImportError:
    TEXTBLOB_AVAILABLE = False

# ═══════════════════════════════════════════════════════════════════════════
# LANGUAGE CONFIGURATIONS
# ═══════════════════════════════════════════════════════════════════════════

LANGUAGE_CONFIGS = {
    'en': {
        'name': 'English',
        'native_name': 'English',
        'code': 'en',
        'locale': 'en_US',
        'direction': 'ltr',
        'greeting': 'Hello',
        'farewell': 'Goodbye',
    },
    'hi': {
        'name': 'Hindi',
        'native_name': 'हिन्दी',
        'code': 'hi',
        'locale': 'hi_IN',
        'direction': 'ltr',
        'greeting': 'नमस्ते',
        'farewell': 'अलविदा',
    },
    'es': {
        'name': 'Spanish',
        'native_name': 'Español',
        'code': 'es',
        'locale': 'es_ES',
        'direction': 'ltr',
        'greeting': 'Hola',
        'farewell': 'Adiós',
    },
    'fr': {
        'name': 'French',
        'native_name': 'Français',
        'code': 'fr',
        'locale': 'fr_FR',
        'direction': 'ltr',
        'greeting': 'Bonjour',
        'farewell': 'Au revoir',
    },
    'de': {
        'name': 'German',
        'native_name': 'Deutsch',
        'code': 'de',
        'locale': 'de_DE',
        'direction': 'ltr',
        'greeting': 'Hallo',
        'farewell': 'Auf Wiedersehen',
    },
    'it': {
        'name': 'Italian',
        'native_name': 'Italiano',
        'code': 'it',
        'locale': 'it_IT',
        'direction': 'ltr',
        'greeting': 'Ciao',
        'farewell': 'Arrivederci',
    },
    'pt': {
        'name': 'Portuguese',
        'native_name': 'Português',
        'code': 'pt',
        'locale': 'pt_BR',
        'direction': 'ltr',
        'greeting': 'Olá',
        'farewell': 'Adeus',
    },
    'ru': {
        'name': 'Russian',
        'native_name': 'Русский',
        'code': 'ru',
        'locale': 'ru_RU',
        'direction': 'ltr',
        'greeting': 'Привет',
        'farewell': 'До свидания',
    },
    'ja': {
        'name': 'Japanese',
        'native_name': '日本語',
        'code': 'ja',
        'locale': 'ja_JP',
        'direction': 'ltr',
        'greeting': 'こんにちは',
        'farewell': 'さようなら',
    },
    'zh': {
        'name': 'Chinese',
        'native_name': '中文',
        'code': 'zh',
        'locale': 'zh_CN',
        'direction': 'ltr',
        'greeting': '你好',
        'farewell': '再见',
    },
    'ko': {
        'name': 'Korean',
        'native_name': '한국어',
        'code': 'ko',
        'locale': 'ko_KR',
        'direction': 'ltr',
        'greeting': '안녕하세요',
        'farewell': '안녕히 가세요',
    },
    'ar': {
        'name': 'Arabic',
        'native_name': 'العربية',
        'code': 'ar',
        'locale': 'ar_SA',
        'direction': 'rtl',
        'greeting': 'مرحبا',
        'farewell': 'وداعا',
    },
}

# ═══════════════════════════════════════════════════════════════════════════
# LANGUAGE-SPECIFIC RESPONSES
# ═══════════════════════════════════════════════════════════════════════════

LOCALIZED_RESPONSES = {
    'en': {
        'greeting': ['Hello! How can I help you?', 'Hi there! What do you need?', 'Greetings! How may I assist?'],
        'farewell': ['Goodbye! Have a great day!', 'See you later!', 'Take care!'],
        'help': ['I\'m here to help!', 'How can I assist you?', 'What do you need?'],
        'error': ['I encountered an error.', 'Something went wrong.', 'I apologize for the issue.'],
        'success': ['Done!', 'Completed successfully!', 'All set!'],
    },
    'hi': {
        'greeting': ['नमस्ते! मैं आपकी कैसे मदद कर सकता हूँ?', 'हाय! आपको क्या चाहिए?', 'स्वागत है!'],
        'farewell': ['अलविदा! आपका दिन शुभ हो!', 'फिर मिलेंगे!', 'ध्यान रखें!'],
        'help': ['मैं आपकी मदद के लिए यहाँ हूँ!', 'मैं आपकी कैसे सहायता कर सकता हूँ?', 'आपको क्या चाहिए?'],
        'error': ['मुझे एक त्रुटि का सामना करना पड़ा।', 'कुछ गलत हुआ।', 'मुझे खेद है।'],
        'success': ['हो गया!', 'सफलतापूर्वक पूरा हुआ!', 'सब ठीक है!'],
    },
    'es': {
        'greeting': ['¡Hola! ¿Cómo puedo ayudarte?', '¡Hola! ¿Qué necesitas?', '¡Saludos!'],
        'farewell': ['¡Adiós! ¡Que tengas un gran día!', '¡Hasta luego!', '¡Cuídate!'],
        'help': ['¡Estoy aquí para ayudarte!', '¿Cómo puedo asistirte?', '¿Qué necesitas?'],
        'error': ['Encontré un error.', 'Algo salió mal.', 'Disculpa por el problema.'],
        'success': ['¡Hecho!', '¡Completado exitosamente!', '¡Todo listo!'],
    },
    'fr': {
        'greeting': ['Bonjour! Comment puis-je vous aider?', 'Salut! Que puis-je faire pour vous?', 'Bienvenue!'],
        'farewell': ['Au revoir! Bonne journée!', 'À bientôt!', 'Prenez soin de vous!'],
        'help': ['Je suis là pour vous aider!', 'Comment puis-je vous assister?', 'Que puis-je faire?'],
        'error': ['J\'ai rencontré une erreur.', 'Quelque chose s\'est mal passé.', 'Je m\'excuse pour le problème.'],
        'success': ['Fait!', 'Complété avec succès!', 'Tout est prêt!'],
    },
    'de': {
        'greeting': ['Hallo! Wie kann ich dir helfen?', 'Hallo! Was brauchst du?', 'Willkommen!'],
        'farewell': ['Auf Wiedersehen! Viel Erfolg!', 'Bis später!', 'Pass auf dich auf!'],
        'help': ['Ich bin hier, um dir zu helfen!', 'Wie kann ich dir helfen?', 'Was brauchst du?'],
        'error': ['Ich bin auf einen Fehler gestoßen.', 'Etwas ist schief gelaufen.', 'Entschuldigung für das Problem.'],
        'success': ['Fertig!', 'Erfolgreich abgeschlossen!', 'Alles erledigt!'],
    },
    'ja': {
        'greeting': ['こんにちは！どのようにお手伝いできますか？', 'やあ！何が必要ですか？', 'ようこそ！'],
        'farewell': ['さようなら！良い一日を！', 'また後で！', 'お気をつけて！'],
        'help': ['お手伝いします！', 'どのようにお手伝いできますか？', '何が必要ですか？'],
        'error': ['エラーが発生しました。', '何か問題が発生しました。', '申し訳ありません。'],
        'success': ['完了！', '正常に完了しました！', 'すべて準備完了！'],
    },
    'zh': {
        'greeting': ['你好！我能帮你什么？', '嗨！你需要什么？', '欢迎！'],
        'farewell': ['再见！祝你有美好的一天！', '待会见！', '照顾好自己！'],
        'help': ['我在这里帮助你！', '我能帮你什么？', '你需要什么？'],
        'error': ['我遇到了一个错误。', '出了点问题。', '对不起。'],
        'success': ['完成！', '成功完成！', '一切就绪！'],
    },
}

# ═══════════════════════════════════════════════════════════════════════════
# TRANSLATOR
# ═══════════════════════════════════════════════════════════════════════════

class Translator:
    """Handles text translation between languages"""
    
    def __init__(self):
        self.client = None
        if GOOGLE_TRANSLATE_AVAILABLE:
            try:
                self.client = translate_v2.Client()
            except Exception as e:
                print(f"[Translator] Could not initialize Google Translate: {e}", file=sys.stderr)
    
    def translate(self, text: str, source_lang: str = 'en', target_lang: str = 'en') -> Dict:
        """Translate text from source to target language"""
        if source_lang == target_lang:
            return {
                'success': True,
                'original_text': text,
                'translated_text': text,
                'source_language': source_lang,
                'target_language': target_lang,
                'method': 'no_translation_needed'
            }
        
        # Try Google Translate
        if self.client:
            try:
                result = self.client.translate_text(
                    text,
                    source_language=source_lang,
                    target_language=target_lang
                )
                return {
                    'success': True,
                    'original_text': text,
                    'translated_text': result['translatedText'],
                    'source_language': source_lang,
                    'target_language': target_lang,
                    'method': 'google_translate'
                }
            except Exception as e:
                print(f"[Translator] Google Translate error: {e}", file=sys.stderr)
        
        # Try TextBlob
        if TEXTBLOB_AVAILABLE:
            try:
                blob = TextBlob(text)
                translated = blob.translate(from_lang=source_lang, to_lang=target_lang)
                return {
                    'success': True,
                    'original_text': text,
                    'translated_text': str(translated),
                    'source_language': source_lang,
                    'target_language': target_lang,
                    'method': 'textblob'
                }
            except Exception as e:
                print(f"[Translator] TextBlob translation error: {e}", file=sys.stderr)
        
        # Fallback
        return {
            'success': False,
            'original_text': text,
            'translated_text': text,
            'source_language': source_lang,
            'target_language': target_lang,
            'method': 'none',
            'error': 'No translation service available'
        }

# ═══════════════════════════════════════════════════════════════════════════
# LANGUAGE MANAGER
# ═══════════════════════════════════════════════════════════════════════════

class LanguageManager:
    """Manages language settings and localization"""
    
    def __init__(self, default_language: str = 'en'):
        self.current_language = default_language
        self.translator = Translator()
        self.supported_languages = list(LANGUAGE_CONFIGS.keys())
    
    def set_language(self, language_code: str) -> Dict:
        """Set current language"""
        if language_code not in LANGUAGE_CONFIGS:
            return {
                'success': False,
                'error': f'Language {language_code} not supported',
                'supported_languages': self.supported_languages
            }
        
        self.current_language = language_code
        return {
            'success': True,
            'current_language': language_code,
            'language_name': LANGUAGE_CONFIGS[language_code]['name'],
            'native_name': LANGUAGE_CONFIGS[language_code]['native_name']
        }
    
    def get_language_info(self, language_code: str = None) -> Dict:
        """Get information about a language"""
        lang = language_code or self.current_language
        if lang not in LANGUAGE_CONFIGS:
            return {'success': False, 'error': f'Language {lang} not found'}
        
        return {
            'success': True,
            'language': LANGUAGE_CONFIGS[lang]
        }
    
    def get_localized_response(self, response_type: str, language_code: str = None) -> str:
        """Get localized response"""
        lang = language_code or self.current_language
        
        if lang not in LOCALIZED_RESPONSES:
            lang = 'en'  # Fallback to English
        
        responses = LOCALIZED_RESPONSES[lang].get(response_type, [])
        if not responses:
            return LOCALIZED_RESPONSES['en'].get(response_type, ['Response not available'])[0]
        
        import random
        return random.choice(responses)
    
    def list_supported_languages(self) -> Dict:
        """List all supported languages"""
        languages = []
        for code, config in LANGUAGE_CONFIGS.items():
            languages.append({
                'code': code,
                'name': config['name'],
                'native_name': config['native_name'],
                'locale': config['locale'],
                'direction': config['direction']
            })
        
        return {
            'success': True,
            'total_languages': len(languages),
            'languages': languages
        }

# ═══════════════════════════════════════════════════════════════════════════
# LOCALIZATION ENGINE
# ═══════════════════════════════════════════════════════════════════════════

class LocalizationEngine:
    """Handles complete localization of responses"""
    
    def __init__(self, language: str = 'en'):
        self.language_manager = LanguageManager(language)
        self.translator = Translator()
    
    def localize_response(self, response: str, target_language: str = None) -> Dict:
        """Localize a response to target language"""
        lang = target_language or self.language_manager.current_language
        
        if lang == 'en':
            return {
                'success': True,
                'original_response': response,
                'localized_response': response,
                'language': lang,
                'method': 'no_translation_needed'
            }
        
        translation = self.translator.translate(response, 'en', lang)
        return {
            'success': translation['success'],
            'original_response': response,
            'localized_response': translation['translated_text'],
            'language': lang,
            'method': translation['method']
        }
    
    def get_localized_greeting(self, language: str = None) -> str:
        """Get localized greeting"""
        return self.language_manager.get_localized_response('greeting', language)
    
    def get_localized_farewell(self, language: str = None) -> str:
        """Get localized farewell"""
        return self.language_manager.get_localized_response('farewell', language)
    
    def get_localized_help(self, language: str = None) -> str:
        """Get localized help message"""
        return self.language_manager.get_localized_response('help', language)

# ═══════════════════════════════════════════════════════════════════════════
# CLI INTERFACE
# ═══════════════════════════════════════════════════════════════════════════

def main():
    """Main CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description='JARVIS Multi-Language Support')
    parser.add_argument('--translate', help='Translate text')
    parser.add_argument('--from-lang', default='en', help='Source language')
    parser.add_argument('--to-lang', default='es', help='Target language')
    parser.add_argument('--list-languages', action='store_true', help='List supported languages')
    parser.add_argument('--get-greeting', help='Get greeting in language')
    parser.add_argument('--get-farewell', help='Get farewell in language')
    
    args = parser.parse_args()
    
    if args.list_languages:
        manager = LanguageManager()
        result = manager.list_supported_languages()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.translate:
        translator = Translator()
        result = translator.translate(args.translate, args.from_lang, args.to_lang)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.get_greeting:
        engine = LocalizationEngine(args.get_greeting)
        greeting = engine.get_localized_greeting()
        print(greeting)
    
    elif args.get_farewell:
        engine = LocalizationEngine(args.get_farewell)
        farewell = engine.get_localized_farewell()
        print(farewell)
    
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
