"""Time utilities for the football news bot."""

from datetime import datetime, timedelta
from typing import Optional
import pytz
from dateutil import parser as date_parser


def parse_date(date_string: str) -> Optional[datetime]:
    """Parse date string to datetime object."""
    if not date_string:
        return None
    
    try:
        # Try parsing with dateutil (handles most formats)
        dt = date_parser.parse(date_string)
        
        # If no timezone info, assume UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=pytz.UTC)
        
        return dt
    except (ValueError, TypeError):
        return None


def get_turkish_time() -> datetime:
    """Get current time in Turkish timezone."""
    turkey_tz = pytz.timezone('Europe/Istanbul')
    return datetime.now(turkey_tz)


def format_time_ago(dt: datetime) -> str:
    """Format time as 'X ago' string in Turkish."""
    if not dt:
        return "bilinmeyen zaman"
    
    now = datetime.now(pytz.UTC)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=pytz.UTC)
    
    diff = now - dt
    
    if diff.days > 0:
        if diff.days == 1:
            return "1 gün önce"
        return f"{diff.days} gün önce"
    
    hours = diff.seconds // 3600
    if hours > 0:
        if hours == 1:
            return "1 saat önce"
        return f"{hours} saat önce"
    
    minutes = diff.seconds // 60
    if minutes > 0:
        if minutes == 1:
            return "1 dakika önce"
        return f"{minutes} dakika önce"
    
    return "az önce"


def is_recent(dt: datetime, hours: int = 24) -> bool:
    """Check if datetime is within recent hours."""
    if not dt:
        return False
    
    now = datetime.now(pytz.UTC)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=pytz.UTC)
    
    return (now - dt) <= timedelta(hours=hours)


def can_post_now(last_post_time: Optional[datetime], min_minutes: int = 10) -> bool:
    """Check if enough time has passed since last post."""
    if not last_post_time:
        return True
    
    now = datetime.now(pytz.UTC)
    if last_post_time.tzinfo is None:
        last_post_time = last_post_time.replace(tzinfo=pytz.UTC)
    
    return (now - last_post_time) >= timedelta(minutes=min_minutes)
