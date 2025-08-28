"""Console publisher for testing without X API limitations."""

from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime
from app.utils.logging import get_logger
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

logger = get_logger(__name__)
console = Console()


class ConsolePublisher:
    """Publisher that outputs to console instead of X/Twitter."""
    
    def __init__(self):
        self.published_count = 0
        self.last_post_time = None
    
    def can_post(self) -> bool:
        """Always allow posting to console."""
        return True
    
    def upload_media(self, image_path: Path) -> Optional[str]:
        """Simulate media upload."""
        if image_path.exists():
            console.print(f"📷 [green]Medya yüklendi:[/green] {image_path.name}")
            return f"console_media_{image_path.stem}"
        return None
    
    def post_tweet(self, text: str, media_ids: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """Post tweet to console."""
        try:
            self.published_count += 1
            self.last_post_time = datetime.now()
            
            # Create styled output
            panel_title = f"🐦 Tweet #{self.published_count}"
            
            # Add media indicator
            if media_ids:
                text_with_media = f"{text}\n\n📷 [dim]Medya: {', '.join(media_ids)}[/dim]"
            else:
                text_with_media = text
            
            # Display tweet
            panel = Panel(
                Text(text_with_media, style="white"),
                title=panel_title,
                title_align="left",
                border_style="blue",
                padding=(1, 2)
            )
            
            console.print(panel)
            console.print(f"[green]✓ Tweet başarıyla konsola gönderildi![/green]\n")
            
            return {
                'id': f"console_{self.published_count}",
                'url': f"console://tweet/{self.published_count}",
                'text': text,
                'media_count': len(media_ids) if media_ids else 0,
                'timestamp': self.last_post_time.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Console tweet error: {e}")
            return None
    
    def post_news(self, text: str, image_path: Optional[Path] = None,
                  news_url: str = "", title: str = "") -> Optional[Dict[str, Any]]:
        """Post news to console."""
        try:
            # Upload media if provided
            media_ids = []
            if image_path:
                media_id = self.upload_media(image_path)
                if media_id:
                    media_ids.append(media_id)
            
            # Post tweet
            result = self.post_tweet(text, media_ids)
            
            if result:
                logger.info("News posted to console successfully")
                return result
            
            return None
            
        except Exception as e:
            logger.error(f"Error posting news to console: {e}")
            return None
    
    def test_connection(self) -> bool:
        """Test console connection."""
        console.print("[green]✓ Konsol bağlantısı başarılı[/green]")
        return True
    
    def get_recent_tweets(self, count: int = 5) -> List[Dict[str, Any]]:
        """Get recent console tweets."""
        return [
            {
                'id': f'console_{i}',
                'text': f'Konsol tweet örneği #{i}',
                'created_at': datetime.now(),
                'metrics': {'retweet_count': 0, 'favorite_count': 0}
            }
            for i in range(1, count + 1)
        ]


# Global console publisher instance
console_publisher = ConsolePublisher()
