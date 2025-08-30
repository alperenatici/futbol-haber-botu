"""X/Twitter client for posting news with media."""

import tweepy
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from app.config import settings
from app.utils.logging import get_logger
from app.utils.dedupe import deduplicator
from app.utils.time import can_post_now

logger = get_logger(__name__)


class XClient:
    """X/Twitter API client for posting news."""
    
    def __init__(self):
        self.api_key = settings.x_api_key
        self.api_secret = settings.x_api_secret
        self.access_token = settings.x_access_token
        self.access_token_secret = settings.x_access_token_secret
        
        self._client = None
        self._api_v1 = None
        self.last_post_time = None
        self.daily_post_count = 0
        self.daily_reset_date = datetime.now().date()
    
    def _init_clients(self):
        """Initialize Twitter API clients."""
        if not settings.has_x_credentials():
            raise ValueError("X/Twitter credentials not found in environment variables")
        
        try:
            # Initialize OAuth 1.0a authentication
            auth = tweepy.OAuth1UserHandler(
                self.api_key,
                self.api_secret,
                self.access_token,
                self.access_token_secret
            )
            
            # Use v2 API for posting (Free tier supports this)
            self._client = tweepy.Client(
                consumer_key=self.api_key,
                consumer_secret=self.api_secret,
                access_token=self.access_token,
                access_token_secret=self.access_token_secret,
                wait_on_rate_limit=False  # Manuel rate limit handling
            )
            
            # Keep v1.1 API for media upload only
            self._api_v1 = tweepy.API(auth, wait_on_rate_limit=False)
            
            logger.info("X/Twitter clients initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize X clients: {e}")
            raise
    
    def _reset_daily_count_if_needed(self):
        """Reset daily post count if new day."""
        today = datetime.now().date()
        if today > self.daily_reset_date:
            self.daily_post_count = 0
            self.daily_reset_date = today
            logger.info("Daily post count reset")
    
    def can_post(self) -> bool:
        """Check if we can post based on rate limits."""
        self._reset_daily_count_if_needed()
        
        # Check daily limit
        if self.daily_post_count >= settings.config.rate_limits.daily_post_cap:
            logger.warning(f"Daily post limit reached: {self.daily_post_count}")
            return False
        
        # Check time-based limit
        min_minutes = settings.config.rate_limits.min_minutes_between_posts
        if not can_post_now(self.last_post_time, min_minutes):
            logger.info(f"Must wait {min_minutes} minutes between posts")
            return False
        
        return True
    
    def upload_media(self, image_path: Path) -> Optional[str]:
        """Upload media file and return media ID."""
        if not self._api_v1:
            self._init_clients()
        
        try:
            if not image_path.exists():
                logger.error(f"Image file not found: {image_path}")
                return None
            
            logger.info(f"Uploading media: {image_path}")
            
            # Upload media using v1.1 API
            media = self._api_v1.media_upload(str(image_path))
            
            logger.info(f"Media uploaded successfully: {media.media_id}")
            return media.media_id_string
            
        except Exception as e:
            logger.error(f"Failed to upload media {image_path}: {e}")
            return None
    
    def post_tweet(self, text: str, media_ids: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """Post a tweet with optional media."""
        if not self._client:
            self._init_clients()
        
        try:
            logger.info(f"Posting tweet: {text[:50]}...")
            
            # Create tweet using v2 API (Free tier supports this)
            response = self._client.create_tweet(
                text=text,
                media_ids=media_ids
            )
            
            if response and response.data:
                tweet_id = response.data['id']
                tweet_url = f"https://twitter.com/user/status/{tweet_id}"
                
                # Update tracking
                self.last_post_time = datetime.now()
                self.daily_post_count += 1
                
                logger.info(f"Tweet posted successfully: {tweet_url}")
                
                return {
                    'id': tweet_id,
                    'url': tweet_url,
                    'text': text,
                    'media_count': len(media_ids) if media_ids else 0
                }
            else:
                logger.error("Tweet creation failed - no response data")
                return None
                
        except tweepy.Forbidden as e:
            logger.error(f"Tweet forbidden: {e}")
            logger.error(f"This might be due to duplicate content or policy violation")
            return None
        except tweepy.Unauthorized as e:
            logger.error(f"Tweet unauthorized: {e}")
            logger.error(f"Check API credentials and permissions")
            return None
        except tweepy.BadRequest as e:
            logger.error(f"Bad request: {e}")
            logger.error(f"Tweet text might be too long or contain invalid characters")
            return None
        except tweepy.TooManyRequests as e:
            logger.warning(f"Rate limit exceeded: {e}")
            # Kısa bir bekleme süresi (5 dakika) sonra tekrar dene
            logger.info("Rate limit hit - bot will wait for next scheduled run")
            return None
        except Exception as e:
            logger.error(f"Error posting tweet: {e}")
            logger.error(f"Tweet text length: {len(text)} characters")
            return None
    
    def post_news(self, text: str, image_path: Optional[Path] = None,
                  news_url: str = "", title: str = "") -> Optional[Dict[str, Any]]:
        """Post news with optional image."""
        # Check if we can post
        if not self.can_post():
            logger.info("Skipping post due to rate limits")
            return None
        
        # Check for duplicates
        if news_url and title:
            if deduplicator.is_duplicate(news_url, title, text):
                logger.info(f"Skipping duplicate news: {title}")
                return None
        
        try:
            media_ids = []
            
            # Upload image if provided
            if image_path and image_path.exists():
                media_id = self.upload_media(image_path)
                if media_id:
                    media_ids.append(media_id)
                else:
                    logger.warning("Failed to upload image, posting without media")
            
            # Post tweet
            result = self.post_tweet(text, media_ids if media_ids else None)
            
            if result:
                # Mark as posted in deduplication database
                if news_url and title:
                    from app.utils.text import extract_domain
                    source = extract_domain(news_url)
                    deduplicator.mark_as_posted(news_url, title, text, source)
                
                logger.info("News posted successfully")
                return result
            
            return None
            
        except Exception as e:
            logger.error(f"Error posting news: {e}")
            return None
    
    def get_recent_tweets(self, count: int = 5) -> List[Dict[str, Any]]:
        """Get recent tweets from the account."""
        if not self._api_v1:
            self._init_clients()
        
        try:
            # Get recent tweets using v1.1 API
            tweets = self._api_v1.user_timeline(
                count=count,
                include_rts=False,
                exclude_replies=True
            )
            
            if tweets:
                return [
                    {
                        'id': tweet.id_str,
                        'text': tweet.text,
                        'created_at': tweet.created_at,
                        'metrics': {
                            'retweet_count': tweet.retweet_count,
                            'favorite_count': tweet.favorite_count
                        }
                    }
                    for tweet in tweets
                ]
            
            return []
            
        except Exception as e:
            logger.error(f"Error fetching recent tweets: {e}")
            return []
    
    def test_connection(self) -> bool:
        """Test X/Twitter API connection."""
        try:
            if not self._api_v1:
                self._init_clients()
            
            # Use v1.1 API to verify credentials
            me = self._api_v1.verify_credentials()
            if me:
                logger.info(f"Connected to X as: @{me.screen_name}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"X connection test failed: {e}")
            return False


# Global X client instance
x_client = XClient()
