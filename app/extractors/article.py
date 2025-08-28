"""Article content extraction using trafilatura and readability."""

import trafilatura
from readability import Document
from bs4 import BeautifulSoup
import httpx
from typing import Optional, Dict, Any
from datetime import datetime

from app.utils.logging import get_logger
from app.utils.text import clean_text, extract_domain, normalize_title
from app.utils.time import parse_date
from app.connectors.rss import NewsItem
from app.utils.hashing import generate_id

logger = get_logger(__name__)


class ArticleExtractor:
    """Extract article content from URLs."""
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.client = httpx.Client(
            timeout=timeout,
            headers={
                'User-Agent': 'FutBot/1.0 (+https://github.com/futbot/futbot)'
            }
        )
    
    def fetch_url(self, url: str) -> Optional[str]:
        """Fetch HTML content from URL."""
        try:
            response = self.client.get(url)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    def extract_with_trafilatura(self, html: str, url: str) -> Optional[Dict[str, Any]]:
        """Extract content using trafilatura."""
        try:
            # Extract main content
            content = trafilatura.extract(
                html,
                include_comments=False,
                include_tables=False,
                include_formatting=False
            )
            
            if not content:
                return None
            
            # Extract metadata
            metadata = trafilatura.extract_metadata(html)
            
            result = {
                'content': clean_text(content),
                'title': metadata.title if metadata else None,
                'author': metadata.author if metadata else None,
                'date': metadata.date if metadata else None,
                'description': metadata.description if metadata else None,
                'sitename': metadata.sitename if metadata else None
            }
            
            return result
            
        except Exception as e:
            logger.warning(f"Trafilatura extraction failed for {url}: {e}")
            return None
    
    def extract_with_readability(self, html: str, url: str) -> Optional[Dict[str, Any]]:
        """Extract content using readability as fallback."""
        try:
            doc = Document(html)
            
            # Parse the extracted HTML
            soup = BeautifulSoup(doc.content(), 'html.parser')
            content = soup.get_text()
            
            if not content or len(content.strip()) < 100:
                return None
            
            result = {
                'content': clean_text(content),
                'title': clean_text(doc.title()),
                'author': None,
                'date': None,
                'description': None,
                'sitename': extract_domain(url)
            }
            
            return result
            
        except Exception as e:
            logger.warning(f"Readability extraction failed for {url}: {e}")
            return None
    
    def extract_article(self, url: str) -> Optional[NewsItem]:
        """Extract article content and create NewsItem."""
        html = self.fetch_url(url)
        if not html:
            return None
        
        # Try trafilatura first
        extracted = self.extract_with_trafilatura(html, url)
        
        # Fallback to readability
        if not extracted:
            extracted = self.extract_with_readability(html, url)
        
        if not extracted or not extracted.get('content'):
            logger.warning(f"No content extracted from {url}")
            return None
        
        # Create NewsItem
        title = normalize_title(extracted.get('title', ''))
        content = extracted['content']
        
        # Use first paragraph as summary if no description
        summary = extracted.get('description', '')
        if not summary and content:
            paragraphs = content.split('\n\n')
            summary = paragraphs[0] if paragraphs else content[:200]
        
        summary = clean_text(summary)
        
        # Parse date
        published_at = None
        if extracted.get('date'):
            published_at = parse_date(extracted['date'])
        
        # Generate ID
        item_id = generate_id(title, url)
        
        item = NewsItem(
            id=item_id,
            url=url,
            title=title,
            summary=summary,
            published_at=published_at,
            source=extract_domain(url),
            raw_content=content
        )
        
        return item
    
    def extract_multiple(self, urls: list) -> list[NewsItem]:
        """Extract articles from multiple URLs."""
        items = []
        
        for url in urls:
            try:
                item = self.extract_article(url)
                if item:
                    items.append(item)
            except Exception as e:
                logger.error(f"Error extracting {url}: {e}")
                continue
        
        logger.info(f"Extracted {len(items)} articles from {len(urls)} URLs")
        return items
    
    def __del__(self):
        """Clean up HTTP client."""
        if hasattr(self, 'client'):
            self.client.close()
