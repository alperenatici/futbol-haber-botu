"""
Tweet processor for handling Twitter content
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime
import re

from app.translate.translator import TurkishTranslator
from app.models.news_item import NewsItem

logger = logging.getLogger(__name__)

class TweetProcessor:
    def __init__(self):
        self.translator = TurkishTranslator()
    
    def process_tweet(self, tweet: Dict) -> Optional[NewsItem]:
        """Process a single tweet into a NewsItem"""
        try:
            # Extract basic info
            text = tweet.get('text', '').strip()
            username = tweet.get('username', '')
            account_name = tweet.get('account_name', username)
            created_at = tweet.get('created_at')
            tweet_url = tweet.get('url', '')
            language = tweet.get('language', 'tr')
            
            if not text or len(text) < 20:
                logger.debug(f"Tweet too short from @{username}")
                return None
            
            # Clean tweet text
            cleaned_text = self._clean_tweet_text(text)
            
            # Translate if not Turkish
            if language != 'tr':
                translated_text = self.translator.translate_text(cleaned_text, source_lang=language)
                if translated_text and len(translated_text) > 10:
                    content = translated_text
                    title = self._extract_title_from_text(translated_text)
                else:
                    # Fallback to original if translation fails
                    content = cleaned_text
                    title = self._extract_title_from_text(cleaned_text)
            else:
                content = cleaned_text
                title = self._extract_title_from_text(cleaned_text)
            
            # Create summary (first sentence or first 100 chars)
            summary = self._create_summary(content)
            
            # Determine news type
            news_type = self._determine_news_type(content)
            
            # Create NewsItem
            news_item = NewsItem(
                title=title,
                content=content,
                summary=summary,
                url=tweet_url,
                source=account_name,
                published_date=created_at or datetime.utcnow(),
                category="sports",
                language="tr",
                news_type=news_type,
                confidence=0.8,  # High confidence for curated accounts
                metadata={
                    'original_username': username,
                    'tweet_id': tweet.get('id'),
                    'original_language': language,
                    'account_category': tweet.get('account_category', 'sports')
                }
            )
            
            logger.info(f"Processed tweet from @{username}: {title[:50]}...")
            return news_item
            
        except Exception as e:
            logger.error(f"Error processing tweet from @{username}: {e}")
            return None
    
    def _clean_tweet_text(self, text: str) -> str:
        """Clean tweet text from URLs, mentions, extra spaces"""
        # Remove URLs
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        
        # Remove excessive mentions (keep max 1)
        mentions = re.findall(r'@\w+', text)
        if len(mentions) > 1:
            # Keep only the first mention
            for mention in mentions[1:]:
                text = text.replace(mention, '', 1)
        
        # Remove excessive hashtags (keep max 2)
        hashtags = re.findall(r'#\w+', text)
        if len(hashtags) > 2:
            for hashtag in hashtags[2:]:
                text = text.replace(hashtag, '', 1)
        
        # Clean extra spaces
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def _extract_title_from_text(self, text: str) -> str:
        """Extract title from tweet text"""
        # Split by sentences
        sentences = re.split(r'[.!?]+', text)
        
        if sentences and len(sentences[0].strip()) > 10:
            title = sentences[0].strip()
            # Limit title length
            if len(title) > 100:
                title = title[:97] + "..."
            return title
        
        # Fallback: use first 80 characters
        if len(text) > 80:
            return text[:77] + "..."
        
        return text
    
    def _create_summary(self, text: str) -> str:
        """Create summary from tweet text"""
        # For tweets, summary can be the full text if it's not too long
        if len(text) <= 200:
            return text
        
        # Split by sentences and take first 2
        sentences = re.split(r'[.!?]+', text)
        if len(sentences) >= 2:
            summary = '. '.join(sentences[:2]).strip()
            if summary and not summary.endswith('.'):
                summary += '.'
            return summary
        
        # Fallback: truncate at word boundary
        if len(text) > 200:
            truncated = text[:197]
            last_space = truncated.rfind(' ')
            if last_space > 150:
                return truncated[:last_space] + "..."
        
        return text
    
    def _determine_news_type(self, text: str) -> str:
        """Determine if news is official, rumor, or neutral"""
        text_lower = text.lower()
        
        # Official indicators
        official_keywords = [
            'resmi', 'açıkladı', 'duyurdu', 'imzaladı', 'transfer oldu',
            'official', 'announced', 'confirmed', 'signed'
        ]
        
        # Rumor indicators  
        rumor_keywords = [
            'söylentisi', 'iddiası', 'söyleniyor', 'iddia ediliyor',
            'rumor', 'reportedly', 'allegedly', 'claims'
        ]
        
        if any(keyword in text_lower for keyword in official_keywords):
            return "OFFICIAL"
        elif any(keyword in text_lower for keyword in rumor_keywords):
            return "RUMOR"
        
        return "NEUTRAL"
    
    def process_tweets_batch(self, tweets: List[Dict]) -> List[NewsItem]:
        """Process multiple tweets into NewsItems"""
        news_items = []
        
        for tweet in tweets:
            news_item = self.process_tweet(tweet)
            if news_item:
                news_items.append(news_item)
        
        logger.info(f"Processed {len(news_items)} valid news items from {len(tweets)} tweets")
        return news_items
