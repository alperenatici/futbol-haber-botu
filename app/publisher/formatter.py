"""Text formatting utilities for social media posts."""

import re
from typing import List, Optional
from urllib.parse import urlparse

from app.utils.logging import get_logger
from app.utils.text import count_characters_for_tweet, extract_domain

logger = get_logger(__name__)


class PostFormatter:
    """Format text for social media posts."""
    
    def __init__(self, max_length: int = 280):
        self.max_length = max_length
        self.url_length = 23  # Twitter's t.co URL length
    
    def shorten_url(self, url: str) -> str:
        """Return URL as-is (Twitter will auto-shorten)."""
        return url
    
    def format_hashtags(self, hashtags: List[str]) -> str:
        """Format hashtags for posting."""
        if not hashtags:
            return ""
        
        formatted = []
        for tag in hashtags:
            if not tag.startswith('#'):
                tag = f"#{tag}"
            # Remove spaces and special characters
            tag = re.sub(r'[^\w#]', '', tag)
            formatted.append(tag)
        
        return " ".join(formatted)
    
    def calculate_length(self, text: str) -> int:
        """Calculate effective length for Twitter."""
        return count_characters_for_tweet(text)
    
    def truncate_text(self, text: str, max_length: int) -> str:
        """Truncate text to fit within character limit."""
        if len(text) <= max_length:
            return text
        
        # Try to break at sentence boundary
        sentences = text.split('. ')
        if len(sentences) > 1:
            truncated = sentences[0] + '.'
            if len(truncated) <= max_length - 3:
                return truncated + '...'
        
        # Break at word boundary
        words = text.split()
        truncated = ""
        for word in words:
            test_text = f"{truncated} {word}".strip()
            if len(test_text) <= max_length - 3:
                truncated = test_text
            else:
                break
        
        return truncated + "..." if truncated else text[:max_length-3] + "..."
    
    def format_post(self, main_text: str, source_url: str = "", 
                   hashtags: List[str] = None, max_length: int = None) -> str:
        """Format complete social media post."""
        if max_length is None:
            max_length = self.max_length
        
        # Start with main text
        post_text = main_text.strip()
        
        # Add source if provided
        source_text = ""
        if source_url:
            domain = extract_domain(source_url)
            source_text = f"\n\nKaynak: {domain}"
        
        # Add hashtags if provided
        hashtag_text = ""
        if hashtags:
            hashtag_text = f" {self.format_hashtags(hashtags)}"
        
        # Combine all parts
        full_text = post_text + source_text + hashtag_text
        
        # Check if it fits
        if self.calculate_length(full_text) <= max_length:
            return full_text
        
        # Try without hashtags
        text_with_source = post_text + source_text
        if self.calculate_length(text_with_source) <= max_length:
            return text_with_source
        
        # Try with shorter source
        if source_url:
            short_source = f"\n\nKaynak: {extract_domain(source_url)}"
            text_with_short_source = post_text + short_source
            
            if self.calculate_length(text_with_short_source) <= max_length:
                return text_with_short_source
        
        # Truncate main text
        available_length = max_length
        if source_text:
            available_length -= len(source_text)
        if hashtag_text:
            available_length -= len(hashtag_text)
        
        truncated_main = self.truncate_text(post_text, available_length)
        final_text = truncated_main + source_text + hashtag_text
        
        return final_text
    
    def clean_text_for_posting(self, text: str) -> str:
        """Clean text for social media posting."""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove problematic characters
        text = text.replace('\u2028', ' ')  # Line separator
        text = text.replace('\u2029', ' ')  # Paragraph separator
        
        # Normalize quotes
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")
        
        return text


# Global formatter instance
formatter = PostFormatter()
