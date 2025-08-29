#!/usr/bin/env python3
"""Otomatik sürekli çalışan bot - 900 saniye aralıklarla."""

import time
import signal
import sys
from datetime import datetime
from typing import Optional

from app.utils.logging import setup_logging, get_logger
from app.pipeline import NewsPipeline
from app.utils.dedupe import deduplicator

# Logging ayarla
setup_logging("INFO")
logger = get_logger(__name__)

class AutoRunner:
    """900 saniye aralıklarla otomatik çalışan bot."""
    
    def __init__(self):
        self.pipeline = NewsPipeline()
        self.running = True
        self.cycle_count = 0
        
        # Graceful shutdown için signal handler
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Shutdown signal handler."""
        logger.info(f"Shutdown signal alındı: {signum}")
        self.running = False
    
    def run_single_cycle(self):
        """Tek döngü çalıştır - haber kontrol et ve paylaş."""
        try:
            self.cycle_count += 1
            logger.info(f"=== Döngü {self.cycle_count} başlıyor ===")
            
            # Pipeline'ı çalıştır - gerçek paylaşım
            results = self.pipeline.run_pipeline(
                dry_run=False,  # Gerçek paylaşım aktif
                max_items=1     # Her seferinde sadece 1 haber
            )
            
            if results:
                posted_count = sum(1 for item in results if getattr(item, 'posted', False))
                logger.info(f"Döngü {self.cycle_count} tamamlandı: {len(results)} haber işlendi, {posted_count} haber paylaşıldı")
                
                if posted_count > 0:
                    # Haber paylaşıldı - benzerlik kontrolü için kaydet
                    for item in results:
                        if getattr(item, 'posted', False):
                            deduplicator.mark_as_posted(
                                item.original.url,
                                item.original.title,
                                item.original.summary or item.original.content[:200],
                                item.original.source
                            )
                            logger.info(f"Haber paylaşıldı ve kaydedildi: {item.original.title[:50]}...")
                else:
                    logger.info("Yeni paylaşılacak haber bulunamadı")
            else:
                logger.info("Döngü tamamlandı: Hiç haber bulunamadı")
                
        except Exception as e:
            logger.error(f"Döngü {self.cycle_count} hatası: {e}")
    
    def run_forever(self):
        """Sonsuz döngü - 900 saniye aralıklarla çalış."""
        logger.info("🤖 Otomatik bot başlatılıyor...")
        logger.info("📅 Her 15 dakikada (900 saniye) bir X hesapları kontrol edilecek")
        logger.info("🔄 Aynı haberler tekrar paylaşılmayacak")
        logger.info("⏰ Her haber paylaşımından sonra 900 saniye bekleniyor")
        logger.info("🛑 Durdurmak için Ctrl+C kullanın\n")
        
        # İlk döngüyü hemen başlat
        self.run_single_cycle()
        
        # Sonsuz döngü
        while self.running:
            try:
                logger.info(f"💤 900 saniye bekleniyor... (Sonraki döngü: {datetime.now().strftime('%H:%M:%S')})")
                
                # 900 saniye bekle (15 dakika)
                for i in range(900):
                    if not self.running:
                        break
                    time.sleep(1)
                
                if self.running:
                    self.run_single_cycle()
                    
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt alındı, kapatılıyor...")
                break
            except Exception as e:
                logger.error(f"Ana döngü hatası: {e}")
                logger.info("5 dakika bekleyip devam ediliyor...")
                time.sleep(300)  # 5 dakika bekle
        
        logger.info("🛑 Bot durduruldu")

def main():
    """Ana fonksiyon."""
    try:
        runner = AutoRunner()
        runner.run_forever()
    except Exception as e:
        logger.error(f"Bot başlatma hatası: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
