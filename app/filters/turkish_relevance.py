"""Content filtering for Turkish football relevance."""

import re
from typing import List, Dict, Any, Optional
from app.utils.logging import get_logger
from app.connectors.rss import NewsItem

logger = get_logger(__name__)


class TurkishRelevanceFilter:
    """Filter news content for Turkish football relevance."""
    
    def __init__(self):
        # Turkish teams and players
        self.turkish_teams = {
            'galatasaray', 'fenerbahçe', 'fenerbahce', 'beşiktaş', 'besiktas', 
            'trabzonspor', 'başakşehir', 'basaksehir', 'konyaspor', 'antalyaspor',
            'gaziantep fk', 'sivasspor', 'kayserispor', 'alanyaspor', 'hatayspor',
            'kasımpaşa', 'kasimpasa', 'fatih karagümrük', 'fatih karagumruk',
            'giresunspor', 'adana demirspor', 'ankaragücü', 'ankaragucu',
            'ümraniyespor', 'umraniyespor', 'pendikspor', 'istanbulspor'
        }
        
        # Turkish players (major ones)
        self.turkish_players = {
            'hakan çalhanoğlu', 'hakan calhanoglu', 'burak yılmaz', 'burak yilmaz',
            'yusuf yazıcı', 'yusuf yazici', 'cengiz ünder', 'cengiz under',
            'merih demiral', 'ozan kabak', 'çağlar söyüncü', 'caglar soyuncu',
            'orkun kökçü', 'orkun kokcu', 'kenan karaman', 'abdülkerim bardakcı',
            'abdulkerim bardakci', 'ferdi kadıoğlu', 'ferdi kadioglu',
            'yunus akgün', 'yunus akgun', 'kerem aktürkoğlu', 'kerem akturkoglu',
            'baris alper yilmaz', 'barış alper yılmaz', 'arda güler', 'arda guler',
            'salih özcan', 'salih ozcan', 'irfan can kahveci', 'cenk tosun',
            'okay yokuşlu', 'okay yokuslu', 'kaan ayhan', 'zeki çelik', 'zeki celik'
        }
        
        # Turkish football keywords
        self.turkish_keywords = {
            'süper lig', 'super lig', 'türkiye', 'turkey', 'turkish', 'türk',
            'milli takım', 'milli takim', 'a milli', 'euro 2024', 'uefa',
            'türk futbolu', 'turk futbolu', 'tff', 'türkiye futbol federasyonu',
            'stefan kuntz', 'vincenzo montella', 'fatih terim', 'şenol güneş',
            'senol gunes', 'ismail kartal', 'fernando santos'
        }
        
        # International teams with Turkish interest
        self.relevant_international_teams = {
            'ac milan', 'inter milan', 'juventus', 'atalanta', 'roma', 'napoli',
            'real madrid', 'barcelona', 'atletico madrid', 'sevilla',
            'bayern munich', 'borussia dortmund', 'bayer leverkusen',
            'manchester united', 'liverpool', 'arsenal', 'chelsea',
            'tottenham', 'manchester city', 'newcastle', 'west ham',
            'leicester', 'brighton', 'fulham', 'crystal palace'
        }
        
        # Transfer-related keywords
        self.transfer_keywords = {
            'transfer', 'imza', 'imzaladı', 'imzalıyor', 'bonservis',
            'sözleşme', 'sozlesme', 'kiralık', 'kiralik', 'satın alma',
            'satin alma', 'teklif', 'görüşme', 'gorusme', 'anlaşma',
            'anlasma', 'resmi', 'official', 'confirmed', 'signs',
            'joins', 'moves to', 'agrees', 'deal'
        }
        
        # Injury/suspension keywords
        self.injury_keywords = {
            'sakatlık', 'sakatlik', 'yaralanma', 'injury', 'injured',
            'ameliyat', 'operation', 'surgery', 'cezalı', 'cezali',
            'suspended', 'suspension', 'kart', 'card', 'disqualified'
        }
        
        # Competition keywords
        self.competition_keywords = {
            'champions league', 'şampiyonlar ligi', 'sampiyonlar ligi',
            'europa league', 'avrupa ligi', 'conference league',
            'konferans ligi', 'world cup', 'dünya kupası', 'dunya kupasi',
            'euro', 'avrupa şampiyonası', 'avrupa sampiyonasi',
            'nations league', 'uluslar ligi', 'qualifying', 'eleme'
        }
    
    def calculate_relevance_score(self, item: NewsItem) -> float:
        """Calculate relevance score for Turkish football fans."""
        score = 0.0
        text = f"{item.title} {item.summary}".lower()
        
        # Turkish teams (highest priority)
        for team in self.turkish_teams:
            if team in text:
                score += 10.0
                logger.debug(f"Turkish team found: {team}")
        
        # Turkish players (high priority)
        for player in self.turkish_players:
            if player in text:
                score += 8.0
                logger.debug(f"Turkish player found: {player}")
        
        # Turkish football keywords
        for keyword in self.turkish_keywords:
            if keyword in text:
                score += 6.0
                logger.debug(f"Turkish keyword found: {keyword}")
        
        # Transfer news (medium-high priority)
        for keyword in self.transfer_keywords:
            if keyword in text:
                score += 4.0
                logger.debug(f"Transfer keyword found: {keyword}")
        
        # International teams with Turkish players
        for team in self.relevant_international_teams:
            if team in text:
                score += 2.0
                logger.debug(f"Relevant international team found: {team}")
        
        # Injury/suspension news
        for keyword in self.injury_keywords:
            if keyword in text:
                score += 3.0
                logger.debug(f"Injury keyword found: {keyword}")
        
        # Competition news
        for keyword in self.competition_keywords:
            if keyword in text:
                score += 2.0
                logger.debug(f"Competition keyword found: {keyword}")
        
        # Boost for Turkish sources
        if any(source in item.source.lower() for source in [
            'sabah', 'hurriyet', 'fanatik', 'sporx', 'ntvspor', 
            'trtspor', 'milliyet', 'haberturk', 'cnnturk', 'sozcu'
        ]):
            score += 3.0
            logger.debug(f"Turkish source bonus: {item.source}")
        
        # Penalty for irrelevant content
        irrelevant_keywords = {
            'american football', 'nfl', 'baseball', 'basketball', 'nba',
            'hockey', 'tennis', 'golf', 'cricket', 'rugby', 'volleyball',
            'formula 1', 'f1', 'motorsport', 'boxing', 'mma', 'wrestling'
        }
        
        for keyword in irrelevant_keywords:
            if keyword in text:
                score -= 5.0
                logger.debug(f"Irrelevant content penalty: {keyword}")
        
        return max(0.0, score)
    
    def is_relevant_for_turkish_audience(self, item: NewsItem, min_score: float = 2.0) -> bool:
        """Check if news item is relevant for Turkish football audience."""
        score = self.calculate_relevance_score(item)
        is_relevant = score >= min_score
        
        logger.debug(f"Relevance score for '{item.title[:50]}...': {score:.1f} (threshold: {min_score})")
        
        return is_relevant
    
    def filter_items(self, items: List[NewsItem], min_score: float = 2.0) -> List[NewsItem]:
        """Filter news items for Turkish relevance."""
        relevant_items = []
        
        for item in items:
            if self.is_relevant_for_turkish_audience(item, min_score):
                relevant_items.append(item)
            else:
                logger.debug(f"Filtered out irrelevant item: {item.title[:50]}...")
        
        logger.info(f"Filtered {len(items)} items to {len(relevant_items)} relevant items")
        return relevant_items


# Global filter instance
turkish_filter = TurkishRelevanceFilter()
