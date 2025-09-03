"""Social media connectors for news collection."""

import tweepy
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from app.config import settings
from app.utils.logging import get_logger
from app.connectors.rss import NewsItem
from app.utils.text import clean_text, is_turkish_text
from app.utils.time import parse_date

logger = get_logger(__name__)


class SocialConnector:
    """Connector for social media platforms."""
    
    def __init__(self):
        # Load accounts from config instead of hardcoding
        self.twitter_accounts = self._load_twitter_accounts()
        if not self.twitter_accounts:
            # Fallback to basic list if config fails
            self.twitter_accounts = [
                "yagosabuncuoglu",  # Yağız Sabuncuoğlu
                "aspor",            # A Spor
                "sporx",            # Sporx
            ]
        self._client_v2 = None
        self._init_twitter_client()
    
    def _load_twitter_accounts(self):
        """Load Twitter accounts from sources.yaml config."""
        try:
            import yaml
            from pathlib import Path
            
            config_path = Path("data/sources.yaml")
            if not config_path.exists():
                logger.warning("sources.yaml not found")
                return []
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                accounts = config.get('twitter_accounts', [])
                usernames = [acc.get('username') for acc in accounts if acc.get('username')]
                logger.info(f"Loaded {len(usernames)} Twitter accounts from config")
                return usernames
        except Exception as e:
            logger.error(f"Error loading Twitter accounts from config: {e}")
            return []
    
    def _init_twitter_client(self):
        """Initialize Twitter API client with Bearer token for v2."""
        if not hasattr(settings, 'x_bearer_token') or not settings.x_bearer_token:
            logger.warning("X_BEARER_TOKEN not available for social connector")
            return
        
        try:
            # Use v2 API with Bearer token for better rate limits
            self._client_v2 = tweepy.Client(
                bearer_token=settings.x_bearer_token,
                wait_on_rate_limit=False  # Manuel handling
            )
            logger.info("Twitter API v2 client initialized for social connector")
        except Exception as e:
            logger.error(f"Failed to initialize Twitter v2 client: {e}")
            self._client_v2 = None
    
    def fetch_twitter_news(self, max_tweets_per_account: int = 2) -> List[NewsItem]:
        """Fetch recent tweets using Twitter API v2 with Bearer token."""
        if not self._client_v2:
            logger.warning("Twitter API v2 not available")
            return []
        
        all_items = []
        cutoff_time = datetime.now() - timedelta(hours=12)  # Last 12 hours
        
        # Football keywords for search
        football_keywords = [
            'futbol', 'transfer', 'galatasaray', 'fenerbahçe', 'beşiktaş', 
            'trabzonspor', 'başakşehir', 'football', 'soccer', 'goal',
            'match', 'player', 'coach', 'team', 'league', 'uefa', 'fifa',
            'sakatlık', 'antrenman', 'maç', 'gol', 'oyuncu'
        ]
        
        for username in self.twitter_accounts:
            try:
                logger.info(f"Searching sports tweets from @{username}")
                
                # Use search_recent_tweets with from: operator
                query = f"from:{username} ({' OR '.join(football_keywords[:5])}) -is:retweet -is:reply"
                
                response = self._client_v2.search_recent_tweets(
                    query=query,
                    max_results=max_tweets_per_account,
                    tweet_fields=['created_at', 'author_id', 'public_metrics'],
                    user_fields=['username'],
                    expansions=['author_id']
                )
                
                if not response.data:
                    logger.info(f"No recent tweets found for @{username}")
                    continue
                
                account_items = []
                for tweet in response.data:
                    # Skip old tweets
                    if tweet.created_at < cutoff_time:
                        continue
                    
                    # Basic football content filtering
                    text = tweet.text.lower()
                    if not any(keyword in text for keyword in football_keywords):
                        continue
                    
                    # Create NewsItem
                    item = NewsItem(
                        id=f"twitter_{tweet.id}",
                        title=f"@{username}: {clean_text(tweet.text[:100])}...",
                        summary=clean_text(tweet.text),
                        url=f"https://twitter.com/{username}/status/{tweet.id}",
                        source=f"Twitter @{username}",
                        published_at=tweet.created_at,
                        language="tr" if is_turkish_text(tweet.text) else "en"
                    )
                    
                    account_items.append(item)
                
                logger.info(f"✓ Found {len(account_items)} football tweets from @{username}")
                all_items.extend(account_items)
                
            except tweepy.TooManyRequests as e:
                logger.warning(f"Rate limit reached for @{username}: {e}")
                # Continue with other accounts instead of breaking
                continue
            except Exception as e:
                logger.error(f"Error searching tweets from @{username}: {e}")
                continue
        
        logger.info(f"Social media total: {len(all_items)} items from {len(self.twitter_accounts)} accounts")
        return all_items


# Global social connector instance
social_connector = SocialConnector()
