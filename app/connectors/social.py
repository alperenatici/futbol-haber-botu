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
        self._api_v1 = None
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
        """Initialize Twitter API client."""
        if not settings.has_x_credentials():
            logger.warning("X/Twitter credentials not available for social connector")
            return
        
        try:
            auth = tweepy.OAuth1UserHandler(
                settings.x_api_key,
                settings.x_api_secret,
                settings.x_access_token,
                settings.x_access_token_secret
            )
            self._api_v1 = tweepy.API(auth, wait_on_rate_limit=True)
            logger.info("Twitter API client initialized for social connector")
        except Exception as e:
            logger.error(f"Failed to initialize Twitter client: {e}")
    
    def fetch_twitter_news(self, max_tweets_per_account: int = 5) -> List[NewsItem]:
        """Fetch recent tweets from Turkish football journalists."""
        if not self._api_v1:
            logger.warning("Twitter API not available")
            return []
        
        all_items = []
        cutoff_time = datetime.now() - timedelta(hours=6)  # Last 6 hours
        
        for username in self.twitter_accounts:
            try:
                logger.info(f"Fetching tweets from @{username}")
                
                # Get user timeline
                tweets = self._api_v1.user_timeline(
                    screen_name=username,
                    count=max_tweets_per_account,
                    exclude_replies=True,
                    include_rts=False,
                    tweet_mode='extended'
                )
                
                account_items = []
                for tweet in tweets:
                    # Skip old tweets
                    if tweet.created_at < cutoff_time:
                        continue
                    
                    # Skip non-football content (basic filtering)
                    text = tweet.full_text.lower()
                    football_keywords = [
                        'futbol', 'transfer', 'galatasaray', 'fenerbahçe', 'beşiktaş', 
                        'trabzonspor', 'başakşehir', 'football', 'soccer', 'goal',
                        'match', 'player', 'coach', 'team', 'league', 'uefa', 'fifa'
                    ]
                    
                    if not any(keyword in text for keyword in football_keywords):
                        continue
                    
                    # Create NewsItem
                    item = NewsItem(
                        id=f"twitter_{tweet.id_str}",
                        title=f"@{username}: {clean_text(tweet.full_text[:100])}...",
                        summary=clean_text(tweet.full_text),
                        url=f"https://twitter.com/{username}/status/{tweet.id_str}",
                        source=f"Twitter @{username}",
                        published_at=tweet.created_at,
                        language="tr" if is_turkish_text(tweet.full_text) else "en"
                    )
                    
                    account_items.append(item)
                
                logger.info(f"✓ Fetched {len(account_items)} football tweets from @{username}")
                all_items.extend(account_items)
                
            except tweepy.TooManyRequests:
                logger.warning(f"Rate limit reached for @{username}")
                break
            except Exception as e:
                logger.error(f"Error fetching tweets from @{username}: {e}")
                continue
        
        logger.info(f"Social media total: {len(all_items)} items from {len(self.twitter_accounts)} accounts")
        return all_items


# Global social connector instance
social_connector = SocialConnector()
