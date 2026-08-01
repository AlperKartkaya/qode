# QoDe Projesi Kullanım ve VM Dağıtım Kılavuzu

Bu belge, Teknofest 2026 "5G ve Yapay Zeka ile Akıllı Yol Güvenliği" yarışması için hazırlanan "QoDe" projesinin değerlendiriciler (jüriler) veya takım arkadaşları tarafından bir Ubuntu VM (Sanal Sunucu) üzerinde nasıl uçtan uca ayağa kaldırılacağını açıklamaktadır.

## 1. Sistem Gereksinimleri
- Ubuntu 20.04 veya 22.04 VM (Yarışma komitesi tarafından sağlanmış)
- NVIDIA GPU ve kurulu `nvidia-docker2` (Yapay zeka çıkarımı için zorunlu)
- Python 3.10 veya üzeri
- Açık (Public) IP Adresi

## 2. VM Kurulumu ve Projeyi Çekme
Sunucu kimlik bilgilerinizle SSH üzerinden bağlandıktan sonra projeyi VM'e indirin:
```bash
# Sunucuya bağlanın
ssh <kullanici_adi>@<sunucu_ip>

# Repoyu klonlayın (Eğer repo gizliyse GitHub Personal Access Token gerekebilir)
git clone https://github.com/AlperKartkaya/qode.git
cd qode
```

## 3. Ortam Değişkenlerini (Env) Ayarlama
Projeyi güvenli bir şekilde çalıştırmak için `.env` dosyalarını oluşturmalıyız. GitHub'da güvenlik sebebiyle bu dosyalar bulunmaz, sadece `.example` (şablon) halleri bulunur.

### Backend `.env` Ayarları
```bash
cp backend/.env.example backend/.env
nano backend/.env
```
Açılan dosyanın içinde aşağıdaki gibi alanları yarışmaya uygun şekilde doldurun:
```env
OGW_CLIENT_ID="yarışma_komitesi_tarafından_verilen_id"
OGW_CLIENT_SECRET="yarışma_komitesi_tarafından_verilen_secret"
BACKEND_CALLBACK_URL="http://<VM_PUBLIC_IP_ADRESINIZ>:8000/api/auth/callback"
```

## 4. Backend ve Yapay Zeka Modelini (Docker) Başlatma
Hazırladığımız `deploy.sh` betiği, komitenin beklediği **Docker Image SHA256** parmak izini çıkaracak ve FastAPI sunucusunu arka planda başlatacaktır.
```bash
chmod +x deploy.sh
./deploy.sh
```
Betik çalıştığında terminale bir **SHA256 Fingerprint** yazdıracaktır. Yarışma kuralları gereği bu kodu final gönderim (submission) sistemine eklemeyi unutmayın!

## 5. Mobil Uygulamayı (Client) Ayarlama
FastAPI sunucunuz artık VM üzerinde (örn: `http://203.0.113.50:8000`) çalışıyor. Mobil uygulamanın bu sunucuya bağlanabilmesi için kendi yerel bilgisayarınızda (Mac/PC) şu adımları izleyin:

```bash
cd apps/mobile
cp .env.example .env
nano .env
```
İçerisine VM'in IP adresini yazın:
```env
EXPO_PUBLIC_API_URL="http://<VM_PUBLIC_IP_ADRESINIZ>:8000"
```

Ardından uygulamayı başlatın veya APK/IPA build'i alın:
```bash
npm start -- -c
# Veya EAS ile build almak için:
# eas build -p android --profile preview
```

## 6. Sorun Giderme (Troubleshooting)
- **Sunucuya (8000 Portuna) Erişilemiyor:** VM'in güvenlik duvarında 8000 portunun açık olduğundan emin olun (`sudo ufw allow 8000/tcp`).
- **Docker "Permission Denied" Hatası:** Kullanıcınızın Docker grubunda olduğundan emin olun (`sudo usermod -aG docker $USER`).
- **GPU Bulunamadı (Fallback Mode):** Eğer VM'de GPU driver'ı eksikse veya `nvidia-smi` komutu çalışmıyorsa sistem çökmek yerine `Fallback Mode`'a girerek simülasyon sonuçları (dummy AI) üretecektir. Gerçek model testleri için GPU driverının düzgün kurulduğundan emin olun.
