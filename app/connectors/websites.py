"""Website scraping connector for news sources."""

import httpx
import time
from urllib.robotparser import RobotFileParser
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from typing import List, Optional, Dict, Set
from datetime import datetime, timedelta

from app.utils.logging import get_logger
from app.utils.text import extract_domain
from app.connectors.rss import NewsItem
from app.utils.hashing import generate_id

logger = get_logger(__name__)


class WebsiteConnector:
    """Website scraping connector with robots.txt compliance."""
    
    def __init__(self, timeout: int = 30, delay: float = 1.0):
        self.timeout = timeout
        self.delay = delay  # Delay between requests
        self.robots_cache = {}  # Cache for robots.txt
        self.last_request = {}  # Track last request time per domain
        
        self.client = httpx.Client(
            timeout=timeout,
            headers={
                'User-Agent': 'FutBot/1.0 (+https://github.com/futbot/futbot)'
            }
        )
    
    def can_fetch(self, url: str) -> bool:
        """Check if URL can be fetched according to robots.txt."""
        domain = extract_domain(url)
        
        if domain not in self.robots_cache:
            try:
                robots_url = f"https://{domain}/robots.txt"
                rp = RobotFileParser()
                rp.set_url(robots_url)
                rp.read()
                self.robots_cache[domain] = rp
            except:
                # If robots.txt can't be fetched, assume allowed
                self.robots_cache[domain] = None
        
        robots = self.robots_cache[domain]
        if robots:
            return robots.can_fetch('*', url)
        
        return True
    
    def respect_rate_limit(self, domain: str):
        """Respect rate limiting for domain."""
        if domain in self.last_request:
            elapsed = time.time() - self.last_request[domain]
            if elapsed < self.delay:
                sleep_time = self.delay - elapsed
                time.sleep(sleep_time)
        
        self.last_request[domain] = time.time()
    
    def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch and parse a web page."""
        if not self.can_fetch(url):
            logger.warning(f"Robots.txt disallows fetching: {url}")
            return None
        
        domain = extract_domain(url)
        self.respect_rate_limit(domain)
        
        try:
            response = self.client.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            return soup
            
        except httpx.RequestError as e:
            logger.error(f"Request error for {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    def extract_article_links(self, soup: BeautifulSoup, base_url: str, 
                            patterns: List[str] = None) -> List[str]:
        """Extract article links from page."""
        links = set()
        
        # Find all links
        for link in soup.find_all('a', href=True):
            href = link['href']
            full_url = urljoin(base_url, href)
            
            # Filter by patterns if provided
            if patterns:
                if any(pattern in full_url for pattern in patterns):
                    links.add(full_url)
            else:
                # Default: look for news/article patterns
                if any(keyword in full_url.lower() for keyword in 
                      ['news', 'article', 'story', 'transfer', 'football', 'soccer']):
                    links.add(full_url)
        
        return list(links)
    
    def scrape_site_links(self, site_config: Dict) -> List[str]:
        """Scrape links from a website configuration."""
        base_url = site_config['url']
        paths = site_config.get('paths', ['/'])
        
        all_links = []
        
        for path in paths:
            full_url = urljoin(base_url, path)
            soup = self.fetch_page(full_url)
            
            if soup:
                links = self.extract_article_links(soup, full_url)
                all_links.extend(links)
        
        # Remove duplicates and sort by recency (assume newer URLs have higher IDs/dates)
        unique_links = list(set(all_links))
        unique_links.sort(reverse=True)
        
        logger.info(f"Found {len(unique_links)} links from {site_config['name']}")
        return unique_links[:50]  # Limit to recent 50 articles
    
    def fetch_all_sites(self, site_configs: List[Dict]) -> List[str]:
        """Fetch article links from all configured sites."""
        all_links = []
        
        for config in site_configs:
            try:
                links = self.scrape_site_links(config)
                all_links.extend(links)
            except Exception as e:
                logger.error(f"Error scraping {config.get('name', 'unknown')}: {e}")
                continue
        
        return all_links
    
    def __del__(self):
        """Clean up HTTP client."""
        if hasattr(self, 'client'):
            self.client.close()
