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
    
    def format_post(self, title: str, summary: str, source_url: str, 
                   hashtags: List[str] = None, news_type: str = "NEUTRAL",
                   footer_template: str = "Kaynak: {source}") -> str:
        """Format a complete social media post with improved content quality."""
        hashtags = hashtags or []
        
        # Clean and validate inputs
        title = title.strip() if title else ""
        summary = summary.strip() if summary else ""
        
        # Ensure we have meaningful content
        if not title and not summary:
            return "Haber içeriği bulunamadı."
        
        # If title is too short or meaningless, use summary as title
        if len(title) < 20 and len(summary) > len(title):
            title = summary
            summary = ""
            
        # Additional quality checks for title
        if title and (title.endswith('...') or title.endswith('.') and len(title) < 30):
            # If title seems incomplete, try to use summary
            if summary and len(summary) > len(title):
                title = summary
                summary = ""
        
        # Format source
        domain = extract_domain(source_url)
        footer = footer_template.format(source=domain)
        
        # Format hashtags
        hashtag_text = self.format_hashtags(hashtags)
        
        # Build post components
        prefix = ""
        if news_type == "OFFICIAL":
            prefix = "RESMİ: "
        elif news_type == "RUMOR":
            prefix = "SÖYLENTİ: "
        
        # Calculate available space
        fixed_parts = f" {footer}"
        if hashtag_text:
            fixed_parts += f" {hashtag_text}"
        
        fixed_length = self.calculate_length(fixed_parts)
        available_length = self.max_length - fixed_length - len(prefix) - 5  # Buffer
        
        # Combine title and summary intelligently
        content = title
        if summary and summary.lower() != title.lower() and len(summary) > 20:
            # Add summary if different from title and meaningful
            potential_content = f"{title}. {summary}"
            if self.calculate_length(potential_content) <= available_length:
                content = potential_content
            else:
                # Try to fit at least part of summary
                remaining_space = available_length - self.calculate_length(title) - 2
                if remaining_space > 30:  # Only add if we have meaningful space
                    truncated_summary = self.truncate_text(summary, remaining_space)
                    if len(truncated_summary) > 20:  # Only if meaningful length
                        content = f"{title}. {truncated_summary}"
        
        # Ensure content ends properly
        if content and not content.endswith(('.', '!', '?')):
            # Find last complete sentence
            sentences = content.split('.')
            if len(sentences) > 1:
                content = '. '.join(sentences[:-1]) + '.'
            else:
                content += '.'
        
        # Build final post
        post_parts = [prefix + content, footer]
        if hashtag_text:
            post_parts.append(hashtag_text)
        
        final_post = " ".join(part for part in post_parts if part)
        
        # Final length check and truncation if needed
        if self.calculate_length(final_post) > self.max_length:
            # Emergency truncation - preserve sentence structure
            excess = self.calculate_length(final_post) - self.max_length + 3
            if len(content) > excess:
                content = content[:-excess] + "..."
                # Ensure it ends at word boundary
                last_space = content.rfind(' ')
                if last_space > len(content) - 20:
                    content = content[:last_space] + "..."
                post_parts[0] = prefix + content
                final_post = " ".join(part for part in post_parts if part)
        
        return final_post
    
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
