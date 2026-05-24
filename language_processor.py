#!/usr/bin/env python3
"""
JARVIS Language Processing Engine
Handles NLP, language detection, multi-language support, and advanced text processing
"""

import json
import sys
import os
from typing import Dict, List, Tuple, Optional
import re
from datetime import datetime

# NLP Libraries
try:
    import nltk
    from nltk.tokenize import word_tokenize, sent_tokenize
    from nltk.corpus import stopwords
    from nltk.sentiment import SentimentIntensityAnalyzer
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
    nltk.download('vader_lexicon', quiet=True)
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False
    print("[Warning] NLTK not available. Install with: pip install nltk", file=sys.stderr)

try:
    from textblob import TextBlob
    TEXTBLOB_AVAILABLE = True
except ImportError:
    TEXTBLOB_AVAILABLE = False
    print("[Warning] TextBlob not available. Install with: pip install textblob", file=sys.stderr)

try:
    from langdetect import detect, detect_langs
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False
    print("[Warning] langdetect not available. Install with: pip install langdetect", file=sys.stderr)

try:
    import spacy
    try:
        nlp = spacy.load("en_core_web_sm")
        SPACY_AVAILABLE = True
    except OSError:
        print("[Warning] spaCy model not found. Install with: python -m spacy download en_core_web_sm", file=sys.stderr)
        SPACY_AVAILABLE = False
except ImportError:
    SPACY_AVAILABLE = False
    print("[Warning] spaCy not available. Install with: pip install spacy", file=sys.stderr)

# ═══════════════════════════════════════════════════════════════════════════
# LANGUAGE DETECTION
# ═══════════════════════════════════════════════════════════════════════════

class LanguageDetector:
    """Detects the language of input text"""
    
    LANGUAGE_MAP = {
        'en': 'English',
        'hi': 'Hindi',
        'es': 'Spanish',
        'fr': 'French',
        'de': 'German',
        'it': 'Italian',
        'pt': 'Portuguese',
        'ru': 'Russian',
        'ja': 'Japanese',
        'zh-cn': 'Chinese (Simplified)',
        'zh-tw': 'Chinese (Traditional)',
        'ko': 'Korean',
        'ar': 'Arabic',
        'tr': 'Turkish',
    }
    
    @staticmethod
    def detect_language(text: str) -> Dict:
        """Detect language of text"""
        if not text or len(text.strip()) < 2:
            return {'language': 'en', 'language_name': 'English', 'confidence': 0.0}
        
        # Try langdetect first (most accurate)
        if LANGDETECT_AVAILABLE:
            try:
                lang_code = detect(text)
                langs = detect_langs(text)
                confidence = max([l.prob for l in langs]) if langs else 0.0
                language_name = LanguageDetector.LANGUAGE_MAP.get(lang_code, lang_code)
                return {
                    'language': lang_code,
                    'language_name': language_name,
                    'confidence': confidence
                }
            except Exception as e:
                print(f"[LanguageDetector] Error: {e}", file=sys.stderr)
        
        # Fallback: Simple heuristic
        return {'language': 'en', 'language_name': 'English', 'confidence': 0.5}
    
    @staticmethod
    def is_english(text: str) -> bool:
        """Check if text is primarily English"""
        result = LanguageDetector.detect_language(text)
        return result['language'] == 'en'

# ═══════════════════════════════════════════════════════════════════════════
# SENTIMENT ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════

class SentimentAnalyzer:
    """Analyzes sentiment of text"""
    
    def __init__(self):
        self.sia = SentimentIntensityAnalyzer() if NLTK_AVAILABLE else None
    
    def analyze(self, text: str) -> Dict:
        """Analyze sentiment of text"""
        if not text:
            return {'sentiment': 'neutral', 'score': 0.0, 'positive': 0.0, 'negative': 0.0, 'neutral': 1.0}
        
        # Use NLTK VADER
        if self.sia:
            scores = self.sia.polarity_scores(text)
            sentiment = 'positive' if scores['compound'] > 0.05 else 'negative' if scores['compound'] < -0.05 else 'neutral'
            return {
                'sentiment': sentiment,
                'score': scores['compound'],
                'positive': scores['pos'],
                'negative': scores['neg'],
                'neutral': scores['neu']
            }
        
        # Fallback: Simple keyword matching
        positive_words = ['good', 'great', 'amazing', 'awesome', 'excellent', 'love', 'happy', 'wonderful']
        negative_words = ['bad', 'terrible', 'awful', 'hate', 'sad', 'angry', 'horrible', 'worst']
        
        text_lower = text.lower()
        pos_count = sum(1 for word in positive_words if word in text_lower)
        neg_count = sum(1 for word in negative_words if word in text_lower)
        
        if pos_count > neg_count:
            sentiment = 'positive'
        elif neg_count > pos_count:
            sentiment = 'negative'
        else:
            sentiment = 'neutral'
        
        return {
            'sentiment': sentiment,
            'score': (pos_count - neg_count) / max(pos_count + neg_count, 1),
            'positive': pos_count / max(pos_count + neg_count, 1) if (pos_count + neg_count) > 0 else 0.0,
            'negative': neg_count / max(pos_count + neg_count, 1) if (pos_count + neg_count) > 0 else 0.0,
            'neutral': 1.0 if (pos_count + neg_count) == 0 else 0.0
        }

# ═══════════════════════════════════════════════════════════════════════════
# TEXT PROCESSING
# ═══════════════════════════════════════════════════════════════════════════

class TextProcessor:
    """Processes and analyzes text"""
    
    @staticmethod
    def tokenize(text: str) -> Dict:
        """Tokenize text into words and sentences"""
        if not text:
            return {'words': [], 'sentences': [], 'word_count': 0, 'sentence_count': 0}
        
        if NLTK_AVAILABLE:
            try:
                words = word_tokenize(text)
                sentences = sent_tokenize(text)
                return {
                    'words': words,
                    'sentences': sentences,
                    'word_count': len(words),
                    'sentence_count': len(sentences)
                }
            except Exception as e:
                print(f"[TextProcessor] Tokenization error: {e}", file=sys.stderr)
        
        # Fallback
        words = text.split()
        sentences = text.split('.')
        return {
            'words': words,
            'sentences': [s.strip() for s in sentences if s.strip()],
            'word_count': len(words),
            'sentence_count': len([s for s in sentences if s.strip()])
        }
    
    @staticmethod
    def extract_entities(text: str) -> Dict:
        """Extract named entities from text"""
        if not SPACY_AVAILABLE:
            return {'entities': [], 'entity_count': 0}
        
        try:
            doc = nlp(text)
            entities = [
                {
                    'text': ent.text,
                    'label': ent.label_,
                    'start': ent.start_char,
                    'end': ent.end_char
                }
                for ent in doc.ents
            ]
            return {'entities': entities, 'entity_count': len(entities)}
        except Exception as e:
            print(f"[TextProcessor] Entity extraction error: {e}", file=sys.stderr)
            return {'entities': [], 'entity_count': 0}
    
    @staticmethod
    def extract_keywords(text: str, top_n: int = 5) -> List[str]:
        """Extract keywords from text"""
        if not text:
            return []
        
        if TEXTBLOB_AVAILABLE:
            try:
                blob = TextBlob(text)
                # Get noun phrases
                keywords = list(blob.noun_phrases)[:top_n]
                return keywords
            except Exception as e:
                print(f"[TextProcessor] Keyword extraction error: {e}", file=sys.stderr)
        
        # Fallback: Simple word frequency
        words = text.lower().split()
        if NLTK_AVAILABLE:
            try:
                stop_words = set(stopwords.words('english'))
                words = [w for w in words if w not in stop_words and len(w) > 3]
            except:
                pass
        
        from collections import Counter
        word_freq = Counter(words)
        return [word for word, _ in word_freq.most_common(top_n)]
    
    @staticmethod
    def correct_spelling(text: str) -> str:
        """Correct spelling in text"""
        if not TEXTBLOB_AVAILABLE:
            return text
        
        try:
            blob = TextBlob(text)
            return str(blob.correct())
        except Exception as e:
            print(f"[TextProcessor] Spelling correction error: {e}", file=sys.stderr)
            return text
    
    @staticmethod
    def get_text_stats(text: str) -> Dict:
        """Get comprehensive text statistics"""
        if not text:
            return {
                'character_count': 0,
                'word_count': 0,
                'sentence_count': 0,
                'avg_word_length': 0.0,
                'avg_sentence_length': 0.0,
                'reading_time_seconds': 0
            }
        
        tokenized = TextProcessor.tokenize(text)
        words = tokenized['words']
        sentences = tokenized['sentences']
        
        char_count = len(text)
        word_count = len(words)
        sentence_count = len(sentences)
        
        avg_word_length = sum(len(w) for w in words) / max(word_count, 1)
        avg_sentence_length = word_count / max(sentence_count, 1)
        reading_time = word_count / 200  # Average reading speed: 200 words/minute
        
        return {
            'character_count': char_count,
            'word_count': word_count,
            'sentence_count': sentence_count,
            'avg_word_length': round(avg_word_length, 2),
            'avg_sentence_length': round(avg_sentence_length, 2),
            'reading_time_seconds': round(reading_time * 60, 0)
        }

# ═══════════════════════════════════════════════════════════════════════════
# INTENT RECOGNITION
# ═══════════════════════════════════════════════════════════════════════════

class IntentRecognizer:
    """Recognizes user intent from text"""
    
    INTENTS = {
        'greeting': ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening', 'howdy', 'greetings'],
        'farewell': ['bye', 'goodbye', 'see you', 'farewell', 'goodnight', 'good night', 'exit', 'quit'],
        'question': ['what', 'when', 'where', 'why', 'how', 'who', 'which', 'can you', 'could you', 'would you'],
        'command': ['open', 'close', 'start', 'stop', 'launch', 'run', 'execute', 'do', 'make', 'create'],
        'affirmation': ['yes', 'yeah', 'sure', 'okay', 'ok', 'alright', 'agreed', 'confirmed'],
        'negation': ['no', 'nope', 'nah', 'never', 'not', 'don\'t', 'doesn\'t', 'won\'t', 'can\'t'],
        'help': ['help', 'assist', 'support', 'guide', 'explain', 'teach', 'show me', 'how to'],
        'gratitude': ['thank', 'thanks', 'appreciate', 'grateful', 'good job', 'well done', 'nice work'],
        'complaint': ['bad', 'terrible', 'awful', 'hate', 'angry', 'frustrated', 'upset', 'problem', 'issue', 'error'],
        'praise': ['good', 'great', 'amazing', 'awesome', 'excellent', 'love', 'wonderful', 'fantastic'],
    }
    
    @staticmethod
    def recognize_intent(text: str) -> Dict:
        """Recognize intent from text"""
        if not text:
            return {'intent': 'unknown', 'confidence': 0.0, 'matched_keywords': []}
        
        text_lower = text.lower()
        intent_scores = {}
        matched_keywords = {}
        
        for intent, keywords in IntentRecognizer.INTENTS.items():
            matches = [kw for kw in keywords if kw in text_lower]
            if matches:
                intent_scores[intent] = len(matches)
                matched_keywords[intent] = matches
        
        if not intent_scores:
            return {'intent': 'unknown', 'confidence': 0.0, 'matched_keywords': []}
        
        best_intent = max(intent_scores, key=intent_scores.get)
        confidence = intent_scores[best_intent] / len(text_lower.split())
        
        return {
            'intent': best_intent,
            'confidence': min(confidence, 1.0),
            'matched_keywords': matched_keywords.get(best_intent, []),
            'all_intents': intent_scores
        }

# ═══════════════════════════════════════════════════════════════════════════
# RESPONSE GENERATOR
# ═══════════════════════════════════════════════════════════════════════════

class ResponseGenerator:
    """Generates contextual responses based on analysis"""
    
    RESPONSE_TEMPLATES = {
        'greeting': [
            "Hello! How can I assist you today?",
            "Greetings! What can I do for you?",
            "Welcome! How may I help?",
        ],
        'farewell': [
            "Goodbye! Have a great day!",
            "See you later! Take care!",
            "Farewell! Until next time!",
        ],
        'question': [
            "That's a great question! Let me help you with that.",
            "I'd be happy to answer that for you.",
            "Let me look into that for you.",
        ],
        'command': [
            "I'll take care of that right away.",
            "Executing your request now.",
            "Let me do that for you.",
        ],
        'help': [
            "I'm here to help! What do you need?",
            "I'd be happy to assist you.",
            "Let me guide you through this.",
        ],
        'gratitude': [
            "You're welcome! Happy to help.",
            "My pleasure! Anything else?",
            "Glad I could assist!",
        ],
        'praise': [
            "Thank you! I appreciate that.",
            "That's kind of you to say!",
            "I'm glad you're satisfied!",
        ],
        'complaint': [
            "I apologize for that. Let me help fix it.",
            "I understand your frustration. Let's resolve this.",
            "I'm sorry about that. How can I make it better?",
        ],
    }
    
    @staticmethod
    def generate_response(text: str, intent: str, sentiment: str) -> str:
        """Generate response based on intent and sentiment"""
        import random
        
        # Select template based on intent
        templates = ResponseGenerator.RESPONSE_TEMPLATES.get(intent, ResponseGenerator.RESPONSE_TEMPLATES['question'])
        response = random.choice(templates)
        
        # Adjust based on sentiment
        if sentiment == 'negative':
            response = "I understand. " + response
        elif sentiment == 'positive':
            response = "Great! " + response
        
        return response

# ═══════════════════════════════════════════════════════════════════════════
# MAIN LANGUAGE PROCESSOR
# ═══════════════════════════════════════════════════════════════════════════

class LanguageProcessor:
    """Main language processing engine"""
    
    def __init__(self):
        self.language_detector = LanguageDetector()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.text_processor = TextProcessor()
        self.intent_recognizer = IntentRecognizer()
        self.response_generator = ResponseGenerator()
    
    def process(self, text: str) -> Dict:
        """Process text and return comprehensive analysis"""
        if not text or not isinstance(text, str):
            return {
                'success': False,
                'error': 'Invalid input text',
                'text': text
            }
        
        try:
            # Language detection
            language_info = self.language_detector.detect_language(text)
            
            # Sentiment analysis
            sentiment_info = self.sentiment_analyzer.analyze(text)
            
            # Text processing
            text_stats = self.text_processor.get_text_stats(text)
            keywords = self.text_processor.extract_keywords(text)
            entities = self.text_processor.extract_entities(text)
            
            # Intent recognition
            intent_info = self.intent_recognizer.recognize_intent(text)
            
            # Response generation
            response = self.response_generator.generate_response(
                text,
                intent_info['intent'],
                sentiment_info['sentiment']
            )
            
            return {
                'success': True,
                'text': text,
                'language': language_info,
                'sentiment': sentiment_info,
                'intent': intent_info,
                'text_stats': text_stats,
                'keywords': keywords,
                'entities': entities['entities'],
                'response': response,
                'timestamp': datetime.now().isoformat()
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'text': text
            }

# ═══════════════════════════════════════════════════════════════════════════
# CLI INTERFACE
# ═══════════════════════════════════════════════════════════════════════════

def main():
    """Main CLI interface"""
    processor = LanguageProcessor()
    
    if len(sys.argv) > 1:
        # Process command line argument
        text = ' '.join(sys.argv[1:])
        result = processor.process(text)
        print(json.dumps(result, indent=2))
    else:
        # Interactive mode
        print("JARVIS Language Processor - Interactive Mode")
        print("Type 'quit' to exit\n")
        
        while True:
            try:
                text = input("Enter text: ").strip()
                if text.lower() == 'quit':
                    break
                
                result = processor.process(text)
                print(json.dumps(result, indent=2))
                print()
            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                print(f"Error: {e}")

if __name__ == '__main__':
    main()
