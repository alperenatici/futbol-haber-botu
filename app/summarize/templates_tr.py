"""Turkish text templates for news formatting."""

import random
from typing import List, Dict, Any
from datetime import datetime

from app.utils.logging import get_logger
from app.utils.text import extract_domain, format_hashtags
from app.classify.rumor_official import NewsType
from app.config import settings

logger = get_logger(__name__)


class TurkishTemplates:
    """Turkish templates for news formatting."""
    
    def __init__(self):
        # Template patterns for different news types
        self.transfer_templates = [
            "{kulup}, {oyuncu} transferini {durum}. {detay}",
            "{oyuncu} için {kulup} cephesinden {gelisme}. {detay}",
            "{kulup} {oyuncu} ile {islem}. {detay}",
            "{oyuncu} {kulup}'a {durum}. {detay}"
        ]
        
        self.injury_templates = [
            "{oyuncu} {sakatlik} yaşadı. {detay}",
            "{kulup}'tan {oyuncu} için sakatlık açıklaması. {detay}",
            "{oyuncu}'nun {sakatlik} durumu açıklandı. {detay}"
        ]
        
        self.match_templates = [
            "{takim1} - {takim2} maçında {gelisme}. {detay}",
            "{lig} maçında {gelisme}. {detay}",
            "{takim} {sonuc} ile {durum}. {detay}"
        ]
        
        self.general_templates = [
            "{baslik}. {detay}",
            "{gelisme} açıklandı. {detay}",
            "{konu} hakkında {gelisme}. {detay}"
        ]
        
        # Status indicators
        self.status_words = {
            'confirmed': ['açıkladı', 'duyurdu', 'onayladı', 'resmen'],
            'rumor': ['iddia ediliyor', 'konuşuluyor', 'söylentiler var'],
            'negotiating': ['görüşüyor', 'müzakere ediyor', 'pazarlık yapıyor'],
            'completed': ['tamamlandı', 'kesinleşti', 'imzalandı']
        }
        
        # Time expressions
        self.time_expressions = [
            "Son dakika:", "Güncel:", "Az önce:", "Bugün:", "Bu sabah:"
        ]
    
    def extract_entities(self, title: str, summary: str) -> Dict[str, str]:
        """Extract entities from title and summary."""
        text = f"{title} {summary}".lower()
        
        # Simple entity extraction (can be improved)
        entities = {
            'kulup': '',
            'oyuncu': '',
            'gelisme': '',
            'detay': summary[:100] + '...' if len(summary) > 100 else summary
        }
        
        # Look for club names (basic patterns)
        clubs = [
            'galatasaray', 'fenerbahçe', 'beşiktaş', 'trabzonspor',
            'barcelona', 'real madrid', 'manchester', 'liverpool',
            'chelsea', 'arsenal', 'juventus', 'milan', 'bayern'
        ]
        
        for club in clubs:
            if club in text:
                entities['kulup'] = club.title()
                break
        
        return entities
    
    def format_with_template(self, title: str, summary: str, 
                           news_type: NewsType) -> str:
        """Format news using appropriate template."""
        entities = self.extract_entities(title, summary)
        
        # Choose template based on content
        if any(word in title.lower() for word in ['transfer', 'imza', 'anlaşma']):
            template = random.choice(self.transfer_templates)
        elif any(word in title.lower() for word in ['sakatlık', 'yaralandı', 'ameliyat']):
            template = random.choice(self.injury_templates)
        elif any(word in title.lower() for word in ['maç', 'gol', 'skor']):
            template = random.choice(self.match_templates)
        else:
            template = random.choice(self.general_templates)
        
        try:
            # Try to format with entities
            formatted = template.format(**entities)
        except KeyError:
            # Fallback to simple format
            formatted = f"{title}. {summary[:100]}..."
        
        return formatted
    
    def add_classification_badge(self, text: str, news_type: NewsType) -> str:
        """Add classification badge to text."""
        config = settings.config.post
        
        if news_type == NewsType.OFFICIAL:
            return f"{config.official_badge}: {text}"
        elif news_type == NewsType.RUMOR:
            return f"{config.rumor_badge}: {text}"
        
        return text
    
    def add_source_footer(self, text: str, source_url: str) -> str:
        """Add source footer to text."""
        domain = extract_domain(source_url)
        footer = settings.config.post.footer.format(source=domain)
        return f"{text}\n\n{footer}"
    
    def add_hashtags(self, text: str, custom_hashtags: List[str] = None) -> str:
        """Add hashtags to text."""
        hashtags = custom_hashtags or settings.config.post.hashtags
        hashtag_str = format_hashtags(hashtags)
        
        if hashtag_str:
            return f"{text} {hashtag_str}"
        
        return text
    
    def format_post(self, title: str, summary: str, source_url: str,
                   news_type: NewsType, max_length: int = 280) -> str:
        """Format complete social media post."""
        # Start with template formatting
        formatted_text = self.format_with_template(title, summary, news_type)
        
        # Add classification badge
        formatted_text = self.add_classification_badge(formatted_text, news_type)
        
        # Add source
        formatted_text = self.add_source_footer(formatted_text, source_url)
        
        # Add hashtags
        formatted_text = self.add_hashtags(formatted_text)
        
        # Ensure it fits within character limit
        if len(formatted_text) > max_length:
            # Try shorter version
            short_text = f"{title[:100]}..."
            short_text = self.add_classification_badge(short_text, news_type)
            short_text = self.add_source_footer(short_text, source_url)
            short_text = self.add_hashtags(short_text)
            
            if len(short_text) <= max_length:
                formatted_text = short_text
            else:
                # Final fallback - just title + source
                domain = extract_domain(source_url)
                formatted_text = f"{title[:200]}... Kaynak: {domain}"
        
        return formatted_text
    
    def create_variations(self, title: str, summary: str, 
                         count: int = 3) -> List[str]:
        """Create multiple variations of the same news."""
        variations = []
        
        for _ in range(count):
            # Use different templates
            entities = self.extract_entities(title, summary)
            template = random.choice(self.general_templates)
            
            try:
                variation = template.format(**entities)
                variations.append(variation)
            except KeyError:
                variations.append(f"{title}. {summary[:50]}...")
        
        return variations


# Global templates instance
templates = TurkishTemplates()
