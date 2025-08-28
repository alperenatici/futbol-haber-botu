"""Text processing utilities."""

import re
from typing import List, Optional
from urllib.parse import urlparse


def clean_text(text: str) -> str:
    """Clean and normalize text."""
    if not text:
        return ""
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Remove HTML entities
    text = text.replace('&amp;', '&')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&quot;', '"')
    text = text.replace('&#39;', "'")
    
    return text


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to maximum length."""
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def extract_domain(url: str) -> str:
    """Extract domain from URL."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        # Remove www. prefix
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    except:
        return url


def normalize_title(title: str) -> str:
    """Normalize title for consistency."""
    title = clean_text(title)
    
    # Remove common prefixes/suffixes
    prefixes_to_remove = [
        "BREAKING:", "EXCLUSIVE:", "UPDATE:", "LATEST:",
        "SON DAKİKA:", "ÖZEL:", "GÜNCEL:"
    ]
    
    for prefix in prefixes_to_remove:
        if title.upper().startswith(prefix):
            title = title[len(prefix):].strip()
    
    return title


def extract_keywords(text: str, min_length: int = 3) -> List[str]:
    """Extract keywords from text."""
    # Simple keyword extraction
    words = re.findall(r'\b[a-zA-ZğüşıöçĞÜŞİÖÇ]+\b', text.lower())
    keywords = [word for word in words if len(word) >= min_length]
    
    # Remove duplicates while preserving order
    seen = set()
    unique_keywords = []
    for word in keywords:
        if word not in seen:
            seen.add(word)
            unique_keywords.append(word)
    
    return unique_keywords


def is_turkish_text(text: str) -> bool:
    """Check if text is likely Turkish."""
    turkish_chars = set('çğıöşüÇĞIİÖŞÜ')
    text_chars = set(text.lower())
    
    # If text contains Turkish characters, likely Turkish
    if turkish_chars & text_chars:
        return True
    
    # Check for common Turkish words
    turkish_words = {
        've', 'bir', 'bu', 'da', 'de', 'ile', 'için', 'olan', 'olarak',
        'futbol', 'takım', 'oyuncu', 'maç', 'gol', 'transfer'
    }
    
    words = set(re.findall(r'\b\w+\b', text.lower()))
    turkish_word_count = len(words & turkish_words)
    
    return turkish_word_count >= 2


def format_hashtags(hashtags: List[str]) -> str:
    """Format hashtags for social media."""
    if not hashtags:
        return ""
    
    # Ensure hashtags start with #
    formatted = []
    for tag in hashtags:
        if not tag.startswith('#'):
            tag = f"#{tag}"
        formatted.append(tag)
    
    return " ".join(formatted)


def count_characters_for_tweet(text: str) -> int:
    """Count characters for Twitter, accounting for URL shortening."""
    # Twitter shortens URLs to 23 characters
    url_pattern = r'https?://[^\s]+'
    urls = re.findall(url_pattern, text)
    
    # Replace URLs with 23-character placeholders
    text_without_urls = re.sub(url_pattern, 'x' * 23, text)
    
    return len(text_without_urls)
