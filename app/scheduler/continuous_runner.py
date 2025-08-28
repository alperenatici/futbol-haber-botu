"""Sürekli çalışan bot scheduler modülü."""

import time
import schedule
from datetime import datetime, timedelta
from typing import Optional
import signal
import sys

from app.utils.logging import get_logger
from app.pipeline import NewsPipeline
from app.config import settings

logger = get_logger(__name__)


class ContinuousRunner:
    """Bot'u sürekli çalıştıran scheduler sınıfı."""
    
    def __init__(self):
        self.pipeline = NewsPipeline()
        self.running = True
        self.last_run = None
        
        # Graceful shutdown için signal handler
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Shutdown signal handler."""
        logger.info(f"Shutdown signal received: {signum}")
        self.running = False
    
    def run_pipeline_job(self):
        """Pipeline'ı çalıştıran job fonksiyonu."""
        try:
            logger.info("Scheduled pipeline run başlıyor...")
            
            # Pipeline'ı çalıştır
            results = self.pipeline.run_pipeline(
                dry_run=False,
                max_items=5  # Her seferinde maksimum 5 haber
            )
            
            self.last_run = datetime.now()
            
            if results:
                posted_count = sum(1 for item in results if getattr(item, 'posted', False))
                logger.info(f"Pipeline tamamlandı: {len(results)} haber işlendi, {posted_count} haber paylaşıldı")
            else:
                logger.info("Pipeline tamamlandı: Yeni haber bulunamadı")
                
        except Exception as e:
            logger.error(f"Pipeline çalıştırma hatası: {e}")
    
    def setup_schedule(self):
        """Çalışma programını ayarla."""
        # Her 30 dakikada bir çalış
        schedule.every(30).minutes.do(self.run_pipeline_job)
        
        # Yoğun saatlerde daha sık çalış (09:00-22:00 arası her 15 dakika)
        schedule.every().hour.at(":00").do(self._check_peak_hours)
        schedule.every().hour.at(":15").do(self._check_peak_hours)
        schedule.every().hour.at(":30").do(self._check_peak_hours)
        schedule.every().hour.at(":45").do(self._check_peak_hours)
        
        logger.info("Scheduler ayarlandı: Her 30 dakikada bir çalışacak")
    
    def _check_peak_hours(self):
        """Yoğun saatlerde ek çalışma kontrolü."""
        now = datetime.now()
        if 9 <= now.hour <= 22:  # 09:00-22:00 arası
            logger.info("Yoğun saatlerde ek çalışma")
            self.run_pipeline_job()
    
    def run_continuous(self):
        """Sürekli çalışma modunu başlat."""
        logger.info("Bot sürekli çalışma modunda başlatılıyor...")
        
        # İlk çalışmayı hemen yap
        self.run_pipeline_job()
        
        # Schedule'ı ayarla
        self.setup_schedule()
        
        # Ana döngü
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Her dakika kontrol et
                
                # Sağlık kontrolü
                if self.last_run:
                    time_since_last = datetime.now() - self.last_run
                    if time_since_last > timedelta(hours=2):
                        logger.warning(f"Son çalışmadan {time_since_last} geçti")
                
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt alındı, kapatılıyor...")
                break
            except Exception as e:
                logger.error(f"Ana döngü hatası: {e}")
                time.sleep(300)  # 5 dakika bekle ve devam et
        
        logger.info("Bot durduruldu")
    
    def run_once(self, dry_run: bool = False, max_items: int = 10):
        """Tek seferlik çalışma."""
        logger.info(f"Bot tek seferlik çalışıyor (dry_run={dry_run}, max_items={max_items})")
        
        try:
            results = self.pipeline.run_pipeline(
                dry_run=dry_run,
                max_items=max_items
            )
            
            if results:
                posted_count = sum(1 for item in results if getattr(item, 'posted', False))
                logger.info(f"Tek seferlik çalışma tamamlandı: {len(results)} haber işlendi, {posted_count} haber paylaşıldı")
            else:
                logger.info("Tek seferlik çalışma tamamlandı: Yeni haber bulunamadı")
                
            return results
            
        except Exception as e:
            logger.error(f"Tek seferlik çalışma hatası: {e}")
            return []


# Global runner instance
continuous_runner = ContinuousRunner()


if __name__ == "__main__":
    # Komut satırından çalıştırılırsa sürekli mod
    continuous_runner.run_continuous()
