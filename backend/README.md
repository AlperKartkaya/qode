# QoDe Backend & AI Entegrasyon Katmanı

Bu klasör, Teknofest 2026 5G ve Yapay Zeka ile Akıllı Yol Güvenliği yarışması için geliştirilen, mobil uygulama ile yarışma VM'indeki AI modellerini ve Turkcell Open Gateway servislerini birbirine bağlayan ana köprüdür (Middleware).

## Mimari Yapı
```mermaid
graph TD
    A[Mobil Uygulama (React Native)] -->|HTTP POST| B(FastAPI Backend)
    B -->|API Çağrısı| C{Open Gateway API}
    C -->|Number Verification| D[Numara Doğrulama]
    C -->|Quality on Demand| E[Bant Genişliği Önceliği]
    B -->|Docker API| F[AI Inference Container]
    F -->|Sonuç JSON| B
    B -->|HTTP GET| A
```

## Gereksinimler
- Python 3.10+
- Docker (NVIDIA GPU destekli `nvidia-docker2` - Yarışma VM'i için zorunlu)

## Kurulum (Yerel Test)
Yerel test ortamında GPU gerekmez, sistem `USE_GPU=False` mantığıyla çalışır.
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8000
```

## Kurulum (Yarışma VM - Canlı Ortam)
Yarışma komitesi tarafından verilen VM'e bağlanıp kurulum yapmak için:
1. `ssh kullanici@vm-ip` ile sunucuya bağlanın.
2. Bu kodları sunucuya çekin.
3. Komite tarafından verilen Docker imajının (örn: `teknofest-ai:latest`) VM üzerinde yüklü olduğundan emin olun.
4. `config.py` içerisindeki `docker_image_name` değişkenini komitenin imaj ismiyle güncelleyin.
5. Ortam değişkenlerinde (Environment Variables) GPU'yu aktif edin: `export USE_GPU=True`
6. `uvicorn app:app --host 0.0.0.0 --port 8000` komutuyla sunucuyu başlatın.

## Testler (Unit Tests)
Proje, hatalara karşı kapsamlı bir test paketi içerir. Testleri çalıştırmak için:
```bash
pip install -r requirements-dev.txt
pytest tests/
```
