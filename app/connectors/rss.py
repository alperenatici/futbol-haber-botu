"""RSS feed connector for news sources."""

import feedparser
import httpx
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from app.utils.logging import get_logger
from app.utils.time import parse_date
from app.utils.text import clean_text, extract_domain
from app.utils.hashing import generate_id

logger = get_logger(__name__)


class NewsItem(BaseModel):
    """News item data model."""
    id: str
    url: str
    title: str
    summary: str
    published_at: Optional[datetime] = None
    source: str
    raw_content: Optional[str] = None


class RSSConnector:
    """RSS feed connector."""
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.client = httpx.Client(
            timeout=timeout,
            headers={
                'User-Agent': 'FutBot/1.0 (+https://github.com/futbot/futbot)'
            }
        )
    
    def fetch_feed(self, url: str, etag: Optional[str] = None, 
                   modified: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Fetch RSS feed with conditional requests."""
        try:
            logger.debug(f"Fetching RSS feed: {url}")
            
            # Prepare headers for conditional request
            headers = {}
            if etag:
                headers['If-None-Match'] = etag
            if modified:
                headers['If-Modified-Since'] = modified
            
            response = self.client.get(url, headers=headers)
            
            # Handle 304 Not Modified
            if response.status_code == 304:
                logger.debug(f"Feed not modified: {url}")
                return None
            
            response.raise_for_status()
            
            # Parse feed
            feed = feedparser.parse(response.content)
            
            if feed.bozo and feed.bozo_exception:
                logger.warning(f"Feed parsing warning for {url}: {feed.bozo_exception}")
            
            # Extract metadata for next request
            metadata = {
                'etag': response.headers.get('etag'),
                'last_modified': response.headers.get('last-modified'),
                'feed': feed
            }
            
            return metadata
            
        except httpx.RequestError as e:
            logger.error(f"Request error for {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching {url}: {e}")
            return None
    
    def parse_entries(self, feed_data: Dict[str, Any], source_url: str) -> List[NewsItem]:
        """Parse feed entries into NewsItem objects."""
        items = []
        feed = feed_data['feed']
        source_domain = extract_domain(source_url)
        
        for entry in feed.entries:
            try:
                # Extract basic info
                title = clean_text(entry.get('title', ''))
                summary = clean_text(entry.get('summary', '') or entry.get('description', ''))
                url = entry.get('link', '')
                
                if not title or not url:
                    continue
                
                # Parse publication date
                published_at = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    try:
                        published_at = datetime(*entry.published_parsed[:6])
                    except:
                        pass
                
                if not published_at and hasattr(entry, 'published'):
                    published_at = parse_date(entry.published)
                
                # Generate unique ID
                item_id = generate_id(title, url)
                
                # Create news item
                item = NewsItem(
                    id=item_id,
                    url=url,
                    title=title,
                    summary=summary,
                    published_at=published_at,
                    source=source_domain,
                    raw_content=entry.get('content', [{}])[0].get('value') if entry.get('content') else None
                )
                
                items.append(item)
                
            except Exception as e:
                logger.warning(f"Error parsing entry from {source_url}: {e}")
                continue
        
        logger.info(f"Parsed {len(items)} items from {source_url}")
        return items
    
    def fetch_all_feeds(self, feed_urls: List[str]) -> List[NewsItem]:
        """Fetch all RSS feeds and return combined news items."""
        all_items = []
        
        for url in feed_urls:
            try:
                feed_data = self.fetch_feed(url)
                if feed_data:
                    items = self.parse_entries(feed_data, url)
                    all_items.extend(items)
            except Exception as e:
                logger.error(f"Error processing feed {url}: {e}")
                continue
        
        # Sort by publication date (newest first)
        all_items.sort(
            key=lambda x: x.published_at or datetime.min,
            reverse=True
        )
        
        logger.info(f"Total items fetched: {len(all_items)}")
        return all_items
    
    def __del__(self):
        """Clean up HTTP client."""
        if hasattr(self, 'client'):
            self.client.close()
