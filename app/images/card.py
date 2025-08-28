"""Text card image generation for social media posts."""

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import textwrap
from typing import Optional, Tuple, Dict, Any
import colorsys

from app.config import settings
from app.utils.logging import get_logger
from app.classify.rumor_official import NewsType

logger = get_logger(__name__)


class CardGenerator:
    """Generate text cards for social media posts."""
    
    def __init__(self):
        self.card_size = (1200, 675)  # 16:9 aspect ratio for Twitter
        self.margin = 60
        self.content_width = self.card_size[0] - (2 * self.margin)
        
        # Color schemes for different teams/leagues
        self.color_schemes = {
            'galatasaray': {'bg': '#FFA500', 'text': '#8B0000', 'accent': '#FFD700'},
            'fenerbahce': {'bg': '#000080', 'text': '#FFFF00', 'accent': '#FFFFFF'},
            'besiktas': {'bg': '#000000', 'text': '#FFFFFF', 'accent': '#C0C0C0'},
            'trabzonspor': {'bg': '#800080', 'text': '#FFFFFF', 'accent': '#FFB6C1'},
            'barcelona': {'bg': '#A50044', 'text': '#004D98', 'accent': '#FFED02'},
            'real_madrid': {'bg': '#FFFFFF', 'text': '#000000', 'accent': '#FFD700'},
            'manchester_united': {'bg': '#DA020E', 'text': '#FFFFFF', 'accent': '#FFE500'},
            'liverpool': {'bg': '#C8102E', 'text': '#FFFFFF', 'accent': '#00B2A9'},
            'default': {'bg': '#1DA1F2', 'text': '#FFFFFF', 'accent': '#14171A'}
        }
    
    def detect_team_colors(self, text: str) -> Dict[str, str]:
        """Detect team from text and return appropriate colors."""
        text_lower = text.lower()
        
        for team, colors in self.color_schemes.items():
            if team != 'default' and team.replace('_', ' ') in text_lower:
                return colors
        
        return self.color_schemes['default']
    
    def create_gradient_background(self, size: Tuple[int, int], 
                                 color1: str, color2: str) -> Image.Image:
        """Create gradient background."""
        img = Image.new('RGB', size)
        draw = ImageDraw.Draw(img)
        
        # Convert hex colors to RGB
        def hex_to_rgb(hex_color):
            hex_color = hex_color.lstrip('#')
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        
        rgb1 = hex_to_rgb(color1)
        rgb2 = hex_to_rgb(color2)
        
        # Create vertical gradient
        for y in range(size[1]):
            ratio = y / size[1]
            r = int(rgb1[0] * (1 - ratio) + rgb2[0] * ratio)
            g = int(rgb1[1] * (1 - ratio) + rgb2[1] * ratio)
            b = int(rgb1[2] * (1 - ratio) + rgb2[2] * ratio)
            
            draw.line([(0, y), (size[0], y)], fill=(r, g, b))
        
        return img
    
    def get_font(self, size: int, bold: bool = False) -> ImageFont.ImageFont:
        """Get font with fallback to default."""
        try:
            # Try to use system fonts
            font_paths = [
                "/System/Library/Fonts/Arial.ttf",  # macOS
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
                "C:/Windows/Fonts/arial.ttf",  # Windows
            ]
            
            if bold:
                font_paths = [
                    "/System/Library/Fonts/Arial Bold.ttf",
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                    "C:/Windows/Fonts/arialbd.ttf",
                ]
            
            for font_path in font_paths:
                if Path(font_path).exists():
                    return ImageFont.truetype(font_path, size)
            
            # Fallback to default font
            return ImageFont.load_default()
            
        except Exception as e:
            logger.warning(f"Error loading font: {e}")
            return ImageFont.load_default()
    
    def wrap_text(self, text: str, font: ImageFont.ImageFont, 
                  max_width: int) -> list:
        """Wrap text to fit within specified width."""
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox = font.getbbox(test_line)
            width = bbox[2] - bbox[0]
            
            if width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    # Word is too long, force break
                    lines.append(word)
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines
    
    def create_badge(self, text: str, color: str, size: Tuple[int, int]) -> Image.Image:
        """Create a badge/label image."""
        badge = Image.new('RGBA', size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(badge)
        
        # Draw rounded rectangle
        draw.rounded_rectangle(
            [(0, 0), size],
            radius=15,
            fill=color,
            outline='white',
            width=2
        )
        
        # Add text
        font = self.get_font(16, bold=True)
        bbox = font.getbbox(text)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        text_x = (size[0] - text_width) // 2
        text_y = (size[1] - text_height) // 2
        
        draw.text((text_x, text_y), text, font=font, fill='white')
        
        return badge
    
    def generate_card(self, title: str, summary: str, news_type: NewsType,
                     source: str = "", openverse_image: Optional[Dict] = None) -> Path:
        """Generate a news card image."""
        try:
            # Detect colors
            colors = self.detect_team_colors(f"{title} {summary}")
            
            # Create base image with gradient
            img = self.create_gradient_background(
                self.card_size, 
                colors['bg'], 
                self._darken_color(colors['bg'], 0.3)
            )
            
            draw = ImageDraw.Draw(img)
            
            # Add semi-transparent overlay for better text readability
            overlay = Image.new('RGBA', self.card_size, (0, 0, 0, 100))
            img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
            draw = ImageDraw.Draw(img)
            
            # Title
            title_font = self.get_font(48, bold=True)
            title_lines = self.wrap_text(title, title_font, self.content_width)
            
            y_pos = self.margin
            for line in title_lines[:2]:  # Max 2 lines for title
                draw.text((self.margin, y_pos), line, font=title_font, fill=colors['text'])
                y_pos += 60
            
            # Summary
            y_pos += 30
            summary_font = self.get_font(28)
            summary_lines = self.wrap_text(summary, summary_font, self.content_width)
            
            for line in summary_lines[:3]:  # Max 3 lines for summary
                draw.text((self.margin, y_pos), line, font=summary_font, fill=colors['text'])
                y_pos += 40
            
            # News type badge
            if news_type != NewsType.NEUTRAL:
                badge_text = "RESMİ" if news_type == NewsType.OFFICIAL else "SÖYLENTİ"
                badge_color = "#28A745" if news_type == NewsType.OFFICIAL else "#FFC107"
                
                badge = self.create_badge(badge_text, badge_color, (120, 40))
                img.paste(badge, (self.card_size[0] - 140, 20), badge)
            
            # Source attribution
            if source:
                source_font = self.get_font(20)
                source_text = f"Kaynak: {source}"
                draw.text(
                    (self.margin, self.card_size[1] - 50), 
                    source_text, 
                    font=source_font, 
                    fill=colors['accent']
                )
            
            # Openverse image attribution (if provided)
            if openverse_image:
                attr_text = f"Fotoğraf: {openverse_image.get('creator', 'Unknown')}"
                attr_font = self.get_font(16)
                draw.text(
                    (self.margin, self.card_size[1] - 25), 
                    attr_text, 
                    font=attr_font, 
                    fill=colors['accent']
                )
            
            # Bot signature
            signature_font = self.get_font(18)
            draw.text(
                (self.card_size[0] - 150, self.card_size[1] - 30), 
                "@FutBot", 
                font=signature_font, 
                fill=colors['accent']
            )
            
            # Save image
            filename = f"card_{hash(title)}.png"
            file_path = settings.temp_dir / filename
            img.save(file_path, 'PNG', quality=95)
            
            logger.info(f"Generated card: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Error generating card: {e}")
            raise
    
    def _darken_color(self, hex_color: str, factor: float) -> str:
        """Darken a hex color by a factor."""
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        
        # Convert to HSV, reduce value, convert back
        hsv = colorsys.rgb_to_hsv(rgb[0]/255, rgb[1]/255, rgb[2]/255)
        new_hsv = (hsv[0], hsv[1], max(0, hsv[2] - factor))
        new_rgb = colorsys.hsv_to_rgb(*new_hsv)
        
        # Convert back to hex
        new_hex = '#{:02x}{:02x}{:02x}'.format(
            int(new_rgb[0] * 255),
            int(new_rgb[1] * 255),
            int(new_rgb[2] * 255)
        )
        
        return new_hex


# Global card generator instance
card_generator = CardGenerator()
