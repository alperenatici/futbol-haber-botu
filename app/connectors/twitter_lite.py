"""
Lightweight Twitter connector with minimal API usage
"""
import logging
import time
from typing import List, Dict, Optional
from datetime import datetime, timedelta, timezone
import yaml
import random

logger = logging.getLogger(__name__)

class TwitterLiteConnector:
    """Minimal Twitter connector to avoid rate limits"""
    
    def __init__(self, config_path: str = None):
        self.config_path = config_path or "data/sources.yaml"
        self.accounts = []
        self.last_run = None
        
        self._load_config()
    
    def _load_config(self):
        """Load Twitter accounts from config"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                self.accounts = config.get('twitter_accounts', [])
                # Only use top 3 accounts to minimize API calls
                self.accounts = self.accounts[:3]
                logger.info(f"Loaded {len(self.accounts)} Twitter accounts (limited)")
        except Exception as e:
            logger.error(f"Failed to load Twitter config: {e}")
            self.accounts = []
    
    def get_mock_tweets(self) -> List[Dict]:
        """Generate mock tweets to avoid rate limits during development"""
        
        # Check if we ran recently (avoid too frequent calls)
        if self.last_run and (datetime.now() - self.last_run).seconds < 300:  # 5 minutes
            logger.info("Skipping tweet fetch - too recent")
            return []
        
        self.last_run = datetime.now()
        
        mock_tweets = [
            {
                'id': f"mock_{int(time.time())}_{random.randint(1000, 9999)}",
                'text': "Galatasaray'da yeni transfer hamlesi! Genç yıldız oyuncu ile görüşmeler başladı. #Galatasaray #Transfer",
                'created_at': datetime.now(timezone.utc),
                'username': 'futbolarena',
                'url': f"https://twitter.com/futbolarena/status/mock_{int(time.time())}",
                'metrics': {'like_count': 45, 'retweet_count': 12},
                'entities': {},
                'language': 'tr',
                'account_name': 'FutbolArena',
                'account_category': 'football',
                'account_language': 'tr'
            },
            {
                'id': f"mock_{int(time.time())}_{random.randint(1000, 9999)}_2",
                'text': "Fenerbahçe'de sakatlık şoku! Yıldız futbolcu 3 hafta sahalardan uzak kalacak. #Fenerbahçe #Sakatlık",
                'created_at': datetime.now(timezone.utc) - timedelta(minutes=30),
                'username': 'sporx',
                'url': f"https://twitter.com/sporx/status/mock_{int(time.time())}_2",
                'metrics': {'like_count': 67, 'retweet_count': 23},
                'entities': {},
                'language': 'tr',
                'account_name': 'Sporx',
                'account_category': 'sports',
                'account_language': 'tr'
            },
            {
                'id': f"mock_{int(time.time())}_{random.randint(1000, 9999)}_3",
                'text': "Manchester United are interested in signing the Turkish midfielder this summer. The player is valued at €25 million.",
                'created_at': datetime.now(timezone.utc) - timedelta(hours=1),
                'username': 'ntvspor',
                'url': f"https://twitter.com/ntvspor/status/mock_{int(time.time())}_3",
                'metrics': {'like_count': 89, 'retweet_count': 34},
                'entities': {},
                'language': 'en',
                'account_name': 'NTV Spor',
                'account_category': 'sports',
                'account_language': 'tr'
            }
        ]
        
        logger.info(f"Generated {len(mock_tweets)} mock tweets for testing")
        return mock_tweets
    
    def get_all_monitored_tweets(self, since_hours: int = 6) -> List[Dict]:
        """Get tweets - using mock data to avoid rate limits"""
        logger.info("Using mock tweets to avoid Twitter API rate limits")
        return self.get_mock_tweets()
    
    def filter_quality_tweets(self, tweets: List[Dict]) -> List[Dict]:
        """Filter tweets for quality and relevance"""
        filtered = []
        
        for tweet in tweets:
            text = tweet.get('text', '')
            
            # Skip very short tweets
            if len(text) < 30:
                continue
            
            # Skip tweets with too many mentions/hashtags
            if text.count('@') > 3 or text.count('#') > 5:
                continue
            
            # Must be sports related
            if not self.is_sports_related(tweet):
                continue
            
            # Skip retweets
            if text.startswith('RT @'):
                continue
            
            filtered.append(tweet)
        
        return filtered
    
    def is_sports_related(self, tweet: Dict) -> bool:
        """Check if tweet is sports/football related"""
        text = tweet.get('text', '').lower()
        
        # Turkish sports keywords
        sports_keywords = [
            'futbol', 'maç', 'gol', 'transfer', 'takım', 'oyuncu', 'antrenör',
            'galatasaray', 'fenerbahçe', 'beşiktaş', 'trabzonspor',
            'şampiyonlar ligi', 'süper lig', 'milli takım', 'fifa', 'uefa',
            'football', 'soccer', 'goal', 'player', 'team', 'coach', 'match',
            'sakatlık', 'manchester', 'midfielder'
        ]
        
        return any(keyword in text for keyword in sports_keywords)
