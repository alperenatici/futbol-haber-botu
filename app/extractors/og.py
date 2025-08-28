"""Open Graph metadata extraction."""

from bs4 import BeautifulSoup
from typing import Optional, Dict
import httpx

from app.utils.logging import get_logger
from app.utils.text import clean_text

logger = get_logger(__name__)


class OpenGraphExtractor:
    """Extract Open Graph metadata from web pages."""
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.client = httpx.Client(
            timeout=timeout,
            headers={
                'User-Agent': 'FutBot/1.0 (+https://github.com/futbot/futbot)'
            }
        )
    
    def extract_og_data(self, url: str) -> Optional[Dict[str, str]]:
        """Extract Open Graph metadata from URL."""
        try:
            response = self.client.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            og_data = {}
            
            # Extract Open Graph tags
            og_tags = soup.find_all('meta', property=lambda x: x and x.startswith('og:'))
            for tag in og_tags:
                property_name = tag.get('property', '').replace('og:', '')
                content = tag.get('content', '')
                if property_name and content:
                    og_data[property_name] = clean_text(content)
            
            # Also extract Twitter Card data as fallback
            twitter_tags = soup.find_all('meta', attrs={'name': lambda x: x and x.startswith('twitter:')})
            for tag in twitter_tags:
                name = tag.get('name', '').replace('twitter:', '')
                content = tag.get('content', '')
                if name and content and name not in og_data:
                    # Map Twitter card names to OG equivalents
                    if name == 'title':
                        og_data['title'] = clean_text(content)
                    elif name == 'description':
                        og_data['description'] = clean_text(content)
                    elif name == 'image':
                        og_data['image'] = content
            
            # Extract basic meta tags as additional fallback
            if 'title' not in og_data:
                title_tag = soup.find('title')
                if title_tag:
                    og_data['title'] = clean_text(title_tag.get_text())
            
            if 'description' not in og_data:
                desc_tag = soup.find('meta', attrs={'name': 'description'})
                if desc_tag:
                    og_data['description'] = clean_text(desc_tag.get('content', ''))
            
            return og_data if og_data else None
            
        except Exception as e:
            logger.warning(f"Error extracting OG data from {url}: {e}")
            return None
    
    def __del__(self):
        """Clean up HTTP client."""
        if hasattr(self, 'client'):
            self.client.close()
