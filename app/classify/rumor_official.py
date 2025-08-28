"""Classification system for official vs rumor news."""

import re
from typing import Dict, List, Tuple
from enum import Enum

from app.utils.logging import get_logger
from app.utils.text import clean_text, extract_domain
from app.connectors.rss import NewsItem

logger = get_logger(__name__)


class NewsType(Enum):
    OFFICIAL = "official"
    RUMOR = "rumor"
    NEUTRAL = "neutral"


class NewsClassifier:
    """Rule-based classifier for official vs rumor news."""
    
    def __init__(self):
        # Official indicators (Turkish and English)
        self.official_keywords = {
            'tr': [
                'resmi', 'açıklama', 'duyurdu', 'açıkladı', 'onayladı', 
                'imzaladı', 'resmen', 'resmileşti', 'kesinleşti',
                'kulüp açıklaması', 'basın açıklaması', 'resmi sitesi'
            ],
            'en': [
                'confirmed', 'announced', 'official', 'statement', 
                'declares', 'signs', 'agreement', 'contract',
                'club confirms', 'officially', 'press release'
            ]
        }
        
        # Rumor indicators
        self.rumor_keywords = {
            'tr': [
                'iddia', 'söylenti', 'rivayet', 'dedikodu', 'konuşuluyor',
                'iddiaya göre', 'söylentilere göre', 'kaynaklara göre',
                'haberlere göre', 'duyumlara göre', 'kulislerde'
            ],
            'en': [
                'rumour', 'rumor', 'reportedly', 'allegedly', 'sources say',
                'according to sources', 'speculation', 'claims',
                'it is said', 'whispers', 'gossip', 'unconfirmed'
            ]
        }
        
        # Official domains (trusted sources)
        self.official_domains = {
            'uefa.com', 'fifa.com', 'tff.org',
            'galatasaray.org', 'fenerbahce.org', 'besiktas.com.tr',
            'trabzonspor.org.tr', 'bursaspor.org.tr',
            'realmadrid.com', 'fcbarcelona.com', 'manutd.com',
            'arsenal.com', 'chelseafc.com', 'liverpoolfc.com',
            'juventus.com', 'acmilan.com', 'inter.it',
            'fcbayern.com', 'bvb.de', 'psg.fr'
        }
        
        # Reliable news sources
        self.reliable_sources = {
            'bbc.co.uk', 'skysports.com', 'espn.com',
            'goal.com', 'transfermarkt.com', 'fanatik.com.tr',
            'sporx.com', 'ntv.com.tr', 'cnnturk.com'
        }
        
        # Tabloid/unreliable patterns
        self.tabloid_patterns = [
            r'exclusive.*transfer', r'shock.*move', r'sensational.*deal',
            r'bombshell.*news', r'insider.*reveals'
        ]
    
    def calculate_official_score(self, item: NewsItem) -> float:
        """Calculate official score for news item."""
        score = 0.0
        text = f"{item.title} {item.summary}".lower()
        domain = extract_domain(item.url)
        
        # Domain-based scoring
        if domain in self.official_domains:
            score += 0.8
        elif domain in self.reliable_sources:
            score += 0.4
        
        # Keyword-based scoring
        for lang in ['tr', 'en']:
            for keyword in self.official_keywords[lang]:
                if keyword in text:
                    score += 0.2
                    break  # Don't double count per language
        
        # Title patterns (official announcements often have formal structure)
        if re.search(r'(resmi|official).*(:|-)', item.title.lower()):
            score += 0.3
        
        # Press release patterns
        if any(pattern in text for pattern in ['basın açıklaması', 'press release', 'club statement']):
            score += 0.3
        
        return min(score, 1.0)  # Cap at 1.0
    
    def calculate_rumor_score(self, item: NewsItem) -> float:
        """Calculate rumor score for news item."""
        score = 0.0
        text = f"{item.title} {item.summary}".lower()
        
        # Keyword-based scoring
        for lang in ['tr', 'en']:
            for keyword in self.rumor_keywords[lang]:
                if keyword in text:
                    score += 0.3
        
        # Tabloid patterns
        for pattern in self.tabloid_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                score += 0.2
        
        # Question marks (often indicate uncertainty)
        if '?' in item.title:
            score += 0.1
        
        # Conditional language
        conditional_patterns = [
            r'could.*transfer', r'might.*sign', r'may.*move',
            r'olabilir', r'mümkün', r'ihtimal'
        ]
        for pattern in conditional_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                score += 0.2
                break
        
        return min(score, 1.0)  # Cap at 1.0
    
    def classify_news(self, item: NewsItem) -> Tuple[NewsType, float]:
        """Classify news item and return type with confidence score."""
        official_score = self.calculate_official_score(item)
        rumor_score = self.calculate_rumor_score(item)
        
        # Decision logic
        if official_score >= 0.6:
            return NewsType.OFFICIAL, official_score
        elif rumor_score >= 0.5:
            return NewsType.RUMOR, rumor_score
        elif official_score > rumor_score and official_score >= 0.3:
            return NewsType.OFFICIAL, official_score
        elif rumor_score > official_score and rumor_score >= 0.3:
            return NewsType.RUMOR, rumor_score
        else:
            return NewsType.NEUTRAL, max(official_score, rumor_score)
    
    def classify_batch(self, items: List[NewsItem]) -> List[Tuple[NewsItem, NewsType, float]]:
        """Classify multiple news items."""
        results = []
        
        for item in items:
            news_type, confidence = self.classify_news(item)
            results.append((item, news_type, confidence))
            
            logger.debug(f"Classified '{item.title}' as {news_type.value} (confidence: {confidence:.2f})")
        
        return results
    
    def get_classification_summary(self, items: List[NewsItem]) -> Dict[str, int]:
        """Get summary of classifications."""
        results = self.classify_batch(items)
        
        summary = {
            NewsType.OFFICIAL.value: 0,
            NewsType.RUMOR.value: 0,
            NewsType.NEUTRAL.value: 0
        }
        
        for _, news_type, _ in results:
            summary[news_type.value] += 1
        
        return summary


# Global classifier instance
classifier = NewsClassifier()
