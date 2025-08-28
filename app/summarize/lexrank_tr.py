"""Turkish text summarization using LexRank algorithm."""

import nltk
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lex_rank import LexRankSummarizer
from sumy.nlp.stemmers import Stemmer
from sumy.utils import get_stop_words
from pathlib import Path
from typing import List, Optional

from app.config import settings
from app.utils.logging import get_logger
from app.utils.text import clean_text, is_turkish_text
from app.connectors.rss import NewsItem

logger = get_logger(__name__)


class TurkishSummarizer:
    """Turkish text summarizer using LexRank."""
    
    def __init__(self):
        self.language = "english"  # Use English as fallback
        try:
            self.stemmer = Stemmer("turkish")
        except:
            logger.warning("Turkish stemmer not available, using English")
            self.stemmer = Stemmer("english")
        
        self.summarizer = LexRankSummarizer(self.stemmer)
        
        # Load Turkish stopwords
        self.stopwords = self._load_turkish_stopwords()
        self.summarizer.stop_words = self.stopwords
        
        # Download required NLTK data
        self._ensure_nltk_data()
    
    def _ensure_nltk_data(self):
        """Ensure required NLTK data is downloaded."""
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            logger.info("Downloading NLTK punkt tokenizer...")
            nltk.download('punkt', quiet=True)
    
    def _load_turkish_stopwords(self) -> set:
        """Load Turkish stopwords from file."""
        stopwords_file = settings.data_dir / "stopwords_tr.txt"
        
        if stopwords_file.exists():
            with open(stopwords_file, 'r', encoding='utf-8') as f:
                stopwords = {line.strip().lower() for line in f if line.strip()}
            logger.debug(f"Loaded {len(stopwords)} Turkish stopwords")
            return stopwords
        else:
            # Fallback to sumy's Turkish stopwords
            logger.warning("Turkish stopwords file not found, using default")
            return get_stop_words(self.language)
    
    def summarize_text(self, text: str, sentence_count: int = 2) -> str:
        """Summarize text to specified number of sentences."""
        if not text or len(text.strip()) < 50:
            return text
        
        try:
            # Clean text
            cleaned_text = clean_text(text)
            
            # Check if text is Turkish
            if not is_turkish_text(cleaned_text):
                logger.debug("Text doesn't appear to be Turkish, using first sentences")
                sentences = cleaned_text.split('. ')
                return '. '.join(sentences[:sentence_count]) + '.'
            
            # Parse text
            parser = PlaintextParser.from_string(cleaned_text, Tokenizer(self.language))
            
            # Generate summary
            summary_sentences = self.summarizer(parser.document, sentence_count)
            
            # Join sentences
            summary = ' '.join(str(sentence) for sentence in summary_sentences)
            
            return clean_text(summary)
            
        except Exception as e:
            logger.error(f"Error summarizing text: {e}")
            # Fallback: return first few sentences
            sentences = text.split('. ')
            return '. '.join(sentences[:sentence_count]) + '.'
    
    def create_short_title(self, title: str, max_words: int = 8) -> str:
        """Create a short title from original title."""
        if not title:
            return ""
        
        # Clean and normalize
        title = clean_text(title)
        
        # Remove common separators and split
        title = title.replace(' - ', ' ').replace(' | ', ' ').replace(' / ', ' ')
        words = title.split()
        
        # If already short enough, return as is
        if len(words) <= max_words:
            return title
        
        # Try to find a natural break point
        for i in range(min(max_words, len(words))):
            if words[i].endswith((':', '-', '–')):
                return ' '.join(words[:i])
        
        # Otherwise, just truncate
        return ' '.join(words[:max_words])
    
    def summarize_news_item(self, item: NewsItem) -> dict:
        """Summarize a news item and return structured data."""
        # Create short title
        short_title = self.create_short_title(item.title)
        
        # Summarize content
        content_to_summarize = item.raw_content or item.summary
        if content_to_summarize and len(content_to_summarize) > 200:
            summary = self.summarize_text(content_to_summarize, sentence_count=2)
        else:
            summary = clean_text(item.summary)
        
        # Ensure summary is not too long
        if len(summary) > 300:
            sentences = summary.split('. ')
            summary = sentences[0] + '.'
        
        return {
            'original_title': item.title,
            'short_title': short_title,
            'summary': summary,
            'word_count': len(summary.split()),
            'char_count': len(summary)
        }
    
    def batch_summarize(self, items: List[NewsItem]) -> List[dict]:
        """Summarize multiple news items."""
        results = []
        
        for item in items:
            try:
                summary_data = self.summarize_news_item(item)
                results.append({
                    'item': item,
                    **summary_data
                })
            except Exception as e:
                logger.error(f"Error summarizing item {item.id}: {e}")
                # Add fallback data
                results.append({
                    'item': item,
                    'original_title': item.title,
                    'short_title': item.title[:50] + '...' if len(item.title) > 50 else item.title,
                    'summary': item.summary[:200] + '...' if len(item.summary) > 200 else item.summary,
                    'word_count': len(item.summary.split()),
                    'char_count': len(item.summary)
                })
        
        logger.info(f"Summarized {len(results)} news items")
        return results


# Global summarizer instance
summarizer = TurkishSummarizer()
