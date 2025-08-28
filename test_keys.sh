#!/bin/bash

# Test için API anahtarlarını ayarla
# Bu dosyayı düzenleyip gerçek anahtarlarınızı yazın

echo "API anahtarlarını test için ayarlıyor..."

# Twitter API v1.1 anahtarları (mevcut)
export X_API_KEY="BURAYA_API_KEY_YAZIN"
export X_API_SECRET="BURAYA_API_SECRET_YAZIN"
export X_ACCESS_TOKEN="BURAYA_ACCESS_TOKEN_YAZIN"
export X_ACCESS_TOKEN_SECRET="BURAYA_ACCESS_TOKEN_SECRET_YAZIN"

# OAuth 2.0 anahtarları (yeni)
export X_CLIENT_ID="WUxyNGx6dXpOZ2xIY19RcmZFSTE6MTpjaQ"
export X_CLIENT_SECRET="2ugYPdhSdH7XZWeW5tWFkuELHKxeZBCq4bS_HD1s8Wak_GwNXS"

echo "✅ Tüm anahtarlar ayarlandı!"
echo ""
echo "Test komutu:"
echo "python3 -m app.main test-connection"
