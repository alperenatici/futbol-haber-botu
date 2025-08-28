"""Text translation utilities for Turkish news bot."""

import re
from typing import Optional, Dict, Any
from langdetect import detect, LangDetectError

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
    
    def translate_text(self, text: str) -> str:
        """Translate English text to Turkish using word mappings."""
        if not self.needs_translation(text):
            return text
            
        logger.info(f"Translating text: {text[:50]}...")
        
        # Clean text
        cleaned_text = clean_text(text)
        
        # Split into words while preserving punctuation
        words = re.findall(r'\b\w+\b|\W+', cleaned_text)
        
        translated_words = []
        for word in words:
            if re.match(r'\w+', word):  # It's a word
                translated = self.translate_word(word)
                translated_words.append(translated)
            else:  # It's punctuation/whitespace
                translated_words.append(word)
        
        result = ''.join(translated_words)
        
        # Clean up extra spaces
        result = re.sub(r'\s+', ' ', result.strip())
        
        # Remove empty translations (like 'the' -> '')
        result = re.sub(r'\s+', ' ', result)
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
        """Translate news summary to Turkish."""
        if not summary:
            return summary
            
        # First check if translation is needed  
        if not self.needs_translation(summary):
            return summary
            
        # Split into sentences for better translation
        sentences = re.split(r'[.!?]+', summary)
        translated_sentences = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence:
                translated = self.translate_text(sentence)
                if translated and translated != sentence:
                    translated_sentences.append(translated)
                else:
                    translated_sentences.append(sentence)
        
        result = '. '.join(translated_sentences)
        if result and not result.endswith('.'):
            result += '.'
            
        return result


# Global translator instance
translator = TurkishTranslator()
