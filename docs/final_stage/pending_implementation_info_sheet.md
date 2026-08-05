# Final aşama bekleyen işler ve bilgi talep föyü

**Durum tarihi:** 5 Ağustos 2026  
**Kapsam:** P5–P8, eksik P3/P4 fiziksel kabul kapıları ve model iyileştirme yolu  
**Kaynak plan:** [`../final_stage_implementation_plan.md`](../final_stage_implementation_plan.md)

Bu belge iki amacı birlikte taşır:

1. Takımın, yarışma komitesinden hangi bilgileri hangi formatta istemesi gerektiğini
   açıklar.
2. Bilgiler geldiğinde kod, model, Android, backend ve VM tarafında hangi sırayla
   uygulama/doğrulama yapılacağını kilitler.

VM IP'si, SSH kullanıcısı, private key/parola, `client_secret`, access/refresh token
ve açık MSISDN bu belgeye, Git'e, issue'a veya mesajlaşma kanalına yazılmaz.
`client_id` tek başına parola değildir; yine de `client_secret` ile birlikte yalnız
komitenin onayladığı güvenli kanaldan alınmalı ve VM secret store/env alanına
doğrudan kurulmalıdır.

---

## 1. Bugünkü doğrulanmış durum

### Acil güvenlik notu

Denetimde geçmiş bir commit içinde VM host/user/parolasının düz metin olarak
`scripts/deploy_vm.py` dosyasına yazıldığı görüldü. Çalışma ağacından kaldırıldı;
ancak Git geçmişinden silinmesi credential'ı tekrar güvenli yapmaz. İlgili VM
parolası/anahtarı **hemen rotate edilmeli**, aktif session'lar kapatılmalı ve erişim
logları kontrol edilmelidir. History rewrite ancak takım koordinasyonuyla, mevcut
clone/branch etkisi değerlendirilerek yapılmalıdır. Yeni deploy script'i yalnız
dışarıdan verilen `QODE_VM_HOST`, `QODE_VM_USER`, `QODE_VM_KEY_PATH` ve doğrulanmış
SSH host key kullanır.

| Alan | Durum | Sonraki geçiş kanıtı |
| --- | --- | --- |
| P0–P2 veri/GT/evaluator | Kod ve deterministik test yüzeyi mevcut | Değişiklik sonrası tüm suite ve gerçek manifest tekrar koşulur |
| P3 runtime asset sözleşmesi | Fail-closed manifest geri yüklendi | Dokuz asset checksum + class inspection geçmeli |
| Driver/smoker yeni HF dosyaları | Dosyalar var; yayımlanan TorchScript class metadata taşımıyor | Class-mapped checkpoint olarak yeniden export, upload ve manifest SHA güncelleme |
| P4 final Docker | Tekrar `final` moda alındı; eksik asset'te build fail eder | Dokuz asset ile offline build/run, üç video ve Web UI kanıtı |
| P5 Open Gateway/backend | Mevcut backend yalnız geçici uyumluluk scaffold'ı | Gerçek OIDC/NV/QoD contract testleri ve credential'lı smoke |
| P6 Android | Native Kotlin uygulama mevcut; final auth/job sözleşmesine bağlı değil | Gerçek cihazda OIDC → NV → QoD → HLS → MP4 → upload → result |
| P7 ortak yol/dokümantasyon | Kısmi | CLI/local API/backend aynı validator ve domain servislerini kullanmalı |
| P8 VM/freeze | VM bilgisi takımda; bu repoda tutulmayacak | İki prova, frozen digest/tar SHA, Web UI ve recovery drill |

Önemli ayrım: testlerin geçmesi yazılım sözleşmesini kanıtlar; GPU, gerçek SIM,
Open Gateway ve Web UI kabulünü kanıtlamaz.

---

## 2. Takımdan beklenen bilgiler ve kararlar

Bunlar secret olmadan paylaşılabilir. VM detaylarını bize vermeniz gerekmiyor.

1. **Open Gateway yazılı cevabının kopyası:** URL/scope/redirect kuralları ve hata
   örnekleri; secret değerler karartılmış olmalı.
2. **Callback'in dışarıdan görünen şekli:** IP'nin kendisi yerine gerekirse yalnız
   `http`/`https`, port ve path formatı (ör. `http://<host>:8080/api/auth/callback`).
3. **Final cihaz politikası:** Komitenin sağladığı SIM mi kullanılacak, tek cihaz mı,
   NV için E.164 numara mı hash mi gönderilecek? Açık numarayı repoya koymayın.
4. **Model/data kullanım izni:** Final/Faz 2 videosunun yalnız kalibrasyon için mi,
   eğitim için de mi kullanılabileceği ve başka takım/komite verisinin yayınlanıp
   yayınlanamayacağı.
5. **Eğitim kaynağı:** Kullanılabilir GPU türü ve yaklaşık saat bütçesi; veri kökleri
   ve boyutları. Credential veya özel veri paylaşmadan envanter yeterlidir.
6. **Model seçim hedefi:** Öncelik sırası (FTR accuracy, T4 üzerinde süre, image
   boyutu). Varsayılanımız: schema-valid sonuç ve `<10 dk` önce, accuracy sonra.
7. **Mobil test cihazı:** Android sürümü, cihaz modeli, boş disk ve final SIM ile
   gerçek cihaz testini yapacak owner.
8. **Operasyon owner'ları:** backend/VM, Android, model ve sunum operatörü.

---

## 3. Yarışma komitesine gönderilecek bilgi talebi

Aşağıdaki metin secret paylaşmayan, kopyalanabilir bir taleptir:

> **Konu: TEKNOFEST 2026 Open Gateway ve final VM entegrasyon bilgileri**
>
> Final entegrasyonumuzu tamamlayabilmemiz için aşağıdaki sözleşme ve provisioning
> bilgilerini yazılı olarak teyit etmenizi rica ederiz. `client_secret` gibi gizli
> değerlerin yalnız onaylı güvenli kanal/secret provisioning yöntemiyle iletilmesini
> rica ederiz.
>
> 1. Takımımıza tanımlanan OAuth/OIDC `client_id` ve `client_secret` provisioning
>    yöntemi; client authentication yöntemi (`client_secret_basic` vb.).
> 2. Exact authorize ve token endpoint'leri; Authorization Code Flow için zorunlu
>    `state`, PKCE, token expiry ve refresh-token davranışı.
> 3. Kaydedilmesi gereken exact redirect URI; izinli scheme/host/port/path ve callback
>    portu için allowlist/firewall gereksinimi.
> 4. Final authorize isteğinde kullanılacak exact scope listesi. Özellikle QoD için
>    `dpv:RequestedServiceProvision#quality-on-demand:sessions:create` ile
>    `quality-on-demand:sessions:create` farkının hangisinin geçerli olduğu.
> 5. Number Verification exact endpoint/version; `phoneNumber`/`hashedPhoneNumber`
>    kullanımı, test SIM/MSISDN-device binding'i, `x-correlator` zorunluluğu ve
>    beklenen hata/status kodları.
> 6. QoD exact endpoint/version; `qosProfile`, `duration` min/max,
>    `applicationServer` IPv4/subnet değeri, 3-legged token'da `device` alanı kuralı,
>    session status ve cleanup/delete beklentisi.
> 7. API rate limit, timeout/retry önerisi, bakım penceresi, TLS/CA/proxy/DNS/egress
>    kısıtları ve prova/final günü teknik escalation iletişim kanalı.
> 8. Final Docker image için zorunlu tag/prefix, CPU/GPU mimarisi ve NVIDIA
>    driver/CUDA uyumu; Web UI çalıştırma girdileri; teslim/freeze deadline'ının
>    exact saat dilimi ve image digest/SHA bildirim yöntemi.
> 9. Hidden evaluator timestamp toleransı, output schema revision ve canlı puanlama
>    alt kalemleri; Lifebox için resmi API varsa endpoint/auth dokümanı, yoksa manuel
>    share-sheet akışının kabul edilip edilmediği.
>
> Gerçek SIM/credential sağlanmadan fake-transport contract testlerimizi
> tamamlayacağız; ancak canlı NV/QoD kabul kapısını yalnız sağlanan credential ve
> final SIM ile kapatacağız.

### Komiteden gelmesi gereken cevap formatı

| Alan | Secret mi? | Repo'ya girer mi? | Kullanım |
| --- | --- | --- | --- |
| API root, endpoint, scope, redirect kuralı | Hayır | Doküman/fixture olarak evet | Contract freeze |
| `client_id` | Hassas tanımlayıcı | Hayır | VM env/secret store |
| `client_secret` | **Evet** | **Asla** | VM secret store |
| Test MSISDN/SIM bilgisi | **Evet/kişisel** | **Asla** | Canlı smoke; logda maskeli |
| Rate limit/status örnekleri | Hayır | Evet | Negative/retry testleri |
| VM credential/IP | **Evet** | **Asla** | Yalnız takım operasyonu |

---

## 4. Uygulama sırası: P5 gerçek gateway ve final backend

### P5.0 — Contract freeze

1. Komite cevabını `docs/final_stage/open_questions.md` içinde secret içermeden
   kapat.
2. Tek env sözleşmesi seç: API root, client id/secret, redirect URI, scopes,
   QoS profile, frozen image digest ve job root.
3. Startup validation ekle: production mod secret/redirect/image digest eksikse
   servis başlamasın; mock yalnız test config'iyle seçilebilsin.
4. Redaction testi yaz: bearer token, secret ve açık telefon log/trace'te yok.

**Kabul:** config contract testi geçer; production'da `mock-token` ve silent mock yok.

### P5.1 — Backend-owned OIDC session

1. `GET /api/auth/start`: kriptografik random `flow_id` ve tek kullanımlık `state`;
   TTL'li memory store; authorize redirect.
2. `GET /api/auth/callback`: code/state zorunlu; mismatch, expiry ve replay fail.
3. Token exchange yalnız backend'de; mobile'a Open Gateway access/refresh token
   dönmez. Mobile yalnız opaque flow/session handle veya güvenli cookie tutar.
4. `expires_in` takip edilir; expired token tekrar authorization ister.

**Testler:** exact authorize URL, Basic/body auth yöntemi, state replay, timeout,
401/403 ve token redaction.

### P5.2 — Number Verification

1. `POST /number-verification/v1/verify`; request'te E.164 veya hash'ten yalnız biri.
2. Her isteğe unique `x-correlator`.
3. `true`, `false`, `401`, `403`, `422`, timeout ve upstream 5xx ayrı domain
   sonuçlarına map edilir.
4. NV doğrulanmadan QoD/upload başlatılamaz.

**Kabul:** fake HTTP transport exact URL/header/body testleri + final SIM'de redact
edilmiş canlı smoke.

### P5.3 — QoD

1. Komitece teyit edilen `qosProfile`, application server ve duration ile session
   oluştur.
2. `201`, `sessionId`, `qosStatus` parse et; `REQUESTED`, `AVAILABLE`,
   `UNAVAILABLE` ayrıştır.
3. QoD timeout/unavailable mobil streaming'i durdurmaz; kalite 240p cap'e iner ve
   neden trace'e yazılır.
4. Komite isterse session cleanup/delete uygula.

**Kabul:** success ve fail-open contract testleri; canlı cevap secret içermeyen
evidence dosyasına yazılır.

### P5.4 — Job runner

1. `POST /api/videos`: MP4 signature/content-type/size kontrolü, random `job_id`,
   atomik upload, SHA256 ve duration probe; `202`.
2. Her job için `input/video.mp4`, `output/results.json`, metadata ve redact trace.
3. Frozen image **digest** ile read-only input/write-only output mount; shell string
   yok; fixed argv, GPU, disk quota ve 570 saniye timeout.
4. Exit `0` tek başına başarı değildir: `results.json` ortak FTR validator'dan
   geçmeden `DONE` olmaz.
5. `GET /api/jobs/{id}`, `/result`, `/trace`; process restart sonrası metadata
   recovery ve TTL cleanup.

**Kabul:** invalid/oversize/traversal/duplicate/timeout/nonzero/missing-output/invalid-
JSON testleri; iki paralel job birbirinin dosyasını göremez.

---

## 5. P6–P8 bekleyen uygulama sırası

### P6 — Android

1. Build-time `QODE_API_BASE_URL` kullan; source'a VM IP yazma.
2. Browser/OIDC redirect'i App Link/custom scheme ile backend flow'una bağla.
3. NV state olmadan QoD/video butonlarını aktif etme.
4. Media3 ile gerçek cihaz spike'ı: HLS playback → tam VOD download/cache → MP4
   export. 240p ve 1080p için duration, sync, seek, boyut ve wall time kaydet.
5. Media3 yolu çalışmazsa lisansı incelenmiş non-GPL FFmpeg fallback'i değerlendir;
   archived `ffmpeg-kit`i doğrudan ekleme.
6. Multipart upload progress/idempotency; job polling exponential backoff + manuel
   refresh; schema version kontrolü; raw JSON/trace ekranı.
7. Lifecycle, rotation, network switch, background ve duplicate tap testleri.

**Kabul:** final SIM ve gerçek cihazda NV; QoD success/high ve failure/240p; tam MP4
`<5 dk`; upload → `DONE/FAILED` sonucu.

### P7 — Tek domain yolu

1. Open Gateway domain contracts'ını HTTP katmanından ayır.
2. CLI, local API ve final backend aynı FTR validator/evaluator/exporter'ı import
   etsin; kopya scoring/schema yazma.
3. Local API endpoint'lerine plan matrisindeki `keep/shim/deprecate` kararlarını ve
   parity testlerini uygula.
4. Production request'ten sahte behavior boolean'larını ve auto-mock fallback'i
   kaldır.
5. README/Android/backend/runbook komutlarını temiz checkout'ta çalıştır.

### P8 — VM, prova ve freeze

1. Takım VM detaylarını yalnız yerel runbook/secret store'da kullanır; repoya
   yazmaz.
2. GPU driver/runtime, disk, Docker, callback portu, dış erişim ve Web UI preflight.
3. Low/high/mobile-recorded üç MP4: offline image, schema-valid, her biri `<10 dk`.
4. İki tam prova: NV success/fail, QoD success/fail-open, Android MP4, upload/job,
   Web UI inference, metrics ve recovery.
5. Tek frozen tag/digest; image ID, RepoDigest, tar SHA256, git SHA ve bütün model
   checksum'larını `out/final_stage/freeze/` altında kaydet.
6. Freeze sonrası model/code/image değişmez; backup restore smoke yapılır.

---

## 6. Modeli nasıl iyileştireceğiz?

### 6.1 Önce ölçüm: fine-tuning'e kör başlamayın

1. Dataset manifestlerine source, lisans, checksum, video/session/subject group id,
   label ve split ekle.
2. Split'i rastgele frame bazlı değil **video/session/kişi bazlı** yap. Aynı videonun
   komşu frame'leri train ve validation'a düşerse metric sızıntılıdır.
3. Faz 2 GT development calibration'dır; Faz 2 üzerinde eğitilen modelin Faz 2
   skoru holdout diye raporlanmaz.
4. Her label için precision/recall/F1, confusion matrix; event-level temporal F1;
   plate exact match; vehicle/color accuracy; ECE/calibration; T4 latency ve peak
   VRAM kaydet.
5. Önce current checkpoint baseline'ı, sonra yalnız tek değişkenli deneyler.

### 6.2 Driver action classifier

Contract sırası sabittir:

```text
arkaya_bakma, esneme, etrafa_bakinma, safe_driving,
sigara_icme, su_icme, telefonla_konusma
```

**Nasıl:** safe-driving negatifleri ve telefon/su/sigara/esneme hard-negative'leri
ekle; class-balanced sampler veya weighted CE kullan; önce backbone'u dondurup head,
sonra düşük LR ile son blokları aç; early stopping'i group holdout macro-F1'e bağla.
Brightness/contrast, blur, compression ve windshield augmentation kullan; davranışı
bozacak aşırı crop/flip'i görsel audit et. Output mutlaka
`model_state_dict + class_names + model_architecture` checkpoint'i olsun.

Faz 2 kalibrasyon örneği:

```bash
PYTHONPATH=src python3 scripts/finetune_faz2.py \
  --video <LOCAL_FAZ2_VIDEO> \
  --gt data/final_stage/faz2/ground_truth.json \
  --out data/finetune
PYTHONPATH=src python3 scripts/finetune_driver.py
```

Bu iki komut training-only aday üretir; holdout testi olmadan “iyileşti” denmez.

### 6.3 Smoker classifier

Runtime ve training aynı upper-driver ROI preprocessing'ini kullanmalı. Positive
sigara örneklerine karşı `telefon`, `su şişesi`, `el yüzde`, gölge, maske ve boş el
hard-negative'leri ekle. Kişi/video bazlı split, dengeli binary sampler, PR-AUC,
smoking recall ve false-positive/video metriklerini izle. Temperature scaling yalnız
ayrı calibration split'inde yapılır.

```bash
PYTHONPATH=src python3 scripts/train_smoker_classifier.py
PYTHONPATH=src python3 scripts/finetune_faz2_crops.py
```

### 6.4 Cabin detector

Bu en büyük açık head'dir. `emniyet_kemeri_ihlali`, `bilgisayar`, `arka_koltuk_1`,
`arka_koltuk_2`, `on_koltuk` için bbox/seat-region annotation üret. Koltuk kimliğini
yalnız kişi confidence'ından değil kalibre edilmiş kabin geometrisi/seat ROI ile
çıkar. Boş koltuk, örtü, çanta, kısmi kişi ve farklı kamera açılarını negative olarak
etiketle. YOLO detector + seat assignment postprocess'i ayrı ayrı değerlendir.

### 6.5 Araç rengi

KMeans/ortalama renk final head'i değildir. Vehicle mask/crop üzerinde color
constancy, gölge/parlama/gece augmentation ve dokuz sınıflı calibrated classifier
eğit. Split'i araç/video bazlı yap; beyaz-gri, siyah-gri, sarı-turuncu confusion'ını
ayrı raporla. Düşük confidence'ta sahte default renk üretme.

### 6.6 Plaka ve OCR

Detector recall ile OCR exact-match'i ayır. Türkiye plaka formatlı sentetik veri,
gerçek blur/perspective/compression ve karakter hard cases (`0/O`, `1/I`, `5/S`,
`8/B`) kullan. OCR bundle runtime'a offline girer. Plate-level exact match ve edit
distance ölç; regex düzeltmesi model skorunu gizlememeli.

### 6.7 Main detector ve temporal mantık

Küçük telefon/laptop nesneleri için resolution/tiling ve YOLO fine-tune deneyini
T4 runtime ile birlikte ölç. Sampling 3–5 FPS aralığında label-duration sensitivity
ile seçilsin. Persistence/debounce, episode gap ve slalom track parametreleri yalnız
development setinde tune edilip holdout'ta kilitli çalıştırılsın.

### 6.8 Her model adayı için release kapısı

1. Seed, dataset manifest SHA, git SHA, config ve base-weight revision kaydet.
2. Train/validation/holdout sonuçları ile inference latency/VRAM'i JSON'a yaz.
3. Eski adaya karşı label-bazlı regression tablosu çıkar; kritik label gerilerse
   toplam score artsa bile açık karar kaydı oluştur.
4. Class-mapped checkpoint export et; lokal class inspection ve runtime warm-up.
5. HF'ye immutable revision olarak upload et; remote SHA256 doğrula.
6. `config/runtime_assets.json` revision, URL, SHA ve model version güncelle.
7. Final asset checker, low/high inference, evaluator ve offline Docker koş.
8. Ancak bütün kapılar geçerse candidate/frozen image'a al.

Önerilen deney dizini:

```text
out/final_stage/experiments/<model>/<run-id>/
  config.json
  dataset-manifest.json
  metrics.json
  confusion-matrix.csv
  calibration.json
  runtime.json
  artifact.sha256
  decision.md
```

---

## 7. Uygulanabilir doğrulama komutları

```bash
# Python syntax/static smoke
PYTHONPATH=src python3 -m compileall -q src tests backend main.py scripts

# Ana unit/integration suite
PYTHONPATH=src python3 -m unittest discover -s tests -v

# Faz 2 manifest/GT
PYTHONPATH=src python3 -m smart_road_safety.cli check-manifest \
  data/final_stage/faz2/manifest.json
PYTHONPATH=src python3 -m smart_road_safety.cli validate-ftr-output \
  data/final_stage/faz2/ground_truth.json

# Final asset kapısı (eksik asset varsa exit 2 beklenir; başarı sayılmaz)
PYTHONPATH=src python3 -m smart_road_safety.cli check-runtime-assets \
  --manifest config/runtime_assets.json --asset-root data/weights --mode final

# Backend contract tests (dev ortamı kurulduktan sonra)
cd backend && PYTHONPATH=. python -m pytest tests && cd ..

# Android
cd apps/android && ./gradlew testDebugUnitTest lintDebug assembleDebug
```

Docker/GPU/Web UI ve live Gateway komutları yalnız takımın secret içermeyen yerel
runbook'unda, gerçek VM'de çalıştırılır. Evidence paylaşılırken token/MSISDN/IP
maskelenir.

---

## 8. Stop/go kontrol listesi

- [ ] Komite exact OAuth/scope/NV/QoD sözleşmesini yazılı teyit etti.
- [ ] Credential yalnız VM secret store'a kuruldu; repo/log/mobile'da yok.
- [ ] P5 contract/negative/redaction testleri yeşil.
- [ ] Final SIM ile NV ve QoD redact edilmiş canlı smoke mevcut.
- [ ] Android HLS→MP4 gerçek cihaz spike'ı `<5 dk`.
- [ ] Dokuz runtime asset immutable revision + checksum + class contract ile hazır.
- [ ] Low/high/mobile-recorded üç inference schema-valid ve `<10 dk`.
- [ ] Holdout metric olmadan model iyileştirme iddiası yapılmıyor.
- [ ] İki tam VM/Web UI provası ve recovery drill tamamlandı.
- [ ] Frozen image/model/git checksum'ları kaydedildi ve backup restore edildi.

Bu liste tamamlanmadan “competition ready” denmez; eksik satır dış blocker veya
test edilmemiş kapı olarak raporlanır.
