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
        """Extract content using trafilatura with improved content quality."""
        try:
            # Extract main content with better settings
            content = trafilatura.extract(
                html,
                include_comments=False,
                include_tables=True,  # Include tables for better content
                include_formatting=True,  # Keep some formatting
                favor_precision=True,  # Prefer complete content
                favor_recall=False  # Avoid noise
            )
            
            if not content or len(content.strip()) < 50:
                return None
            
            # Extract metadata
            metadata = trafilatura.extract_metadata(html)
            
            # Clean and validate content
            cleaned_content = clean_text(content)
            
            # Ensure content has meaningful sentences
            sentences = [s.strip() for s in cleaned_content.split('.') if s.strip()]
            if len(sentences) < 2:  # Need at least 2 sentences for meaningful content
                return None
                
            # Reconstruct content with proper sentence structure
            meaningful_content = '. '.join(sentences)
            if not meaningful_content.endswith('.'):
                meaningful_content += '.'
            
            result = {
                'content': meaningful_content,
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
        """Extract content using readability as fallback with improved text processing."""
        try:
            doc = Document(html)
            
            # Parse the extracted HTML
            soup = BeautifulSoup(doc.content(), 'html.parser')
            
            # Remove unwanted elements
            for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                element.decompose()
            
            # Extract text with better spacing
            content = soup.get_text(separator=' ', strip=True)
            
            if not content or len(content.strip()) < 100:
                return None
            
            # Clean and structure content
            cleaned_content = clean_text(content)
            
            # Ensure proper sentence structure
            sentences = []
            for sentence in cleaned_content.split('.'):
                sentence = sentence.strip()
                if sentence and len(sentence) > 10:  # Filter out very short fragments
                    sentences.append(sentence)
            
            if len(sentences) < 2:
                return None
                
            # Reconstruct with proper punctuation
            meaningful_content = '. '.join(sentences)
            if not meaningful_content.endswith('.'):
                meaningful_content += '.'
            
            result = {
                'content': meaningful_content,
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
        
        if not extracted or not extracted.get('content') or len(extracted.get('content', '').strip()) < 50:
            logger.warning(f"No meaningful content extracted from {url}")
            return None
        
        # Create NewsItem
        title = normalize_title(extracted.get('title', ''))
        content = extracted['content']
        
        # Create meaningful summary
        summary = extracted.get('description', '')
        if not summary and content:
            # Extract first meaningful sentences for summary
            sentences = [s.strip() for s in content.split('.') if s.strip() and len(s.strip()) > 20]
            if sentences:
                # Use first 2-3 sentences for summary, max 300 chars
                summary_sentences = []
                char_count = 0
                for sentence in sentences[:3]:
                    if char_count + len(sentence) < 300:
                        summary_sentences.append(sentence)
                        char_count += len(sentence)
                    else:
                        break
                summary = '. '.join(summary_sentences)
                if summary and not summary.endswith('.'):
                    summary += '.'
            else:
                summary = content[:200] + '...' if len(content) > 200 else content
        
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
