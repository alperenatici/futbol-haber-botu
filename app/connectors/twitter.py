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
        """Setup Twitter API v2 client with search endpoints only"""
        try:
            import os
            
            # Twitter API v2 credentials - Bearer token is required for v2
            bearer_token = os.getenv('X_BEARER_TOKEN')
            api_key = os.getenv('X_API_KEY')
            api_secret = os.getenv('X_API_SECRET')
            access_token = os.getenv('X_ACCESS_TOKEN')
            access_token_secret = os.getenv('X_ACCESS_TOKEN_SECRET')
            
            # For Free tier, we need bearer token for search endpoints
            if not bearer_token:
                logger.error("Bearer token is required for X API v2 Free tier")
                return
            
            # Setup API v2 client with bearer token only (Free tier compatible)
            self.client = tweepy.Client(
                bearer_token=bearer_token,
                wait_on_rate_limit=True
            )
            
            # Keep v1.1 API for posting (if needed later)
            if all([api_key, api_secret, access_token, access_token_secret]):
                auth = tweepy.OAuthHandler(api_key, api_secret)
                auth.set_access_token(access_token, access_token_secret)
                self.api = tweepy.API(auth, wait_on_rate_limit=True)
            else:
                self.api = None
                logger.warning("OAuth 1.0a credentials not found, posting will not be available")
            
            logger.info("Twitter API v2 connection established (Free tier compatible)")
            
        except Exception as e:
            logger.error(f"Failed to setup Twitter API: {e}")
    
    def get_user_tweets(self, username: str, count: int = 10, since_hours: int = 24) -> List[Dict]:
        """Get recent tweets from a specific user using search (Free tier compatible)"""
        if not self.client:
            logger.error("Twitter API v2 client not initialized")
            return []
        
        try:
            from datetime import timezone
            since_time = datetime.now(timezone.utc) - timedelta(hours=since_hours)
            
            # Use search tweets endpoint with from: operator (Free tier compatible)
            # This searches for tweets from a specific user
            query = f"from:{username} -is:retweet -is:reply"
            
            # Search for tweets
            tweets = self.client.search_recent_tweets(
                query=query,
                max_results=min(count, 100),  # Max 100 for Free tier
                tweet_fields=['created_at', 'text', 'public_metrics', 'context_annotations', 'entities', 'author_id'],
                user_fields=['username', 'name'],
                expansions=['author_id']
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
                self.last_check[tweet_key] = datetime.now(timezone.utc)
            
            logger.info(f"Found {len(processed_tweets)} new tweets from @{username} using search")
            return processed_tweets
            
        except Exception as e:
            logger.error(f"Error searching tweets from @{username}: {e}")
            return []
    
    def get_all_monitored_tweets(self, since_hours: int = 1) -> List[Dict]:
        """Get tweets from all monitored accounts"""
        all_tweets = []
        
        # Limit to first 3 accounts to avoid rate limits
        limited_accounts = self.accounts[:3]
        
        for account in limited_accounts:
            username = account.get('username')
            if not username:
                continue
            
            tweets = self.get_user_tweets(username, count=1, since_hours=since_hours)
            
            # Add delay between requests to avoid rate limiting
            import time
            time.sleep(2)
            
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
    
    def search_sports_tweets(self, query: str = "futbol OR transfer OR gol", count: int = 10) -> List[Dict]:
        """Search for sports-related tweets using Free tier search endpoint"""
        if not self.client:
            logger.error("Twitter API v2 client not initialized")
            return []
        
        try:
            # Search for sports tweets in Turkish
            search_query = f"{query} lang:tr -is:retweet"
            
            tweets = self.client.search_recent_tweets(
                query=search_query,
                max_results=min(count, 100),
                tweet_fields=['created_at', 'text', 'public_metrics', 'context_annotations', 'entities', 'author_id'],
                user_fields=['username', 'name'],
                expansions=['author_id']
            )
            
            if not tweets.data:
                logger.info("No sports tweets found")
                return []
            
            # Get user info from includes
            users_dict = {}
            if tweets.includes and 'users' in tweets.includes:
                for user in tweets.includes['users']:
                    users_dict[user.id] = user.username
            
            processed_tweets = []
            for tweet in tweets.data:
                username = users_dict.get(tweet.author_id, 'unknown')
                
                processed_tweet = {
                    'id': tweet.id,
                    'text': tweet.text,
                    'created_at': tweet.created_at,
                    'username': username,
                    'url': f"https://twitter.com/{username}/status/{tweet.id}",
                    'metrics': tweet.public_metrics if hasattr(tweet, 'public_metrics') else {},
                    'entities': tweet.entities if hasattr(tweet, 'entities') else {},
                    'language': 'tr'
                }
                
                processed_tweets.append(processed_tweet)
            
            logger.info(f"Found {len(processed_tweets)} sports tweets")
            return processed_tweets
            
        except Exception as e:
            logger.error(f"Error searching sports tweets: {e}")
            return []
