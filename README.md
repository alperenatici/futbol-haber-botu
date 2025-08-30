# Futbol Haber Botu 🤖⚽

Otomatik Türkçe futbol haberleri için X/Twitter botu. RSS kaynaklarından ve web sitelerinden futbol haberlerini toplar, sınıflandırır, özetler ve görsellerle birlikte X'te paylaşır.

## Özellikler

- 📰 **Çoklu Kaynak Desteği**: RSS feeds ve web scraping
- 🔍 **Akıllı Sınıflandırma**: Resmi vs söylenti haberleri
- 📝 **Türkçe Özetleme**: LexRank algoritması ile
- 🎨 **Otomatik Görsel**: Metin kartları + CC lisanslı görseller
- 🚫 **Tekrar Önleme**: Akıllı deduplication sistemi
- ⏰ **Oran Sınırlama**: X API limitlerini koruma
- 🤖 **GitHub Actions**: Tam otomatik çalışma

## Kurulum

### 1. Projeyi İndirin

```bash
git clone https://github.com/kullanici/futbot.git
cd futbot
```

### 2. Python Ortamını Hazırlayın

```bash
# Python 3.11+ gerekli
python -m venv venv
source venv/bin/activate  # Linux/Mac
# veya
venv\Scripts\activate     # Windows

# Bağımlılıkları yükleyin
pip install -e .
```

### 3. Konfigürasyon

`data/sources.yaml` dosyasını düzenleyin:

```yaml
language: tr
rate_limits:
  min_minutes_between_posts: 10
  daily_post_cap: 30
sources:
  rss:
    - https://www.skysports.com/rss/12040
    - https://www.uefa.com/rssfeed/news/all.xml
  sites:
    - name: transfermarkt_news
      url: https://www.transfermarkt.com
      paths:
        - /transfers/news
```

### 4. API Anahtarları

Aşağıdaki ortam değişkenlerini ayarlayın:

```bash
# X/Twitter API (Gerekli)
export X_API_KEY="your_api_key"
export X_API_SECRET="your_api_secret"
export X_ACCESS_TOKEN="your_access_token"
export X_ACCESS_TOKEN_SECRET="your_access_token_secret"

# Openverse API (Opsiyonel - daha yüksek rate limit için)
export OPENVERSE_CLIENT_ID="your_client_id"
export OPENVERSE_CLIENT_SECRET="your_client_secret"
```

## Kullanım

### CLI Komutları

```bash
# Yardım
python -m app.main --help

# Bağlantı testi
python -m app.main test-connection

# Haberleri topla (dry run)
python -m app.main ingest --dry-run

# Tek tur çalıştır (dry run)
python -m app.main run-once --dry-run --max 5

# Canlı yayın (dikkatli kullanın!)
python -m app.main run-once --no-dry-run --max 3

# Bot durumu
python -m app.main status

# Eski kayıtları temizle
python -m app.main cleanup --days 30
```

### GitHub Actions ile Otomasyon

1. Repository'yi GitHub'a push edin
2. Repository Settings > Secrets and variables > Actions
3. Aşağıdaki secrets'ları ekleyin:
   - `X_API_KEY`
   - `X_API_SECRET`
   - `X_ACCESS_TOKEN`
   - `X_ACCESS_TOKEN_SECRET`
   - `OPENVERSE_CLIENT_ID` (opsiyonel)
   - `OPENVERSE_CLIENT_SECRET` (opsiyonel)

Bot otomatik olarak her 15 dakikada bir çalışacak.

## X/Twitter API Kurulumu

### 1. Developer Account

1. [developer.twitter.com](https://developer.twitter.com) adresine gidin
2. Developer hesabı oluşturun
3. Yeni bir App oluşturun

### 2. API Anahtarları

1. App Settings > Keys and Tokens
2. API Key & Secret'ı kopyalayın
3. Access Token & Secret oluşturun
4. Read and Write permissions ayarlayın

### 3. API v2 Erişimi

- Free tier: Aylık 1,500 tweet
- Basic tier ($100/ay): Aylık 50,000 tweet
- Media upload v1.1 API üzerinden

## Proje Yapısı

```
futbot/
├── app/
│   ├── classify/          # Haber sınıflandırma
│   ├── connectors/        # RSS ve web scraping
│   ├── extractors/        # İçerik çıkarma
│   ├── images/           # Görsel oluşturma
│   ├── publisher/        # X/Twitter yayınlama
│   ├── summarize/        # Türkçe özetleme
│   ├── utils/            # Yardımcı fonksiyonlar
│   ├── config.py         # Konfigürasyon
│   ├── main.py           # CLI interface
│   └── pipeline.py       # Ana pipeline
├── data/
│   ├── sources.yaml      # Haber kaynakları
│   ├── stopwords_tr.txt  # Türkçe stopwords
│   └── posted.db         # Yayınlanan haberler
├── tests/                # Test dosyaları
├── .github/workflows/    # GitHub Actions
└── README.md
```

## Özelleştirme

### Yeni Haber Kaynağı Ekleme

`data/sources.yaml` dosyasına yeni RSS feed veya website ekleyin:

```yaml
sources:
  rss:
    - https://yeni-kaynak.com/rss.xml
  sites:
    - name: yeni_site
      url: https://yeni-site.com
      paths:
        - /haberler
        - /transfer
```

### Takım Renkleri

`app/images/card.py` dosyasında `color_schemes` dictionary'sini düzenleyin:

```python
self.color_schemes = {
    'yeni_takim': {'bg': '#FF0000', 'text': '#FFFFFF', 'accent': '#000000'},
    # ...
}
```

### Sınıflandırma Kuralları

`app/classify/rumor_official.py` dosyasında keyword listelerini güncelleyin.

## Test

```bash
# Tüm testleri çalıştır
pytest

# Belirli test dosyası
pytest tests/test_pipeline.py

# Verbose output
pytest -v
```

## Sorun Giderme

### Yaygın Hatalar

1. **"X connection failed"**
   - API anahtarlarını kontrol edin
   - App permissions'ları kontrol edin (Read and Write)

2. **"Rate limit exceeded"**
   - `min_minutes_between_posts` değerini artırın
   - `daily_post_cap` değerini azaltın

3. **"No news items found"**
   - RSS feed'leri kontrol edin
   - İnternet bağlantısını kontrol edin

4. **"Media upload failed"**
   - Görsel dosya boyutunu kontrol edin
   - API v1.1 erişimini kontrol edin

### Log Dosyaları

```bash
# Log dosyasını görüntüle
tail -f logs/futbot.log

# Detaylı log ile çalıştır
python -m app.main run-once --verbose
```

## Güvenlik ve Uyumluluk

### Telif Hakları

- Openverse sadece CC lisanslı görseller kullanır
- Metin kartları orijinal içerik
- Kaynak belirtme zorunlu

### X/Twitter Kuralları

- Spam önleme mekanizmaları
- Rate limiting uyumu
- Automation Policy uyumu

### Veri Gizliliği

- API anahtarları environment variables'da
- Kişisel veri toplamaz
- GDPR uyumlu

## Katkıda Bulunma

1. Fork edin
2. Feature branch oluşturun (`git checkout -b feature/yeni-ozellik`)
3. Commit edin (`git commit -am 'Yeni özellik eklendi'`)
4. Push edin (`git push origin feature/yeni-ozellik`)
5. Pull Request oluşturun

## Lisans

MIT License - Detaylar için `LICENSE` dosyasına bakın.

## Destek

- 🐛 Bug reports: GitHub Issues
- 💡 Feature requests: GitHub Discussions
- 📧 İletişim: [alperenatici@icloud.com]

## Changelog

### v0.1.0 (2024-01-01)
- İlk sürüm
- RSS ve web scraping desteği
- Türkçe sınıflandırma ve özetleme
- X/Twitter entegrasyonu
- GitHub Actions otomasyonu

---

**Not**: Bu bot eğitim ve araştırma amaçlıdır. Ticari kullanım için ilgili API'lerin terms of service'ini kontrol edin.
