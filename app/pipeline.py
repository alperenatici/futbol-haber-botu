"""Main pipeline for processing news items."""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path

from app.config import settings
from app.utils.logging import get_logger
from app.utils.dedupe import deduplicator
from app.connectors.rss import RSSConnector, NewsItem
from app.connectors.websites import WebsiteConnector
from app.connectors.social import social_connector
from app.extractors.article import ArticleExtractor
from app.classify.rumor_official import classifier, NewsType
from app.summarize.lexrank_tr import summarizer
from app.summarize.templates_tr import templates
from app.images.openverse import openverse_client
from app.images.card import card_generator
from app.publisher.x_client import x_client
from app.publisher.console_publisher import console_publisher
from app.publisher.formatter import formatter

logger = get_logger(__name__)


class ProcessedNewsItem:
    """Processed news item ready for publishing."""
    
    def __init__(self, original_item: NewsItem):
        self.original = original_item
        self.news_type: Optional[NewsType] = None
        self.confidence: float = 0.0
        self.summary_data: Optional[Dict] = None
        self.formatted_text: str = ""
        self.image_path: Optional[Path] = None
        self.openverse_image: Optional[Dict] = None
        self.post_result: Optional[Dict] = None


class NewsPipeline:
    """Main news processing pipeline."""
    
    def __init__(self):
        self.rss_connector = RSSConnector()
        self.website_connector = WebsiteConnector()
        self.article_extractor = ArticleExtractor()
        
    def ingest_news(self) -> List[NewsItem]:
        """Ingest news from all configured sources."""
        logger.info("Starting news ingestion...")
        
        all_items = []
        
        # Fetch RSS feeds
        rss_urls = settings.config.sources.rss
        
        if rss_urls:
            logger.info(f"Fetching {len(rss_urls)} RSS feeds")
            for i, url in enumerate(rss_urls):
                logger.info(f"RSS {i+1}/{len(rss_urls)}: {url}")
            rss_items = self.rss_connector.fetch_all_feeds(rss_urls)
            logger.info(f"RSS feeds returned {len(rss_items)} items")
            all_items.extend(rss_items)
        else:
            logger.warning("No RSS URLs configured")
        
        # Fetch website articles
        site_configs = settings.config.sources.sites
        if site_configs:
            logger.info(f"Scraping {len(site_configs)} websites")
            article_urls = self.website_connector.fetch_all_sites(site_configs)
            logger.info(f"Website scraping returned {len(article_urls)} URLs")
            
            # Extract articles from URLs
            if article_urls:
                extracted_items = self.article_extractor.extract_multiple(article_urls[:20])  # Limit to 20
                logger.info(f"Article extraction returned {len(extracted_items)} items")
                all_items.extend(extracted_items)
        else:
            logger.warning("No website configs found")
        
        # Skip social media due to X API limitations
        logger.info("Skipping social media (X API Free tier limitations)")
        
        logger.info(f"Total collected items before filtering: {len(all_items)}")
        
        # Filter recent items (last 24 hours)
        recent_items = []
        cutoff_time = datetime.now() - timedelta(hours=24)
        
        for item in all_items:
            if item.published_at and item.published_at > cutoff_time:
                recent_items.append(item)
            elif not item.published_at:  # Include items without date
                recent_items.append(item)
        
        logger.info(f"Ingested {len(all_items)} total items, {len(recent_items)} recent")
        return recent_items
    
    def deduplicate_items(self, items: List[NewsItem]) -> List[NewsItem]:
        """Remove duplicate news items."""
        logger.info("Deduplicating news items...")
        
        unique_items = []
        for item in items:
            if not deduplicator.is_duplicate(item.url, item.title, item.summary):
                unique_items.append(item)
        
        logger.info(f"Removed {len(items) - len(unique_items)} duplicates")
        return unique_items
    
    def classify_items(self, items: List[NewsItem]) -> List[ProcessedNewsItem]:
        """Classify news items as official/rumor/neutral."""
        logger.info("Classifying news items...")
        
        processed_items = []
        results = classifier.classify_batch(items)
        
        for item, news_type, confidence in results:
            processed = ProcessedNewsItem(item)
            processed.news_type = news_type
            processed.confidence = confidence
            processed_items.append(processed)
        
        # Log classification summary
        summary = classifier.get_classification_summary(items)
        logger.info(f"Classification summary: {summary}")
        
        return processed_items
    
    def summarize_items(self, items: List[ProcessedNewsItem]) -> List[ProcessedNewsItem]:
        """Summarize news items."""
        logger.info("Summarizing news items...")
        
        for processed in items:
            try:
                summary_data = summarizer.summarize_news_item(processed.original)
                processed.summary_data = summary_data
                
                # Format for posting
                formatted_text = templates.format_post(
                    processed.summary_data['short_title'],
                    processed.summary_data['summary'],
                    processed.original.url,
                    processed.news_type
                )
                
                processed.formatted_text = formatter.clean_text_for_posting(formatted_text)
                
            except Exception as e:
                logger.error(f"Error summarizing item {processed.original.id}: {e}")
                # Fallback formatting
                processed.formatted_text = f"{processed.original.title}\n\nKaynak: {processed.original.source}"
        
        return items
    
    def generate_images(self, items: List[ProcessedNewsItem]) -> List[ProcessedNewsItem]:
        """Generate images for news items."""
        logger.info("Generating images...")
        
        for processed in items:
            try:
                # Try to find Openverse image if enabled
                if settings.config.license.image_preference == "openverse_only":
                    openverse_image = openverse_client.find_football_image(
                        processed.original.title,
                        processed.original.summary
                    )
                    processed.openverse_image = openverse_image
                
                # Generate text card
                image_path = card_generator.generate_card(
                    processed.summary_data['short_title'] if processed.summary_data else processed.original.title,
                    processed.summary_data['summary'] if processed.summary_data else processed.original.summary,
                    processed.news_type,
                    processed.original.source,
                    processed.openverse_image
                )
                
                processed.image_path = image_path
                
            except Exception as e:
                logger.error(f"Error generating image for item {processed.original.id}: {e}")
                processed.image_path = None
        
        return items
    
    def publish_items(self, items: List[ProcessedNewsItem], dry_run: bool = False) -> List[ProcessedNewsItem]:
        """Publish news items to X/Twitter."""
        if dry_run:
            logger.info("DRY RUN: Would publish the following items:")
            for i, processed in enumerate(items[:5]):  # Show first 5
                logger.info(f"{i+1}. {processed.formatted_text[:100]}...")
            return items
        
        logger.info("Publishing news items...")
        
        published_count = 0
        for processed in items:
            try:
                # Post to X API using v2 (Free tier supports 500 writes/month)
                result = x_client.post_news(
                    text=processed.formatted_text,
                    image_path=processed.image_path,
                    news_url=processed.original.url,
                    title=processed.original.title
                )
                
                if result:
                    processed.post_result = result
                    published_count += 1
                    logger.info(f"Published to X: {processed.original.title[:50]}...")
                else:
                    logger.warning(f"Failed to publish: {processed.original.title[:50]}...")
                
                # Small delay between posts
                import time
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error publishing item {processed.original.id}: {e}")
        
        logger.info(f"Published {published_count} items")
        return items
    
    def run_pipeline(self, dry_run: bool = False, max_items: int = 10) -> List[ProcessedNewsItem]:
        """Run the complete news pipeline."""
        logger.info("Starting news pipeline...")
        
        try:
            # Step 1: Ingest
            items = self.ingest_news()
            if not items:
                logger.info("No news items found")
                return []
            
            # Step 2: Deduplicate
            items = self.deduplicate_items(items)
            if not items:
                logger.info("No unique items after deduplication")
                return []
            
            # Limit items for processing
            items = items[:max_items]
            
            # Step 3: Classify
            processed_items = self.classify_items(items)
            
            # Step 4: Summarize
            processed_items = self.summarize_items(processed_items)
            
            # Step 5: Generate images
            processed_items = self.generate_images(processed_items)
            
            # Step 6: Publish
            processed_items = self.publish_items(processed_items, dry_run)
            
            logger.info("Pipeline completed successfully")
            return processed_items
            
        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            raise
        finally:
            # Cleanup old entries
            deduplicator.cleanup_old_entries()


# Global pipeline instance
pipeline = NewsPipeline()
