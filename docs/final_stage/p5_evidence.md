# P5 gerçek Open Gateway ve final backend kanıtı

**Tarih:** 7 Ağustos 2026
**Durum:** Yazılım/contract kapısı tamamlandı; gerçek callback, final SIM, QoD cevabı
ve frozen Docker image ile canlı ortam kabulü henüz dış kanıt bekliyor.

## Uygulanan sözleşme

- Ignored root `.env` hem eski `OGW_*` anahtarlarını hem kanonik `OPENGW_*`
  alias'larını destekleyecek şekilde mutlak repo yolundan yüklenir. Secret değerler
  test/log/evidence çıktısına yazılmaz; VM credential alanları uygulama config'ine
  alınmaz.
- `GET /api/auth/start` kriptografik random, TTL'li state/flow üretir ve organizer
  scope'larıyla authorize URL'sine `302` döner.
- Callback state'i exchange çağrısından önce tek kullanımlık tüketir. Access token
  yalnız process-memory store'da ve `expires_in` süresince tutulur; hiçbir API
  response'una konmaz.
- Token exchange organizer Postman sözleşmesindeki Basic client auth ve exact form
  body ile yapılır.
- Number Verification E.164 veya SHA-256 identifier'dan tam birini kabul eder,
  unique `x-correlator` gönderir, false ve upstream hata durumlarını ayrıştırır.
- QoD exact organizer payload'ını `device` alanı olmadan gönderir. Upstream hata
  streaming'i durdurmaz; response açıkça `UNAVAILABLE`, `streamingAllowed=true` ve
  `fallbackMaxResolution=240p` taşır.
- Video upload yalnız verified flow'da, MP4 MIME/signature/size/ffprobe kontrolüyle,
  random job dizinine atomik olarak yazılır. Client filename path olarak kullanılmaz.
- Idempotency key flow bazında duplicate job'ı engeller. Metadata ve redact trace
  disk üzerinde; token process memory'de kalır. TTL cleanup ve toplam disk quota
  uygulanır.
- Container runner shell kullanmaz; frozen repository digest, offline network,
  read-only input, job-specific output, optional GPU ve 570 saniye timeout ister.
- Exit `0` yeterli değildir; ortak `competition.ftr` validator geçmeden job `DONE`
  olmaz.
- Eski access-token taşıyan/global-state `/auth/token`, `/nv/verify`, `/qod/session`,
  `/upload`, `/ai-run`, `/ai-result` endpoint'leri `410 Gone` döndürür.

## Kod yüzeyleri

- `src/smart_road_safety/integration/opengateway.py`
- `src/smart_road_safety/integration/auth.py`
- `backend/config.py`
- `backend/app.py`
- `backend/jobs.py`
- `backend/container_runner.py`
- `tests/test_opengateway_clients.py`
- `tests/test_gateway_auth_store.py`
- `backend/tests/test_final_backend.py`
- `backend/tests/test_container_runner.py`

## Doğrulama

```bash
PYTHONPATH=src backend/venv/bin/python -m unittest discover -s tests -v
cd backend
PYTHONPATH=.:../src venv/bin/python -m pytest -q tests
```

Contract testleri exact authorize/token/NV/QoD URL, header ve body alanlarını;
state replay/expiry, token expiry, NV-before-QoD state machine, QoD fail-open,
MP4 rejection, idempotency, path isolation, invalid result ve legacy endpoint
kapanışını kapsar.

7 Ağustos 2026 yerel doğrulama sonucu:

- core/unit suite: **94 test geçti**;
- final backend suite: **11 test geçti**;
- Python `compileall`: geçti;
- `git diff --check`: geçti;
- root `.env`: git tarafından ignore ediliyor; client id, client secret ve callback
  alanları değerleri yazdırılmadan dolu doğrulandı;
- local fake-transport API smoke: auth start `302`, callback `200`, NV `200`,
  QoD `201/AVAILABLE`, session `200`, response'larda access token yok.

Bu smoke gerçek operatör isteği değildir; yalnız backend state machine ve HTTP
sözleşmesinin yerel kanıtıdır.

## Canlı kabul için kalanlar

1. `.env` callback URI'sinin provider tarafında bire bir kayıtlı olduğunu doğrula.
2. Public callback portuna mobil şebekeden erişim smoke'u yap.
3. Android/browser üzerinden gerçek authorization code üret; backend callback ile
   token exchange'i tamamla. Token/authorization code evidence'a yazılmaz.
4. Final SIM ve maskeli MSISDN ile NV true/false kanıtı kaydet.
5. QoD için `201` ve `REQUESTED/AVAILABLE` ya da sağlayıcının redact edilmiş hata
   sonucunu kaydet; failure yolunda 240p streaming'in devam ettiğini göster.
6. `FINAL_AI_IMAGE` değerini frozen `teknofest-2026/...@sha256:<digest>` olarak
   kur; gerçek MP4 upload → PROCESSING → DONE → schema-valid result koş.
7. `out/final_stage/gateway/live-smoke-redacted.json` içinde yalnız flow/correlator,
   HTTP status, QoD status ve timestamp tut; token, secret, açık telefon, auth code
   veya VM credential tutma.

Bu yedi madde tamamlanmadan G5 live-smoke veya P5 fiziksel kabulü tamamlandı
denmeyecektir.
