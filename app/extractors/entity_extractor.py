"""Extract entities (teams, players, coaches) from news content."""

import re
from typing import List, Dict, Set, Optional
from app.utils.logging import get_logger

logger = get_logger(__name__)


class EntityExtractor:
    """Extract football entities from news content."""
    
    def __init__(self):
        # Turkish teams
        self.turkish_teams = {
            'galatasaray': {'name': 'Galatasaray', 'hashtag': '#Galatasaray', 'color': '#FFA500'},
            'fenerbahçe': {'name': 'Fenerbahçe', 'hashtag': '#Fenerbahçe', 'color': '#004B9D'},
            'fenerbahce': {'name': 'Fenerbahçe', 'hashtag': '#Fenerbahçe', 'color': '#004B9D'},
            'beşiktaş': {'name': 'Beşiktaş', 'hashtag': '#Beşiktaş', 'color': '#000000'},
            'besiktas': {'name': 'Beşiktaş', 'hashtag': '#Beşiktaş', 'color': '#000000'},
            'trabzonspor': {'name': 'Trabzonspor', 'hashtag': '#Trabzonspor', 'color': '#8B0000'},
            'başakşehir': {'name': 'Başakşehir', 'hashtag': '#Başakşehir', 'color': '#FF6600'},
            'basaksehir': {'name': 'Başakşehir', 'hashtag': '#Başakşehir', 'color': '#FF6600'},
            'konyaspor': {'name': 'Konyaspor', 'hashtag': '#Konyaspor', 'color': '#008000'},
            'antalyaspor': {'name': 'Antalyaspor', 'hashtag': '#Antalyaspor', 'color': '#FF0000'},
            'sivasspor': {'name': 'Sivasspor', 'hashtag': '#Sivasspor', 'color': '#DC143C'},
            'kayserispor': {'name': 'Kayserispor', 'hashtag': '#Kayserispor', 'color': '#FFD700'},
            'alanyaspor': {'name': 'Alanyaspor', 'hashtag': '#Alanyaspor', 'color': '#FF8C00'},
            'hatayspor': {'name': 'Hatayspor', 'hashtag': '#Hatayspor', 'color': '#8B0000'},
            'kasımpaşa': {'name': 'Kasımpaşa', 'hashtag': '#Kasımpaşa', 'color': '#000080'},
            'kasimpasa': {'name': 'Kasımpaşa', 'hashtag': '#Kasımpaşa', 'color': '#000080'},
            'gaziantep fk': {'name': 'Gaziantep FK', 'hashtag': '#GaziantepFK', 'color': '#DC143C'},
            'adana demirspor': {'name': 'Adana Demirspor', 'hashtag': '#AdanaDemirspor', 'color': '#0066CC'},
            'ankaragücü': {'name': 'Ankaragücü', 'hashtag': '#Ankaragücü', 'color': '#FFD700'},
            'ankaragucu': {'name': 'Ankaragücü', 'hashtag': '#Ankaragücü', 'color': '#FFD700'}
        }
        
        # Turkish players
        self.turkish_players = {
            'hakan çalhanoğlu': {'name': 'Hakan Çalhanoğlu', 'hashtag': '#HakanÇalhanoğlu', 'team': 'Inter Milan'},
            'hakan calhanoglu': {'name': 'Hakan Çalhanoğlu', 'hashtag': '#HakanÇalhanoğlu', 'team': 'Inter Milan'},
            'burak yılmaz': {'name': 'Burak Yılmaz', 'hashtag': '#BurakYılmaz', 'team': 'Galatasaray'},
            'burak yilmaz': {'name': 'Burak Yılmaz', 'hashtag': '#BurakYılmaz', 'team': 'Galatasaray'},
            'yusuf yazıcı': {'name': 'Yusuf Yazıcı', 'hashtag': '#YusufYazıcı', 'team': 'Lille'},
            'yusuf yazici': {'name': 'Yusuf Yazıcı', 'hashtag': '#YusufYazıcı', 'team': 'Lille'},
            'cengiz ünder': {'name': 'Cengiz Ünder', 'hashtag': '#CengizÜnder', 'team': 'Fenerbahçe'},
            'cengiz under': {'name': 'Cengiz Ünder', 'hashtag': '#CengizÜnder', 'team': 'Fenerbahçe'},
            'merih demiral': {'name': 'Merih Demiral', 'hashtag': '#MerihDemiral', 'team': 'Al-Ahli'},
            'ozan kabak': {'name': 'Ozan Kabak', 'hashtag': '#OzanKabak', 'team': 'Hoffenheim'},
            'çağlar söyüncü': {'name': 'Çağlar Söyüncü', 'hashtag': '#ÇağlarSöyüncü', 'team': 'Leicester'},
            'caglar soyuncu': {'name': 'Çağlar Söyüncü', 'hashtag': '#ÇağlarSöyüncü', 'team': 'Leicester'},
            'orkun kökçü': {'name': 'Orkun Kökçü', 'hashtag': '#OrkunKökçü', 'team': 'Benfica'},
            'orkun kokcu': {'name': 'Orkun Kökçü', 'hashtag': '#OrkunKökçü', 'team': 'Benfica'},
            'kenan karaman': {'name': 'Kenan Karaman', 'hashtag': '#KenanKaraman', 'team': 'Schalke'},
            'ferdi kadıoğlu': {'name': 'Ferdi Kadıoğlu', 'hashtag': '#FerdiKadıoğlu', 'team': 'Fenerbahçe'},
            'ferdi kadioglu': {'name': 'Ferdi Kadıoğlu', 'hashtag': '#FerdiKadıoğlu', 'team': 'Fenerbahçe'},
            'yunus akgün': {'name': 'Yunus Akgün', 'hashtag': '#YunusAkgün', 'team': 'Galatasaray'},
            'yunus akgun': {'name': 'Yunus Akgün', 'hashtag': '#YunusAkgün', 'team': 'Galatasaray'},
            'kerem aktürkoğlu': {'name': 'Kerem Aktürkoğlu', 'hashtag': '#KeremAktürkoğlu', 'team': 'Galatasaray'},
            'kerem akturkoglu': {'name': 'Kerem Aktürkoğlu', 'hashtag': '#KeremAktürkoğlu', 'team': 'Galatasaray'},
            'arda güler': {'name': 'Arda Güler', 'hashtag': '#ArdaGüler', 'team': 'Real Madrid'},
            'arda guler': {'name': 'Arda Güler', 'hashtag': '#ArdaGüler', 'team': 'Real Madrid'},
            'salih özcan': {'name': 'Salih Özcan', 'hashtag': '#SalihÖzcan', 'team': 'Borussia Dortmund'},
            'salih ozcan': {'name': 'Salih Özcan', 'hashtag': '#SalihÖzcan', 'team': 'Borussia Dortmund'},
            'irfan can kahveci': {'name': 'İrfan Can Kahveci', 'hashtag': '#İrfanCanKahveci', 'team': 'Fenerbahçe'},
            'cenk tosun': {'name': 'Cenk Tosun', 'hashtag': '#CenkTosun', 'team': 'Beşiktaş'},
            'okay yokuşlu': {'name': 'Okay Yokuşlu', 'hashtag': '#OkayYokuşlu', 'team': 'West Bromwich'},
            'okay yokuslu': {'name': 'Okay Yokuşlu', 'hashtag': '#OkayYokuşlu', 'team': 'West Bromwich'},
            'kaan ayhan': {'name': 'Kaan Ayhan', 'hashtag': '#KaanAyhan', 'team': 'Galatasaray'},
            'zeki çelik': {'name': 'Zeki Çelik', 'hashtag': '#ZekiÇelik', 'team': 'Roma'},
            'zeki celik': {'name': 'Zeki Çelik', 'hashtag': '#ZekiÇelik', 'team': 'Roma'},
            'barış alper yılmaz': {'name': 'Barış Alper Yılmaz', 'hashtag': '#BarışAlperYılmaz', 'team': 'Galatasaray'},
            'baris alper yilmaz': {'name': 'Barış Alper Yılmaz', 'hashtag': '#BarışAlperYılmaz', 'team': 'Galatasaray'}
        }
        
        # Turkish coaches
        self.turkish_coaches = {
            'fatih terim': {'name': 'Fatih Terim', 'hashtag': '#FatihTerim'},
            'şenol güneş': {'name': 'Şenol Güneş', 'hashtag': '#ŞenolGüneş'},
            'senol gunes': {'name': 'Şenol Güneş', 'hashtag': '#ŞenolGüneş'},
            'ismail kartal': {'name': 'İsmail Kartal', 'hashtag': '#İsmailKartal'},
            'okan buruk': {'name': 'Okan Buruk', 'hashtag': '#OkanBuruk'},
            'valerien ismael': {'name': 'Valerien Ismael', 'hashtag': '#ValerienIsmael'},
            'fernando santos': {'name': 'Fernando Santos', 'hashtag': '#FernandoSantos'},
            'stefan kuntz': {'name': 'Stefan Kuntz', 'hashtag': '#StefanKuntz'},
            'vincenzo montella': {'name': 'Vincenzo Montella', 'hashtag': '#VincenzoMontella'}
        }
        
        # International teams
        self.international_teams = {
            'real madrid': {'name': 'Real Madrid', 'hashtag': '#RealMadrid'},
            'barcelona': {'name': 'Barcelona', 'hashtag': '#Barcelona'},
            'manchester united': {'name': 'Manchester United', 'hashtag': '#ManUtd'},
            'manchester city': {'name': 'Manchester City', 'hashtag': '#ManCity'},
            'liverpool': {'name': 'Liverpool', 'hashtag': '#Liverpool'},
            'chelsea': {'name': 'Chelsea', 'hashtag': '#Chelsea'},
            'arsenal': {'name': 'Arsenal', 'hashtag': '#Arsenal'},
            'tottenham': {'name': 'Tottenham', 'hashtag': '#Tottenham'},
            'bayern munich': {'name': 'Bayern Münih', 'hashtag': '#BayernMünih'},
            'borussia dortmund': {'name': 'Borussia Dortmund', 'hashtag': '#BVB'},
            'juventus': {'name': 'Juventus', 'hashtag': '#Juventus'},
            'ac milan': {'name': 'AC Milan', 'hashtag': '#ACMilan'},
            'inter milan': {'name': 'Inter Milan', 'hashtag': '#InterMilan'},
            'paris saint-germain': {'name': 'PSG', 'hashtag': '#PSG'},
            'psg': {'name': 'PSG', 'hashtag': '#PSG'},
            'atletico madrid': {'name': 'Atletico Madrid', 'hashtag': '#AtleticoMadrid'}
        }
    
    def extract_entities(self, text: str) -> Dict[str, List[Dict]]:
        """Extract all entities from text."""
        text_lower = text.lower()
        entities = {
            'teams': [],
            'players': [],
            'coaches': []
        }
        
        # Extract Turkish teams
        for key, info in self.turkish_teams.items():
            if key in text_lower:
                entities['teams'].append({
                    'name': info['name'],
                    'hashtag': info['hashtag'],
                    'type': 'turkish_team',
                    'color': info.get('color', '#000000')
                })
                logger.debug(f"Found Turkish team: {info['name']}")
        
        # Extract international teams
        for key, info in self.international_teams.items():
            if key in text_lower:
                entities['teams'].append({
                    'name': info['name'],
                    'hashtag': info['hashtag'],
                    'type': 'international_team'
                })
                logger.debug(f"Found international team: {info['name']}")
        
        # Extract Turkish players
        for key, info in self.turkish_players.items():
            if key in text_lower:
                entities['players'].append({
                    'name': info['name'],
                    'hashtag': info['hashtag'],
                    'team': info.get('team', ''),
                    'type': 'turkish_player'
                })
                logger.debug(f"Found Turkish player: {info['name']}")
        
        # Extract coaches
        for key, info in self.turkish_coaches.items():
            if key in text_lower:
                entities['coaches'].append({
                    'name': info['name'],
                    'hashtag': info['hashtag'],
                    'type': 'coach'
                })
                logger.debug(f"Found coach: {info['name']}")
        
        return entities
    
    def generate_hashtags(self, entities: Dict[str, List[Dict]], base_hashtags: List[str] = None) -> List[str]:
        """Generate hashtags based on extracted entities."""
        hashtags = set(base_hashtags or ['#futbol'])
        
        # Add entity-specific hashtags
        for entity_type, entity_list in entities.items():
            for entity in entity_list:
                hashtags.add(entity['hashtag'])
        
        # Add content-based hashtags
        if entities['teams']:
            if any(team['type'] == 'turkish_team' for team in entities['teams']):
                hashtags.add('#SüperLig')
        
        if entities['players']:
            hashtags.add('#transfer')
            if any(player['type'] == 'turkish_player' for player in entities['players']):
                hashtags.add('#MilliTakım')
        
        if entities['coaches']:
            hashtags.add('#teknikdirektör')
        
        # Limit to 5 hashtags to avoid spam
        return list(hashtags)[:5]
    
    def get_primary_entity(self, entities: Dict[str, List[Dict]]) -> Optional[Dict]:
        """Get the most important entity for image search."""
        # Priority: Turkish teams > Turkish players > International teams > Coaches
        
        if entities['teams']:
            # Prefer Turkish teams
            turkish_teams = [t for t in entities['teams'] if t['type'] == 'turkish_team']
            if turkish_teams:
                return turkish_teams[0]
            # Fallback to international teams
            return entities['teams'][0]
        
        if entities['players']:
            # Prefer Turkish players
            turkish_players = [p for p in entities['players'] if p['type'] == 'turkish_player']
            if turkish_players:
                return turkish_players[0]
        
        if entities['coaches']:
            return entities['coaches'][0]
        
        return None


# Global entity extractor instance
entity_extractor = EntityExtractor()
