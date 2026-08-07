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
pip install -e .
cd backend
PYTHONPATH=../src:. uvicorn app:app --host 0.0.0.0 --port 8000
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
PYTHONPATH=.:../src python -m pytest tests
```

## P5 API sözleşmesi

| Endpoint | İşlev |
| --- | --- |
| `GET /api/auth/start` | Tek kullanımlık state üretip organizer authorize URL'sine yönlendirir |
| `GET /api/auth/callback` | Code exchange; token yalnız backend memory store'da tutulur |
| `GET /api/session/{flow_id}` | Maskeli NV/QoD durum özeti |
| `POST /api/number-verification/verify` | Backend-owned token ile gerçek NV |
| `POST /api/qod/sessions` | Gerçek QoD; upstream hata halinde açık 240p fail-open sonucu |
| `POST /api/videos` | Doğrulanmış flow için atomik/idempotent MP4 upload ve `202` job |
| `GET /api/jobs/{job_id}` | Job durumu |
| `GET /api/jobs/{job_id}/result` | Yalnız validator'dan geçmiş DONE sonucu |
| `GET /api/jobs/{job_id}/trace` | Secret içermeyen job trace |

Eski `/auth/token`, `/nv/verify`, `/qod/session`, `/upload`, `/ai-run` ve
`/ai-result` endpoint'leri access token'ı mobile taşıyan/global-state sözleşmeyi
yeniden kullanılmasın diye `410 Gone` döndürür. Android istemci P6'da yeni flow/job
sözleşmesine geçirilecektir.
