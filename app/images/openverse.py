"""Openverse API integration for CC-licensed images."""

import httpx
import json
from typing import Optional, List, Dict, Any
from urllib.parse import quote
from pathlib import Path

from app.config import settings
from app.utils.logging import get_logger
from app.utils.text import extract_keywords

logger = get_logger(__name__)


class OpenverseClient:
    """Client for Openverse API to fetch CC-licensed images."""
    
    def __init__(self):
        self.base_url = "https://api.openverse.org/v1"
        self.client_id = settings.openverse_client_id
        self.client_secret = settings.openverse_client_secret
        
        self.client = httpx.Client(
            timeout=30,
            headers={
                'User-Agent': 'FutBot/1.0 (+https://github.com/futbot/futbot)'
            }
        )
        
        self._access_token = None
    
    def _get_access_token(self) -> Optional[str]:
        """Get OAuth2 access token for higher rate limits."""
        if not self.client_id or not self.client_secret:
            logger.debug("No Openverse credentials provided, using anonymous access")
            return None
        
        if self._access_token:
            return self._access_token
        
        try:
            response = self.client.post(
                f"{self.base_url}/auth_tokens/token/",
                data={
                    'client_id': self.client_id,
                    'client_secret': self.client_secret,
                    'grant_type': 'client_credentials'
                }
            )
            response.raise_for_status()
            
            token_data = response.json()
            self._access_token = token_data.get('access_token')
            
            logger.info("Successfully authenticated with Openverse API")
            return self._access_token
            
        except Exception as e:
            logger.warning(f"Failed to authenticate with Openverse: {e}")
            return None
    
    def search_images(self, query: str, license_type: str = "cc0,by,by-sa", 
                     per_page: int = 10) -> List[Dict[str, Any]]:
        """Search for images on Openverse."""
        try:
            # Prepare headers
            headers = {}
            token = self._get_access_token()
            if token:
                headers['Authorization'] = f'Bearer {token}'
            
            # Prepare parameters
            params = {
                'q': query,
                'license_type': license_type,
                'page_size': per_page,
                'mature': 'false',
                'qa': 'true'  # Quality assurance - better quality images
            }
            
            response = self.client.get(
                f"{self.base_url}/images/",
                params=params,
                headers=headers
            )
            response.raise_for_status()
            
            data = response.json()
            results = data.get('results', [])
            
            logger.debug(f"Found {len(results)} images for query: {query}")
            return results
            
        except Exception as e:
            logger.error(f"Error searching Openverse: {e}")
            return []
    
    def download_image(self, image_url: str, filename: str) -> Optional[Path]:
        """Download image from URL."""
        try:
            response = self.client.get(image_url)
            response.raise_for_status()
            
            # Save to temp directory
            file_path = settings.temp_dir / filename
            
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
            logger.debug(f"Downloaded image: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Error downloading image {image_url}: {e}")
            return None
    
    def find_football_image(self, title: str, summary: str) -> Optional[Dict[str, Any]]:
        """Find relevant football image based on news content."""
        # Extract keywords for search
        keywords = extract_keywords(f"{title} {summary}")
        
        # Football-related search terms
        football_terms = ['football', 'soccer', 'futbol']
        
        # Try different search combinations
        search_queries = []
        
        # Add specific team/player names if found
        for keyword in keywords[:3]:  # Top 3 keywords
            if len(keyword) > 3:  # Skip very short words
                search_queries.append(f"{keyword} football")
        
        # Generic football searches
        search_queries.extend([
            "football stadium",
            "soccer ball",
            "football player",
            "football match",
            "soccer field"
        ])
        
        # Try each search query
        for query in search_queries:
            results = self.search_images(query, per_page=5)
            
            if results:
                # Filter for good quality images
                for result in results:
                    # Check image dimensions (avoid very small images)
                    width = result.get('width', 0)
                    height = result.get('height', 0)
                    
                    if width >= 400 and height >= 300:
                        return {
                            'url': result.get('url'),
                            'thumbnail': result.get('thumbnail'),
                            'title': result.get('title', ''),
                            'creator': result.get('creator', ''),
                            'license': result.get('license', ''),
                            'license_url': result.get('license_url', ''),
                            'source': result.get('source', ''),
                            'width': width,
                            'height': height,
                            'search_query': query
                        }
        
        logger.info(f"No suitable images found for: {title}")
        return None
    
    def format_attribution(self, image_data: Dict[str, Any]) -> str:
        """Format image attribution text."""
        creator = image_data.get('creator', 'Unknown')
        license_name = image_data.get('license', 'CC')
        
        # Shorten license names
        license_short = {
            'cc0': 'CC0',
            'by': 'CC BY',
            'by-sa': 'CC BY-SA',
            'by-nc': 'CC BY-NC',
            'by-nd': 'CC BY-ND'
        }.get(license_name.lower(), license_name.upper())
        
        return f"Fotoğraf: {creator}/{license_short}"
    
    def __del__(self):
        """Clean up HTTP client."""
        if hasattr(self, 'client'):
            self.client.close()


# Global Openverse client instance
openverse_client = OpenverseClient()
