"""Text translation utilities for Turkish news bot."""

import re
import requests
from typing import Optional, Dict, Any
try:
    from langdetect import detect
    from langdetect.lang_detect_exception import LangDetectException as LangDetectError
except ImportError:
    # Fallback if langdetect is not available
    def detect(text):
        return 'unknown'
    
    class LangDetectError(Exception):
        pass

from app.utils.logging import get_logger
from app.utils.text import clean_text

logger = get_logger(__name__)


class TurkishTranslator:
    """Simple Turkish translator using basic word mappings and rules."""
    
    def __init__(self):
        # Common football/sports terms translation dictionary
        self.translation_dict = {
            # Football terms
            'football': 'futbol',
            'soccer': 'futbol', 
            'player': 'oyuncu',
            'team': 'takım',
            'club': 'kulüp',
            'match': 'maç',
            'game': 'oyun',
            'goal': 'gol',
            'transfer': 'transfer',
            'contract': 'sözleşme',
            'manager': 'teknik direktör',
            'coach': 'antrenör',
            'stadium': 'stadyum',
            'league': 'lig',
            'season': 'sezon',
            'injury': 'sakatlık',
            'injured': 'sakatlandı',
            'signed': 'imzaladı',
            'signs': 'imzalıyor',
            'joins': 'katılıyor',
            'joined': 'katıldı',
            'leaves': 'ayrılıyor',
            'left': 'ayrıldı',
            'confirms': 'doğruluyor',
            'confirmed': 'doğrulandı',
            'announces': 'duyuruyor',
            'announced': 'duyuruldu',
            'official': 'resmi',
            'rumor': 'söylenti',
            'rumour': 'söylenti',
            'reports': 'raporlar',
            'according to': 'göre',
            'sources': 'kaynaklar',
            'exclusive': 'özel',
            'breaking': 'son dakika',
            'update': 'güncelleme',
            'latest': 'son',
            'news': 'haber',
            'football news': 'futbol haberi',
            'transfer news': 'transfer haberi',
            
            # Common words
            'the': '',
            'a': 'bir',
            'an': 'bir',
            'and': 've',
            'or': 'veya',
            'but': 'ama',
            'with': 'ile',
            'from': 'den',
            'to': 'ya',
            'in': 'de',
            'on': 'da',
            'at': 'de',
            'for': 'için',
            'by': 'tarafından',
            'is': '',
            'are': '',
            'was': 'idi',
            'were': 'idiler',
            'will': 'olacak',
            'has': 'var',
            'have': 'var',
            'had': 'vardı',
            'new': 'yeni',
            'old': 'eski',
            'big': 'büyük',
            'small': 'küçük',
            'good': 'iyi',
            'bad': 'kötü',
            'first': 'ilk',
            'last': 'son',
            'next': 'sonraki',
            'this': 'bu',
            'that': 'şu',
            'year': 'yıl',
            'month': 'ay',
            'week': 'hafta',
            'day': 'gün',
            'today': 'bugün',
            'yesterday': 'dün',
            'tomorrow': 'yarın',
            'now': 'şimdi',
            'after': 'sonra',
            'before': 'önce',
            'during': 'sırasında',
            'million': 'milyon',
            'euros': 'euro',
            'pounds': 'pound',
            'dollars': 'dolar'
        }
        
        # Team name mappings
        self.team_names = {
            'manchester united': 'Manchester United',
            'manchester city': 'Manchester City', 
            'liverpool': 'Liverpool',
            'chelsea': 'Chelsea',
            'arsenal': 'Arsenal',
            'tottenham': 'Tottenham',
            'real madrid': 'Real Madrid',
            'barcelona': 'Barcelona',
            'atletico madrid': 'Atletico Madrid',
            'bayern munich': 'Bayern Münih',
            'borussia dortmund': 'Borussia Dortmund',
            'paris saint-germain': 'Paris Saint-Germain',
            'psg': 'PSG',
            'juventus': 'Juventus',
            'ac milan': 'AC Milan',
            'inter milan': 'Inter Milan',
            'galatasaray': 'Galatasaray',
            'fenerbahce': 'Fenerbahçe',
            'besiktas': 'Beşiktaş',
            'trabzonspor': 'Trabzonspor'
        }
    
    def detect_language(self, text: str) -> str:
        """Detect the language of the text."""
        try:
            # Clean text for better detection
            cleaned = re.sub(r'[^\w\s]', ' ', text)
            cleaned = re.sub(r'\s+', ' ', cleaned.strip())
            
            if len(cleaned) < 10:
                return 'unknown'
                
            lang = detect(cleaned)
            return lang
        except LangDetectError:
            return 'unknown'
    
    def needs_translation(self, text: str) -> bool:
        """Check if text needs translation to Turkish."""
        if not text or len(text.strip()) < 10:
            return False
            
        # Check if already contains Turkish characters
        turkish_chars = set('çğıöşüÇĞIİÖŞÜ')
        if any(char in text for char in turkish_chars):
            return False
            
        # Detect language
        lang = self.detect_language(text)
        return lang == 'en'
    
    def translate_word(self, word: str) -> str:
        """Translate a single word."""
        word_lower = word.lower()
        
        # Check team names first
        for eng_team, tr_team in self.team_names.items():
            if eng_team in word_lower:
                return word.replace(eng_team, tr_team)
        
        # Check translation dictionary
        if word_lower in self.translation_dict:
            translation = self.translation_dict[word_lower]
            # Preserve capitalization
            if word.isupper():
                return translation.upper()
            elif word.istitle():
                return translation.capitalize()
            else:
                return translation
        
        return word
    
    def translate_with_mymemory(self, text: str, source_lang: str = 'en', target_lang: str = 'tr') -> Optional[str]:
        """Translate text using MyMemory free translation API with rate limit handling."""
        try:
            # Clean and prepare text for translation
            clean_text_input = text.strip()
            if len(clean_text_input) < 5:
                return None
                
            # MyMemory API endpoint
            url = "https://api.mymemory.translated.net/get"
            params = {
                'q': clean_text_input[:500],  # Reduced limit to avoid rate limits
                'langpair': f'{source_lang}|{target_lang}',
                'de': 'futbolhaber@example.com',  # Optional email for better service
                'mt': '1'  # Machine translation flag for better quality
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Check for rate limit
            if data.get('responseStatus') == 403 or 'RATE_LIMIT_EXCEEDED' in str(data):
                logger.warning("MyMemory API rate limit exceeded, falling back to local translation")
                return None
                
            if data.get('responseStatus') == 200:
                translated = data.get('responseData', {}).get('translatedText', '')
                
                # Quality checks for translation
                if translated and len(translated.strip()) > 5:
                    # Check if translation is meaningful (not just copied)
                    if translated.lower() != text.lower():
                        # Additional quality check - ensure Turkish characters or meaningful change
                        turkish_chars = set('çğıöşüÇĞIİÖŞÜ')
                        has_turkish = any(char in translated for char in turkish_chars)
                        word_ratio = len(translated.split()) / max(len(text.split()), 1)
                        
                        # Accept if has Turkish chars or reasonable word count ratio
                        if has_turkish or (0.5 <= word_ratio <= 2.0):
                            logger.info(f"MyMemory translation: {text[:30]} -> {translated[:30]}")
                            return translated.strip()
                    
        except requests.exceptions.RequestException as e:
            logger.warning(f"MyMemory API request failed: {e}")
        except Exception as e:
            logger.warning(f"MyMemory translation failed: {e}")
            
        return None

    def translate_text(self, text: str) -> str:
        """Translate English text to Turkish with improved quality and completeness."""
        if not self.needs_translation(text):
            return text
            
        logger.info(f"Translating text: {text[:50]}...")
        
        # Split long text into sentences for better translation
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        translated_sentences = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            # Try API translation first for each sentence
            api_translation = self.translate_with_mymemory(sentence)
            if api_translation:
                # Validate API translation quality
                cleaned = clean_text(api_translation)
                if len(cleaned) >= len(sentence) * 0.3:  # Ensure reasonable length
                    translated_sentences.append(cleaned)
                    continue
            
            # Fallback to word mapping translation for this sentence
            logger.info(f"Using fallback translation for: {sentence[:30]}...")
            
            # Clean text
            cleaned_text = clean_text(sentence)
            
            # Split into words while preserving punctuation
            words = re.findall(r'\b\w+\b|\W+', cleaned_text)
            
            translated_words = []
            for word in words:
                if re.match(r'\w+', word):  # It's a word
                    translated = self.translate_word(word)
                    translated_words.append(translated)
                else:  # It's punctuation/whitespace
                    translated_words.append(word)
            
            sentence_result = ''.join(translated_words)
            
            # Clean up extra spaces
            sentence_result = re.sub(r'\s+', ' ', sentence_result.strip())
            
            # Remove empty translations (like 'the' -> '')
            sentence_result = re.sub(r'\s+', ' ', sentence_result)
            sentence_result = re.sub(r'\s+([.,!?;:])', r'\1', sentence_result)
            
            if sentence_result.strip():
                translated_sentences.append(sentence_result)
        
        # Join sentences back together
        result = ' '.join(translated_sentences)
        
        # Final cleanup
        result = re.sub(r'\s+', ' ', result.strip())
        result = re.sub(r'\s+([.,!?;:])', r'\1', result)
        
        logger.info(f"Translation result: {result[:50]}...")
        return result
    
    def translate_title(self, title: str) -> str:
        """Translate news title to Turkish."""
        if not title:
            return title
            
        # First check if translation is needed
        if not self.needs_translation(title):
            return title
            
        # Translate
        translated = self.translate_text(title)
        
        # Ensure it's not too long
        if len(translated) > 100:
            words = translated.split()
            translated = ' '.join(words[:12]) + '...'
            
        return translated
    
    def translate_summary(self, summary: str) -> str:
        """Translate news summary to Turkish with improved sentence structure."""
        if not summary:
            return summary
            
        # First check if translation is needed  
        if not self.needs_translation(summary):
            return summary
            
        # Use the improved translate_text method
        translated = self.translate_text(summary)
        
        # Ensure proper sentence structure
        if translated:
            # Fix sentence endings
            translated = re.sub(r'\s*\.\s*\.+', '.', translated)  # Remove multiple dots
            translated = re.sub(r'([.!?])\s*([A-ZÜÇĞIÖŞ])', r'\1 \2', translated)  # Space after punctuation
            
            # Ensure it ends with proper punctuation
            if not re.search(r'[.!?]$', translated.strip()):
                translated = translated.strip() + '.'
                
        return translated


# Global translator instance
translator = TurkishTranslator()
