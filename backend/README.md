# QoDe Backend & AI Entegrasyon Katmanı

Bu klasör, Teknofest 2026 5G ve Yapay Zeka ile Akıllı Yol Güvenliği yarışması için geliştirilen, mobil uygulama ile yarışma VM'indeki AI modellerini ve Turkcell Open Gateway servislerini birbirine bağlayan ana köprüdür (Middleware).

## Mimari Yapı
```mermaid
graph TD
    A[Mobil Uygulama (Native Android/Kotlin)] -->|HTTP| B(FastAPI Backend)
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
Yerel API smoke'u GPU olmadan açılabilir. AI inference ise Docker daemon/image
yoksa **FAILED** olur; sahte `results.json` üretmez.
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt pytest
cd backend
uvicorn app:app --host 0.0.0.0 --port 8000
```

## Yarışma VM'i

VM adresi, SSH hesabı, private key/parola ve Open Gateway secret değerleri repoya
yazılmaz. Takımın ürettiği, checksum/digest ile dondurulmuş
`teknofest-2026/qode-final:<frozen-tag>` image'ı kullanılır; `latest` kullanılmaz.
P5 canlı kurulum sırası ve komiteden beklenecek alanlar
[`docs/final_stage/pending_implementation_info_sheet.md`](../docs/final_stage/pending_implementation_info_sheet.md)
dosyasındadır.

## Testler (Unit Tests)
Proje, hatalara karşı kapsamlı bir test paketi içerir. Testleri çalıştırmak için:
```bash
cd backend
PYTHONPATH=. python -m pytest tests
```

> Mevcut `/auth/token`, `/nv/verify`, `/qod/session`, `/upload`, `/ai-run` ve
> `/ai-result` yüzeyi P5 öncesi uyumluluk yüzeyidir. Open Gateway access token'ının
> mobilden backend'e taşındığı bu sözleşme production/final kabul edilmez; P5'te
> backend-owned OIDC session ve job-id tabanlı API ile değiştirilecektir.
