"""Deduplication utilities for news items."""

import hashlib
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Set, Optional
from urllib.parse import urlparse, parse_qs, urljoin

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class NewsDeduplicator:
    """Handles deduplication of news items."""
    
    def __init__(self):
        self.db_path = settings.data_dir / "posted.db"
        self._init_db()
    
    def _init_db(self):
        """Initialize the SQLite database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS posted_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url_hash TEXT UNIQUE NOT NULL,
                    content_hash TEXT NOT NULL,
                    original_url TEXT NOT NULL,
                    title TEXT NOT NULL,
                    posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    source TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_url_hash ON posted_items(url_hash)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_content_hash ON posted_items(content_hash)
            """)
    
    def normalize_url(self, url: str) -> str:
        """Normalize URL for consistent comparison."""
        parsed = urlparse(url.lower())
        
        # Remove common tracking parameters
        tracking_params = {
            'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
            'fbclid', 'gclid', 'ref', 'source', 'campaign'
        }
        
        query_params = parse_qs(parsed.query)
        filtered_params = {
            k: v for k, v in query_params.items() 
            if k.lower() not in tracking_params
        }
        
        # Rebuild query string
        if filtered_params:
            query_string = '&'.join(
                f"{k}={'&'.join(v)}" for k, v in filtered_params.items()
            )
        else:
            query_string = ''
        
        # Remove fragment
        normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        if query_string:
            normalized += f"?{query_string}"
        
        return normalized
    
    def hash_url(self, url: str) -> str:
        """Generate hash for URL."""
        normalized = self.normalize_url(url)
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()[:16]
    
    def hash_content(self, title: str, summary: str) -> str:
        """Generate hash for content with Turkish similarity detection."""
        # Normalize text for comparison
        content = f"{title.lower().strip()} {summary.lower().strip()}"
        # Remove extra whitespace and common words
        content = ' '.join(content.split())
        
        # Remove common Turkish words that might cause false duplicates
        turkish_common_words = {
            'bir', 'bu', 'şu', 'o', 've', 'ile', 'için', 'da', 'de', 'ta', 'te', 'den', 'dan', 'ten', 'tan',
            'nin', 'nın', 'nun', 'nün', 'in', 'ın', 'un', 'ün', 'e', 'a', 'ye', 'ya', 'i', 'ı', 'u', 'ü',
            'olan', 'oldu', 'olur', 'olacak', 'var', 'yok', 'gibi', 'kadar', 'daha', 'en', 'çok', 'az',
            'galatasaray', 'fenerbahçe', 'beşiktaş', 'trabzonspor', 'transfer', 'futbol', 'maç', 'takım',
            'oyuncu', 'teknik', 'direktör', 'antrenör', 'sezon', 'lig', 'süper', 'spor', 'haber', 'son'
        }
        words = [word for word in content.split() if word not in turkish_common_words and len(word) > 2]
        content = ' '.join(words)
        
        return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]
    
    def is_duplicate(self, url: str, title: str, summary: str) -> bool:
        """Check if item is a duplicate."""
        url_hash = self.hash_url(url)
        content_hash = self.hash_content(title, summary)
        
        with sqlite3.connect(self.db_path) as conn:
            # Check URL hash
            cursor = conn.execute(
                "SELECT 1 FROM posted_items WHERE url_hash = ?",
                (url_hash,)
            )
            if cursor.fetchone():
                logger.debug(f"Duplicate URL found: {url}")
                return True
            
            # Check content hash (more recent items only)
            cutoff = datetime.now() - timedelta(days=7)
            cursor = conn.execute(
                "SELECT 1 FROM posted_items WHERE content_hash = ? AND posted_at > ?",
                (content_hash, cutoff.isoformat())
            )
            if cursor.fetchone():
                logger.info(f"Duplicate content found: {title[:50]}...")
                return True
        
        return False
    
    def mark_as_posted(self, url: str, title: str, summary: str, source: str):
        """Mark item as posted."""
        url_hash = self.hash_url(url)
        content_hash = self.hash_content(title, summary)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO posted_items 
                   (url_hash, content_hash, original_url, title, source)
                   VALUES (?, ?, ?, ?, ?)""",
                (url_hash, content_hash, url, title, source)
            )
    
    def cleanup_old_entries(self, days: int = 30):
        """Remove old entries to keep database size manageable."""
        cutoff = datetime.now() - timedelta(days=days)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM posted_items WHERE posted_at < ?",
                (cutoff.isoformat(),)
            )
            deleted = cursor.rowcount
            
        if deleted > 0:
            logger.info(f"Cleaned up {deleted} old entries from database")
    
    def get_recent_posts(self, hours: int = 24) -> list:
        """Get recent posts for debugging."""
        cutoff = datetime.now() - timedelta(hours=hours)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """SELECT original_url, title, source, posted_at 
                   FROM posted_items 
                   WHERE posted_at > ? 
                   ORDER BY posted_at DESC""",
                (cutoff.isoformat(),)
            )
            return [dict(row) for row in cursor.fetchall()]


# Global deduplicator instance
deduplicator = NewsDeduplicator()
