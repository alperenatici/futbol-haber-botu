"""
Twitter/X API connector for fetching tweets from specific accounts
"""
import tweepy
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import yaml
from pathlib import Path

logger = logging.getLogger(__name__)

class TwitterConnector:
    def __init__(self, config_path: str = None):
        """Initialize Twitter API connection"""
        self.config_path = config_path or "data/sources.yaml"
        self.api = None
        self.client = None
        self.accounts = []
        self.last_check = {}
        
        self._load_config()
        self._setup_api()
    
    def _load_config(self):
        """Load Twitter accounts from config"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                self.accounts = config.get('twitter_accounts', [])
                logger.info(f"Loaded {len(self.accounts)} Twitter accounts to monitor")
        except Exception as e:
            logger.error(f"Failed to load Twitter config: {e}")
            self.accounts = []
    
    def _setup_api(self):
        """Setup Twitter API v2 client"""
        try:
            import os
            
            # Twitter API v2 credentials
            bearer_token = os.getenv('X_BEARER_TOKEN')
            api_key = os.getenv('X_API_KEY')
            api_secret = os.getenv('X_API_SECRET')
            access_token = os.getenv('X_ACCESS_TOKEN')
            access_token_secret = os.getenv('X_ACCESS_TOKEN_SECRET')
            
            if not all([api_key, api_secret, access_token, access_token_secret]):
                logger.error("Missing Twitter API credentials")
                return
            
            # Setup API v1.1 for compatibility
            auth = tweepy.OAuthHandler(api_key, api_secret)
            auth.set_access_token(access_token, access_token_secret)
            self.api = tweepy.API(auth, wait_on_rate_limit=True)
            
            # Setup API v2 client
            self.client = tweepy.Client(
                bearer_token=bearer_token,
                consumer_key=api_key,
                consumer_secret=api_secret,
                access_token=access_token,
                access_token_secret=access_token_secret,
                wait_on_rate_limit=True
            )
            
            logger.info("Twitter API connection established")
            
        except Exception as e:
            logger.error(f"Failed to setup Twitter API: {e}")
    
    def get_user_tweets(self, username: str, count: int = 10, since_hours: int = 24) -> List[Dict]:
        """Get recent tweets from a specific user"""
        if not self.client:
            logger.error("Twitter client not initialized")
            return []
        
        try:
            # Calculate since_id based on last check
            since_time = datetime.utcnow() - timedelta(hours=since_hours)
            
            # Get user by username
            user = self.client.get_user(username=username)
            if not user.data:
                logger.warning(f"User @{username} not found")
                return []
            
            user_id = user.data.id
            
            # Get user's tweets
            tweets = self.client.get_users_tweets(
                id=user_id,
                max_results=count,
                tweet_fields=['created_at', 'text', 'public_metrics', 'context_annotations', 'entities'],
                exclude=['retweets', 'replies']  # Only original tweets
            )
            
            if not tweets.data:
                logger.info(f"No recent tweets found for @{username}")
                return []
            
            processed_tweets = []
            for tweet in tweets.data:
                # Filter by time
                if tweet.created_at < since_time:
                    continue
                
                # Check if we've already processed this tweet
                tweet_key = f"{username}_{tweet.id}"
                if tweet_key in self.last_check:
                    continue
                
                processed_tweet = {
                    'id': tweet.id,
                    'text': tweet.text,
                    'created_at': tweet.created_at,
                    'username': username,
                    'url': f"https://twitter.com/{username}/status/{tweet.id}",
                    'metrics': tweet.public_metrics if hasattr(tweet, 'public_metrics') else {},
                    'entities': tweet.entities if hasattr(tweet, 'entities') else {},
                    'language': self._detect_language(tweet.text)
                }
                
                processed_tweets.append(processed_tweet)
                self.last_check[tweet_key] = datetime.utcnow()
            
            logger.info(f"Found {len(processed_tweets)} new tweets from @{username}")
            return processed_tweets
            
        except Exception as e:
            logger.error(f"Error fetching tweets from @{username}: {e}")
            return []
    
    def get_all_monitored_tweets(self, since_hours: int = 1) -> List[Dict]:
        """Get tweets from all monitored accounts"""
        all_tweets = []
        
        for account in self.accounts:
            username = account.get('username')
            if not username:
                continue
            
            tweets = self.get_user_tweets(username, count=5, since_hours=since_hours)
            
            # Add account metadata to tweets
            for tweet in tweets:
                tweet['account_name'] = account.get('name', username)
                tweet['account_category'] = account.get('category', 'sports')
                tweet['account_language'] = account.get('language', 'tr')
            
            all_tweets.extend(tweets)
        
        # Sort by creation time (newest first)
        all_tweets.sort(key=lambda x: x['created_at'], reverse=True)
        
        logger.info(f"Collected {len(all_tweets)} total tweets from {len(self.accounts)} accounts")
        return all_tweets
    
    def _detect_language(self, text: str) -> str:
        """Detect tweet language"""
        try:
            from langdetect import detect
            return detect(text)
        except:
            # Simple heuristic for Turkish
            turkish_chars = 'çğıöşüÇĞIİÖŞÜ'
            if any(char in text for char in turkish_chars):
                return 'tr'
            return 'en'
    
    def is_sports_related(self, tweet: Dict) -> bool:
        """Check if tweet is sports/football related"""
        text = tweet.get('text', '').lower()
        
        # Turkish sports keywords
        sports_keywords = [
            'futbol', 'maç', 'gol', 'transfer', 'takım', 'oyuncu', 'antrenör',
            'galatasaray', 'fenerbahçe', 'beşiktaş', 'trabzonspor',
            'şampiyonlar ligi', 'süper lig', 'milli takım', 'fifa', 'uefa',
            'football', 'soccer', 'goal', 'player', 'team', 'coach', 'match'
        ]
        
        return any(keyword in text for keyword in sports_keywords)
    
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
            
            # Skip retweets (additional check)
            if text.startswith('RT @'):
                continue
            
            filtered.append(tweet)
        
        return filtered
