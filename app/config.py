"""Configuration management for the football news bot."""

import os
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class RateLimits(BaseModel):
    min_minutes_between_posts: int = 10
    daily_post_cap: int = 30


class RSSFeed(BaseModel):
    url: str
    name: str

class Sources(BaseModel):
    rss_feeds: List[RSSFeed] = Field(default_factory=list)
    sites: List[Dict[str, Any]] = Field(default_factory=list)
    
    @property
    def rss(self) -> List[str]:
        """Get RSS URLs for backward compatibility."""
        return [feed.url for feed in self.rss_feeds]


class License(BaseModel):
    image_preference: str = "openverse_only"  # 'card_only' | 'openverse_only'


class Post(BaseModel):
    hashtags: List[str] = Field(default_factory=lambda: ["#futbol", "#transfer", "#sakatlık"])
    footer: str = "Kaynak: {source}"
    rumor_badge: str = "SÖYLENTİ"
    official_badge: str = "RESMİ"


class Config(BaseModel):
    language: str = "tr"
    rate_limits: RateLimits = Field(default_factory=RateLimits)
    sources: Sources = Field(default_factory=Sources)
    license: License = Field(default_factory=License)
    post: Post = Field(default_factory=Post)


class Settings:
    """Global settings and configuration."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.data_dir = self.project_root / "data"
        self.logs_dir = self.project_root / "logs"
        self.temp_dir = self.project_root / "temp"
        
        # Create directories if they don't exist
        self.data_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)
        self.temp_dir.mkdir(exist_ok=True)
        
        # Load configuration
        self.config = self._load_config()
        
        # Environment variables for API keys
        self.x_api_key = os.getenv("X_API_KEY")
        self.x_api_secret = os.getenv("X_API_SECRET")
        self.x_access_token = os.getenv("X_ACCESS_TOKEN")
        self.x_access_token_secret = os.getenv("X_ACCESS_TOKEN_SECRET")
        self.openverse_client_id = os.getenv("OPENVERSE_CLIENT_ID")
        self.openverse_client_secret = os.getenv("OPENVERSE_CLIENT_SECRET")
        
    def _load_config(self) -> Config:
        """Load configuration from YAML file."""
        config_path = self.data_dir / "sources.yaml"
        
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                yaml_data = yaml.safe_load(f)
                
                # Manual mapping to fix rss_feeds -> rss issue
                sources_data = yaml_data.copy()
                if 'rss_feeds' in sources_data:
                    # Convert list of dicts to list of RSSFeed objects
                    rss_feeds = [RSSFeed(**item) for item in sources_data['rss_feeds']]
                    sources_data['rss_feeds'] = rss_feeds
                    del sources_data['rss_feeds']  # Remove after conversion
                    sources_data['rss_feeds'] = rss_feeds  # Add back converted
                
                # Create config with manual mapping
                config = Config(
                    sources=Sources(**sources_data),
                    license=License(**yaml_data.get('license', {})),
                    post=Post(**yaml_data.get('post', {}))
                )
                return config
        else:
            print(f"DEBUG: Config file not found at {config_path}")
            # Return default config
            return Config()
    
    def has_x_credentials(self) -> bool:
        """Check if X/Twitter credentials are available."""
        return all([
            self.x_api_key,
            self.x_api_secret,
            self.x_access_token,
            self.x_access_token_secret
        ])


# Global settings instance
settings = Settings()
