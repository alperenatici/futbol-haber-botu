"""Hashing utilities for content identification."""

import hashlib
from typing import Union


def hash_content(content: str, algorithm: str = "sha256", length: int = 16) -> str:
    """Generate hash for content."""
    if not content:
        return ""
    
    # Normalize content
    normalized = content.lower().strip()
    normalized = ' '.join(normalized.split())  # Remove extra whitespace
    
    # Generate hash
    if algorithm == "md5":
        hasher = hashlib.md5()
    elif algorithm == "sha1":
        hasher = hashlib.sha1()
    else:
        hasher = hashlib.sha256()
    
    hasher.update(normalized.encode('utf-8'))
    return hasher.hexdigest()[:length]


def hash_url(url: str) -> str:
    """Generate hash for URL."""
    return hash_content(url, length=12)


def generate_id(title: str, url: str) -> str:
    """Generate unique ID for news item."""
    combined = f"{title}|{url}"
    return hash_content(combined, length=8)
