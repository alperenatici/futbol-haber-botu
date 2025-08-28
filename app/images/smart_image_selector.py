"""Smart image selection based on news content entities."""

import re
import httpx
from typing import Optional, Dict, List, Any
from pathlib import Path
from urllib.parse import urlparse
from PIL import Image
import io

from app.utils.logging import get_logger
from app.extractors.entity_extractor import entity_extractor
from app.config import settings

logger = get_logger(__name__)


class SmartImageSelector:
    """Select relevant images based on news content."""
    
    def __init__(self):
        self.client = httpx.Client(
            timeout=30,
            headers={
                'User-Agent': 'FutBot/1.0 (+https://github.com/futbot/futbot)'
            }
        )
        
        # Team logo URLs (can be expanded)
        self.team_logos = {
            'galatasaray': 'https://logoeps.com/wp-content/uploads/2013/03/galatasaray-vector-logo.png',
            'fenerbahçe': 'https://logoeps.com/wp-content/uploads/2013/03/fenerbahce-vector-logo.png',
            'beşiktaş': 'https://logoeps.com/wp-content/uploads/2013/03/besiktas-vector-logo.png',
            'trabzonspor': 'https://logoeps.com/wp-content/uploads/2013/03/trabzonspor-vector-logo.png',
            'real madrid': 'https://logoeps.com/wp-content/uploads/2013/03/real-madrid-vector-logo.png',
            'barcelona': 'https://logoeps.com/wp-content/uploads/2013/03/barcelona-vector-logo.png',
            'manchester united': 'https://logoeps.com/wp-content/uploads/2013/03/manchester-united-vector-logo.png',
            'liverpool': 'https://logoeps.com/wp-content/uploads/2013/03/liverpool-vector-logo.png'
        }
    
    def extract_image_from_source(self, url: str) -> Optional[str]:
        """Extract featured image from news source."""
        try:
            response = self.client.get(url)
            response.raise_for_status()
            html = response.text
            
            # Look for Open Graph image
            og_image_match = re.search(r'<meta property="og:image" content="([^"]+)"', html, re.IGNORECASE)
            if og_image_match:
                image_url = og_image_match.group(1)
                if self.is_valid_image_url(image_url):
                    logger.info(f"Found OG image: {image_url}")
                    return image_url
            
            # Look for Twitter card image
            twitter_image_match = re.search(r'<meta name="twitter:image" content="([^"]+)"', html, re.IGNORECASE)
            if twitter_image_match:
                image_url = twitter_image_match.group(1)
                if self.is_valid_image_url(image_url):
                    logger.info(f"Found Twitter image: {image_url}")
                    return image_url
            
            # Look for featured image in article
            featured_match = re.search(r'<img[^>]+class="[^"]*featured[^"]*"[^>]+src="([^"]+)"', html, re.IGNORECASE)
            if featured_match:
                image_url = featured_match.group(1)
                if self.is_valid_image_url(image_url):
                    logger.info(f"Found featured image: {image_url}")
                    return image_url
            
        except Exception as e:
            logger.error(f"Error extracting image from {url}: {e}")
        
        return None
    
    def is_valid_image_url(self, url: str) -> bool:
        """Check if URL points to a valid image."""
        if not url:
            return False
        
        # Check file extension
        parsed = urlparse(url)
        path = parsed.path.lower()
        valid_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}
        
        if any(path.endswith(ext) for ext in valid_extensions):
            return True
        
        # Check if URL contains image indicators
        image_indicators = ['image', 'photo', 'picture', 'img']
        return any(indicator in url.lower() for indicator in image_indicators)
    
    def get_team_logo(self, team_name: str) -> Optional[str]:
        """Get team logo URL."""
        team_key = team_name.lower()
        return self.team_logos.get(team_key)
    
    def search_unsplash_image(self, query: str) -> Optional[str]:
        """Search for copyright-free images on Unsplash."""
        try:
            # Unsplash API requires access key, using source.unsplash.com for now
            # This provides random images but is free to use
            search_query = query.replace(' ', '%20')
            unsplash_url = f"https://source.unsplash.com/800x600/?{search_query}"
            
            # Test if the URL returns a valid image
            response = self.client.head(unsplash_url)
            if response.status_code == 200:
                logger.info(f"Found Unsplash image for: {query}")
                return unsplash_url
        except Exception as e:
            logger.error(f"Error searching Unsplash for {query}: {e}")
        
        return None
    
    def download_and_validate_image(self, image_url: str) -> Optional[Path]:
        """Download and validate image."""
        try:
            response = self.client.get(image_url)
            response.raise_for_status()
            
            # Validate it's actually an image
            try:
                image = Image.open(io.BytesIO(response.content))
                image.verify()
            except Exception:
                logger.error(f"Invalid image content from {image_url}")
                return None
            
            # Save to temp directory
            filename = f"news_image_{hash(image_url) % 10000}.jpg"
            image_path = settings.temp_dir / filename
            
            with open(image_path, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"Downloaded image: {image_path}")
            return image_path
            
        except Exception as e:
            logger.error(f"Error downloading image {image_url}: {e}")
            return None
    
    def select_best_image(self, news_url: str, title: str, summary: str) -> Optional[Path]:
        """Select the best image for the news item."""
        text = f"{title} {summary}"
        entities = entity_extractor.extract_entities(text)
        
        # Strategy 1: Try to get image from news source
        source_image = self.extract_image_from_source(news_url)
        if source_image:
            image_path = self.download_and_validate_image(source_image)
            if image_path:
                return image_path
        
        # Strategy 2: Get primary entity and search for relevant image
        primary_entity = entity_extractor.get_primary_entity(entities)
        if primary_entity:
            # Try team logo first
            if primary_entity.get('type') in ['turkish_team', 'international_team']:
                logo_url = self.get_team_logo(primary_entity['name'])
                if logo_url:
                    image_path = self.download_and_validate_image(logo_url)
                    if image_path:
                        return image_path
            
            # Try Unsplash search
            search_query = f"football {primary_entity['name']}"
            unsplash_image = self.search_unsplash_image(search_query)
            if unsplash_image:
                image_path = self.download_and_validate_image(unsplash_image)
                if image_path:
                    return image_path
        
        # Strategy 3: Generic football image
        generic_queries = ['football', 'soccer', 'futbol', 'football stadium']
        for query in generic_queries:
            unsplash_image = self.search_unsplash_image(query)
            if unsplash_image:
                image_path = self.download_and_validate_image(unsplash_image)
                if image_path:
                    return image_path
        
        logger.warning(f"No suitable image found for: {title[:50]}...")
        return None
    
    def __del__(self):
        """Clean up HTTP client."""
        if hasattr(self, 'client'):
            self.client.close()


# Global smart image selector instance
smart_image_selector = SmartImageSelector()
