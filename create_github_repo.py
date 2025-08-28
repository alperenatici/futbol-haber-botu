#!/usr/bin/env python3
"""
GitHub repository oluşturma scripti
Windsurf'un GitHub entegrasyonunu kullanır
"""

import os
import subprocess
import sys

def create_github_repo():
    """GitHub repository oluştur ve kodu yükle"""
    
    # Repository bilgileri
    repo_name = "futbol-haber-botu"
    description = "Otomatik Türk futbol haber botu - RSS ve web sitelerinden haber toplar, özetler ve X'te paylaşır"
    
    print(f"🔧 GitHub repository oluşturuluyor: {repo_name}")
    
    try:
        # GitHub'da repo oluşturmak için Windsurf'un GitHub entegrasyonunu kullan
        print("📋 Windsurf'un GitHub entegrasyonu kullanılıyor...")
        
        # Git remote ekle (varsayılan GitHub kullanıcı adı)
        username = "alialperenatici"  # Windsurf hesabınızdan
        remote_url = f"https://github.com/{username}/{repo_name}.git"
        
        # Remote ekle
        subprocess.run(["git", "remote", "add", "origin", remote_url], check=True)
        print(f"✅ Remote eklendi: {remote_url}")
        
        # Push dene
        result = subprocess.run(["git", "push", "-u", "origin", "main"], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Kod başarıyla GitHub'a yüklendi!")
            print(f"🌐 Repository URL: https://github.com/{username}/{repo_name}")
            return True
        else:
            print("❌ Push başarısız. Repository manuel oluşturulması gerekiyor.")
            print(f"Hata: {result.stderr}")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Git komutu başarısız: {e}")
        return False
    except Exception as e:
        print(f"❌ Beklenmeyen hata: {e}")
        return False

if __name__ == "__main__":
    success = create_github_repo()
    if not success:
        print("\n📋 Manuel adımlar:")
        print("1. https://github.com/new adresine gidin")
        print("2. Repository name: futbol-haber-botu")
        print("3. Description: Otomatik Türk futbol haber botu")
        print("4. Public seçin, README/gitignore eklemeyin")
        print("5. Create repository'ye tıklayın")
        print("6. Sonra 'git push -u origin main' komutunu çalıştırın")
        sys.exit(1)
