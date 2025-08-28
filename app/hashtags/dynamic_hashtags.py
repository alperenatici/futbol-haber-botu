"""Dynamic hashtag generation based on news content."""

import re
from typing import List, Set, Dict, Any
from app.utils.logging import get_logger
from app.extractors.entity_extractor import entity_extractor

logger = get_logger(__name__)


class DynamicHashtagGenerator:
    """Generate relevant hashtags based on news content."""
    
    def __init__(self):
        # Turkish team hashtags
        self.team_hashtags = {
            'galatasaray': ['#Galatasaray', '#GS', '#CimBom'],
            'fenerbahçe': ['#Fenerbahçe', '#FB', '#SarıLacivert'],
            'beşiktaş': ['#Beşiktaş', '#BJK', '#KartalYuvası'],
            'trabzonspor': ['#Trabzonspor', '#TS', '#BorMav'],
            'başakşehir': ['#Başakşehir', '#IBFK'],
            'antalyaspor': ['#Antalyaspor'],
            'kayserispor': ['#Kayserispor'],
            'sivasspor': ['#Sivasspor'],
            'alanyaspor': ['#Alanyaspor'],
            'gaziantep fk': ['#GaziantepFK'],
            'konyaspor': ['#Konyaspor'],
            'kasımpaşa': ['#Kasımpaşa'],
            'fatih karagümrük': ['#FatihKaragümrük'],
            'adana demirspor': ['#AdanaDemirspor'],
            'hatayspor': ['#Hatayspor'],
            'ankaragücü': ['#Ankaragücü'],
            'istanbulspor': ['#İstanbulspor'],
            'pendikspor': ['#Pendikspor']
        }
        
        # International team hashtags
        self.international_hashtags = {
            'real madrid': ['#RealMadrid', '#HalaMadrid'],
            'barcelona': ['#Barcelona', '#FCB', '#Barça'],
            'manchester united': ['#ManUtd', '#MUFC'],
            'manchester city': ['#ManCity', '#MCFC'],
            'liverpool': ['#Liverpool', '#LFC', '#YNWA'],
            'chelsea': ['#Chelsea', '#CFC'],
            'arsenal': ['#Arsenal', '#AFC', '#Gunners'],
            'tottenham': ['#Tottenham', '#THFC', '#Spurs'],
            'juventus': ['#Juventus', '#Juve'],
            'milan': ['#ACMilan', '#Milan'],
            'inter': ['#Inter', '#InterMilan'],
            'bayern munich': ['#BayernMunich', '#FCBayern'],
            'borussia dortmund': ['#BVB', '#Dortmund'],
            'psg': ['#PSG', '#ParisSaintGermain'],
            'atletico madrid': ['#AtleticoMadrid', '#Atleti']
        }
        
        # Competition hashtags
        self.competition_hashtags = {
            'süper lig': ['#SüperLig', '#TürkiyeSüperLigi'],
            'champions league': ['#ChampionsLeague', '#UCL'],
            'europa league': ['#EuropaLeague', '#UEL'],
            'conference league': ['#ConferenceLeague', '#UECL'],
            'premier league': ['#PremierLeague', '#PL'],
            'la liga': ['#LaLiga'],
            'serie a': ['#SerieA'],
            'bundesliga': ['#Bundesliga'],
            'ligue 1': ['#Ligue1'],
            'türkiye kupası': ['#TürkiyeKupası'],
            'world cup': ['#WorldCup', '#FIFAWorldCup'],
            'euro 2024': ['#EURO2024'],
            'nations league': ['#NationsLeague']
        }
        
        # Player position hashtags
        self.position_hashtags = {
            'kaleci': ['#Kaleci', '#Goalkeeper'],
            'defans': ['#Defans', '#Defence'],
            'orta saha': ['#OrtaSaha', '#Midfield'],
            'forvet': ['#Forvet', '#Striker'],
            'kanat': ['#Kanat', '#Winger']
        }
        
        # Transfer hashtags
        self.transfer_hashtags = ['#Transfer', '#Transferler', '#YeniTransfer']
        
        # General football hashtags
        self.general_hashtags = ['#Futbol', '#Football', '#Soccer', '#Spor']
        
        # News type hashtags
        self.news_type_hashtags = {
            'transfer': ['#Transfer', '#TransferHaberi'],
            'injury': ['#Sakatlık', '#InjuryNews'],
            'match': ['#Maç', '#MatchDay'],
            'goal': ['#Gol', '#Goal'],
            'official': ['#Resmi', '#Official'],
            'rumor': ['#Söylenti', '#Rumor']
        }
    
    def extract_hashtags_from_entities(self, entities: List[Dict[str, Any]]) -> Set[str]:
        """Extract hashtags based on identified entities."""
        hashtags = set()
        
        for entity in entities:
            entity_name = entity['name'].lower()
            entity_type = entity['type']
            original_name = entity['name']
            
            # Team hashtags
            if entity_type in ['turkish_team', 'international_team']:
                if entity_name in self.team_hashtags:
                    hashtags.update(self.team_hashtags[entity_name])
                elif entity_name in self.international_hashtags:
                    hashtags.update(self.international_hashtags[entity_name])
                else:
                    # Create hashtag from team name
                    clean_name = re.sub(r'[^\w\s]', '', original_name)
                    clean_name = ''.join(word.capitalize() for word in clean_name.split())
                    if len(clean_name) > 2:
                        hashtags.add(f"#{clean_name}")
            
            # Competition hashtags
            elif entity_type == 'competition':
                if entity_name in self.competition_hashtags:
                    hashtags.update(self.competition_hashtags[entity_name])
                else:
                    # Create hashtag from competition name
                    clean_name = re.sub(r'[^\w\s]', '', original_name)
                    clean_name = ''.join(word.capitalize() for word in clean_name.split())
                    if len(clean_name) > 2:
                        hashtags.add(f"#{clean_name}")
            
            # Player hashtags (use full player name as hashtag)
            elif entity_type in ['turkish_player', 'international_player']:
                # Use full player name for hashtag
                clean_name = re.sub(r'[^\w\s]', '', original_name)
                clean_name = ''.join(word.capitalize() for word in clean_name.split())
                if len(clean_name) > 2 and len(clean_name) < 20:  # Reasonable length
                    hashtags.add(f"#{clean_name}")
            
            # Coach/Manager hashtags
            elif entity_type in ['coach', 'manager']:
                # Use full coach name for hashtag
                clean_name = re.sub(r'[^\w\s]', '', original_name)
                clean_name = ''.join(word.capitalize() for word in clean_name.split())
                if len(clean_name) > 2 and len(clean_name) < 20:
                    hashtags.add(f"#{clean_name}")
        
        return hashtags
    
    def extract_hashtags_from_content(self, title: str, summary: str) -> Set[str]:
        """Extract hashtags based on content keywords."""
        hashtags = set()
        text = f"{title} {summary}".lower()
        
        # Transfer related - Turkish keywords
        transfer_keywords = ['transfer', 'imza', 'anlaşma', 'bonservis', 'kiralık', 'geliyor', 'gidiyor', 'ayrıldı', 'katıldı']
        if any(keyword in text for keyword in transfer_keywords):
            hashtags.add('#Transfer')
        
        # Match related - Turkish keywords  
        match_keywords = ['maç', 'karşılaşma', 'müsabaka', 'gol', 'skor', 'beraberlik', 'galibiyeti', 'mağlubiyeti']
        if any(keyword in text for keyword in match_keywords):
            hashtags.add('#Maç')
        
        # Injury related - Turkish keywords
        injury_keywords = ['sakatlık', 'yaralandı', 'ameliyat', 'tedavi', 'sakatlandı', 'yaralı']
        if any(keyword in text for keyword in injury_keywords):
            hashtags.add('#Sakatlık')
        
        # Coach related - Turkish keywords
        coach_keywords = ['teknik direktör', 'antrenör', 'hoca', 'istifa', 'görevden', 'atandı']
        if any(keyword in text for keyword in coach_keywords):
            hashtags.add('#TeknikDirektör')
        
        # Competition detection - more specific
        if 'şampiyonlar ligi' in text or 'champions league' in text:
            hashtags.add('#ChampionsLeague')
        elif 'europa league' in text or 'avrupa ligi' in text:
            hashtags.add('#EuropaLeague')
        elif 'süper lig' in text:
            hashtags.add('#SüperLig')
        elif 'türkiye kupası' in text:
            hashtags.add('#TürkiyeKupası')
        
        return hashtags
    
    def generate_hashtags(self, title: str, summary: str, 
                         base_hashtags: List[str] = None, 
                         max_hashtags: int = 8) -> List[str]:
        """Generate dynamic hashtags for news content."""
        try:
            # Extract entities
            entities = entity_extractor.extract_entities(f"{title} {summary}")
            
            # Get hashtags from entities
            entity_hashtags = self.extract_hashtags_from_entities(entities)
            
            # Get hashtags from content
            content_hashtags = self.extract_hashtags_from_content(title, summary)
            
            # Combine all hashtags
            all_hashtags = set()
            
            # Add base hashtags
            if base_hashtags:
                all_hashtags.update(base_hashtags)
            
            # Add entity hashtags
            all_hashtags.update(entity_hashtags)
            
            # Add content hashtags
            all_hashtags.update(content_hashtags)
            
            # Always include general football hashtag
            all_hashtags.add('#Futbol')
            
            # Convert to list and limit
            hashtag_list = list(all_hashtags)[:max_hashtags]
            
            logger.info(f"Generated {len(hashtag_list)} hashtags: {hashtag_list}")
            return hashtag_list
            
        except Exception as e:
            logger.error(f"Error generating hashtags: {e}")
            # Fallback to base hashtags
            return base_hashtags or ['#Futbol']
    
    def get_trending_hashtags(self) -> List[str]:
        """Get currently trending football hashtags."""
        # This could be enhanced to fetch real trending data
        return [
            '#SüperLig', '#Galatasaray', '#Fenerbahçe', '#Beşiktaş',
            '#ChampionsLeague', '#Transfer', '#Futbol'
        ]


# Global hashtag generator instance
hashtag_generator = DynamicHashtagGenerator()
