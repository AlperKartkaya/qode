# QODE Final Aşama Uygulama Planı

- **Plan tarihi:** 1 Ağustos 2026
- **Final:** 8–9 Ağustos 2026
- **AI image değişiklik son tarihi:** 7 Ağustos 2026, 21:00
- **Durum:** Uygulama öncesi kanonik plan
**Kapsam:** Faz 2 ground truth, düşük/yüksek çözünürlüklü video inference, mobil canlı demo, Open Gateway Number Verification ve Quality on Demand, backend, Docker/Web UI, değerlendirme ve final operasyonu

Bu dosya final aşaması için yapılacak işlerin sırasını, bağımlılıklarını, uygulanacağı kod yüzeylerini, kabul ölçütlerini ve doğrulama komutlarını tek yerde toplar. Kod değişikliğine başlanırken ilk referans bu plan ve `assumptions.md` olacaktır. Eski `docs/ktr_implementation_plan.md` geçmiş KTR/FTR çalışmasının kaydı olarak kalır; final operasyonunun güncel planı bu dosyadır.

---

## 1. Hedef sonuç ve tamamlanma tanımı

Finale hazır sistem aşağıdaki uçtan uca akışları gerçek sözleşmelerle çalıştırmalıdır:

1. Sağlanan Faz 2 HLS kaynağını düşük ve yüksek çözünürlükte indirir, envanterler ve yeniden üretilebilir bir manifest ile doğrular.
2. `faz2_gt` ground truth'unu yalnızca geliştirme/değerlendirme amacıyla kullanır; gizli/final videolarda ground truth sidecar'ı veya sabit sonuç üretmez.
3. Düşük çözünürlüklü, yüksek çözünürlüklü ve canlı yayından kaydedilmiş MP4 üzerinde gerçek inference çalıştırır.
4. Her koşuda `/app/data/input/video.mp4` girdisini okuyup en fazla 10 dakikada `/app/data/output/results.json` üretir.
5. `results.json` dosyasını kesin FTR şemasına göre doğrular ve araç, plaka, renk, sürücü eylemi, nesne ve yolcu etiketlerini gerçek model/temporal mantıktan üretir.
6. Mobil uygulamada OIDC Authorization Code Flow ile Number Verification yapar; doğrulama başarısızsa canlı demo akışını durdurur.
7. Doğrulama başarılıysa gerçek QoD session isteği yapar; QoD başarısızlığını streaming için engel haline getirmez.
8. Mobil uygulama HLS içeriğinin tamamını oynatır/kaydeder, en fazla 5 dakikada oynatılabilir MP4 olarak dışa aktarır ve backend'e yükler.
9. Backend yüklemeyi `202 Accepted` ile iş kuyruğuna alır, sabitlenmiş AI image'ı çalıştırır, sonucu doğrular ve mobil uygulamaya `PROCESSING`, `DONE` veya `FAILED` durumuyla sunar.
10. Yarışma VM'inde Web UI üzerinden `teknofest-2026/` önekli tek final image ile başarılı koşu yapılır; image SHA256 değeri 7 Ağustos 21:00'dan önce kayıt altına alınır.

**Tamamlanma koşulu:** Bölüm 13'teki G0–G8 kapılarının tamamı geçmiş, dış bağımlılıklar açıkça kaydedilmiş ve final runbook'u en az iki tam prova ile doğrulanmış olmalıdır.

---

## 2. Yeni kaynaklar ve değiştirdikleri gerçekler

### 2.1 Incoming staging dosyaları ve kanonik kaynak sırası

Repo köküne eklenen parantezli/boşluklu dosya adları **incoming staging adlarıdır**; kalıcı kod, manifest ve dokümantasyon bunlara bağlanmayacaktır. P0 tamamlanınca karşılıkları aşağıdaki kanonik path'ler olacaktır. Uygulama sırasında içerik çelişkisi olursa tablodaki öncelik sırası kullanılır:

| Öncelik | Incoming staging kaynağı | P0 sonrası kanonik path | Authority |
| ---: | --- | --- | --- |
| 1 | `Final Yarışma Senaryosu (1).pdf` | `docs/final_stage/final_yarisma_senaryosu.pdf` | Final operasyonu, süreler, canlı demo ve puanlama |
| 2 | `Yarışmacı Platformu Operasyon Rehberi (1).pdf` | `docs/final_stage/platform_operasyon_rehberi.pdf` | VM, Web UI, Docker image ve çalışma dizini sözleşmesi |
| 3 | `OpenGateway/OGW_Teknofest.pdf`, iki YAML ve Postman collection | `docs/final_stage/open_gateway/` | OIDC, Number Verification ve QoD request/response sözleşmeleri |
| 4 | `Open Gateway Demo - UX Akış Kılavuzu (1).pdf` | `docs/final_stage/open_gateway_demo_ux.pdf` | Mobil/backend ekran ve durum akışı |
| 5 | `faz2_gt (1).json` | `data/final_stage/faz2/ground_truth.json` | Faz 2 FTR ground truth'u |

P0 patch'i kanonik kopyaların checksum'ını staging dosyalarıyla karşılaştırıp bütün referansları güncelledikten sonra root-staging kopyalarını kaldıracaktır; repo içinde iki ayrı source of truth bırakılmayacaktır.

Ardından kaynak sırası şöyle devam eder:

6. FTR teslim dokümanı — kesin `results.json` şeması ve etiket sözlüğü.
7. Şartname ve mevcut KTR/FTR dokümanları — genel hedefler ve geçmiş kararlar.
8. Repo içindeki destek veri setleri ve yerel gözlemler — eğitim/iyileştirme girdileri; üstteki resmi kaynakların yerine geçmez.

### 2.2 Yeni dosyalardan sabitlenen gereksinimler

| Konu | Yeni gerçek | Uygulama etkisi |
| --- | --- | --- |
| Final tarihi | Final 8–9 Ağustos 2026; image değişiklik sonu 7 Ağustos 21:00 | Plan geri sayımlı yürütülecek; son gün özellik geliştirme yapılmayacak. |
| Değerlendirme | Düşük video %25, yüksek video %25, canlı demo %25, sunum %25 | AI doğruluğu kadar mobil/telekom/backend ve sunum da P0'dır. |
| Number Verification | Başarısızlık canlı demo puanını sıfırlar ve akışı durdurur; başarı +5 | NV, mock destek özelliği değil canlı demo kapısıdır. |
| QoD | Başarı ek +5; başarısızlık streaming'i durdurmaz | Orkestrasyon “fail-open for streaming” davranmalıdır. |
| Mobil kayıt | Stream'in tamamı en fazla 5 dakikada MP4 olarak dışa aktarılmalı | HLS kayıt/remux yolu ilk teknik risk olarak çözülmelidir. |
| AI çalıştırma | Üç video varyantının her biri en fazla 10 dakikada işlenir | Performans ölçümü ve timeout zorunludur. |
| Platform | Hakem yalnızca Web UI kullanır; CLI gösterimi değerlendirilmez | CLI geliştirme aracı olarak kalır, final kabulü Web UI ile yapılır. |
| Docker adı | Image adı `teknofest-2026/` ile başlamalı | README, script ve runbook aynı adı kullanmalıdır. |
| Girdi/çıktı | `/app/data/input/video.mp4` → `/app/data/output/results.json` | Container sözleşmesi değiştirilmeden korunmalıdır. |
| Ground truth | `faz2_gt` içinde 34 event ve tüm üç FTR event ailesi var | Gerçek temporal evaluator ve kalibrasyon fixture'ı eklenmelidir. |
| API dokümanı | OIDC, NV ve QoD endpoint/payload ayrıntıları mevcut | Gerçek client uygulanabilir; sadece credential/provisioning dış blokerdir. |

### 2.3 Canlı doğrulanan HLS özellikleri

1 Ağustos 2026 tarihli preflight kontrolünde master playlist erişilebilir durumdaydı ve iki varyant döndürdü:

`https://teknofest-arge-turkcell.ercdn.net/hls/4/pZ/faz2/faz2.smil/playlist.m3u8`

- 1920×1080, yaklaşık 9.16 Mbps;
- 426×240, yaklaşık 0.29 Mbps;
- her iki varyant 56 segment ve yaklaşık 113.92 saniye VOD içeriyor.

Bu değerler test fixture'ına körlemesine sabitlenmeyecek; indirme öncesi yeniden probe edilip manifest'e yazılacaktır. HLS URL'si veya segment sayısı değişirse araç açık hata vermeli, sessizce eski cache'i kullanmamalıdır.

---

## 3. Mevcut repo başlangıç durumu ve açık farklar

Bu plan yazılırken alınan baseline:

- `faz2_gt (1).json`, mevcut FTR validator ile **geçiyor** ve 34 tespit içeriyor.
- `data/real_dataset_manifest.json`, manifest checker'da **adaptation-needed** dönüyor; `nesneler`, `yolcular` ve exact plate text eksik.
- `PYTHONPATH=src python3 -m unittest discover -s tests -v`: **49 testten 46'sı geçiyor, 3'ü başarısız**.
  - Legacy screenshot fixture'ları artık diskte bulunmadığı için iki adapter/analysis testi fail ediyor.
  - DOCX rapor testinde görsel caption'ın düz metin extraction'ında bulunacağı varsayımı fail ediyor.
- `python3 -m compileall -q src tests`: **geçiyor**.
- Yerel final inference weight'leri eksik; mevcut Docker build bazı weight indirme hatalarını yalnızca uyarı olarak geçiriyor.
- `main.py` `data/` içinde tam bir MP4 bekliyor; mevcut kökte üç MP4 olduğu için varsayılan yerel çağrı fail ediyor.
- `main.py` yaklaşık 1 FPS örnekliyor; 0.89 saniyeden başlayan ve kısa süreli olayları kaçırma riski yüksek.
- `model_inference.py` içinde araç sınıfı, plaka crop'u, emniyet kemeri ve yolcu pozisyonu için sessiz veya heuristik fallback'ler var.
- `integration/` gerçek gateway interface'lerini taşıyor fakat çalışan uygulama ve `local_api` default olarak mock gateway kuruyor.
- `apps/mobile/README.md`, `services/api/README.md` ve `services/vision/README.md` rezerv/placeholder seviyesinde; çalışan mobil uygulama veya final backend yok.
- Mevcut README örnek image adı `teknofest/qode:latest`; final platformu için geçersiz.

**Başlangıç kuralı:** Bu üç mevcut test hatası önce gerçek repo durumu ile uzlaştırılacak. Yeni değişikliklerin üzerine “önceden de kırık” test borcu taşınmayacak.

---

## 4. Mimari kararlar

### 4.1 Ayrı sorumluluk sınırları

Final çözüm üç ayrı çalışma birimi olarak korunacaktır:

```text
Android uygulama
  ├─ OIDC/NV/QoD ekranları
  ├─ HLS oynatma + kayıt + MP4 export
  └─ upload / job status / result / trace
             │
             ▼
Final demo backend
  ├─ OIDC callback ve kısa ömürlü token/session store
  ├─ gerçek Open Gateway client'ları
  ├─ güvenli multipart upload ve inference job state
  └─ sabit argümanlı ContainerInferenceRunner
             │
             ▼
AI competition image
  ├─ yalnızca /app/data/input/video.mp4 okur
  ├─ model inference + temporal aggregation yapar
  └─ yalnızca /app/data/output/results.json üretir
```

AI competition image'a OAuth credential, mobil session state, backend web sunucusu veya yarışma günü ağ bağımlılığı eklenmeyecektir. Böylece hakem Web UI çalıştırması demo backend'den bağımsız ve deterministik kalır.

### 4.2 Gerçek yol ile fixture yolunun ayrılması

- `faz2_gt` bir **golden evaluation fixture**'ıdır; runtime prediction kaynağı değildir.
- Mock gateway'ler sadece unit test/offline demo için dependency injection ile seçilir.
- Gerçek modda credential eksikse açık `configuration error` verilir; otomatik mock fallback yapılmaz.
- Model weight'i eksikse final modunda container startup/build fail eder; düşük doğruluklu heuristiğe sessiz geçiş yapılmaz.
- Sidecar `vehicle_info.json` yalnızca açık geliştirme/fixture modunda kabul edilir; gizli video final çalışmasının parçası olamaz.

### 4.3 Yeni bağımlılık kararı

Mevcut local API stdlib tabanlıdır; multipart upload, OIDC redirect/callback, asenkron job lifecycle ve tutarlı hata modeli için yetersiz kalma riski vardır. Uygulama başlamadan küçük bir ADR hazırlanacaktır:

- **Önerilen backend yönü:** final demo backend'i `services/api/` altında ayrı, minimal bir HTTP uygulaması olarak kurmak; mevcut `src/smart_road_safety/local_api/` yüzeyini geliştirme/uyumluluk adapter'ı olarak korumak.
- **Karar kapısı:** yeni framework/dependency eklenmeden önce stdlib ile güvenli ve test edilebilir multipart/job çözümünün maliyeti ile minimal framework seçeneği karşılaştırılacak. Yeni bağımlılık ancak ADR'de gerekçe, sürüm, lisans ve image etkisi kaydedildikten sonra eklenecek.
- **Mobil yön:** repo içindeki mevcut tasarım Android uygulamayı işaret ettiği için varsayılan hedef native Android/Kotlin'dir. Ekipte ayrı bir çalışan mobil repo varsa yeniden scaffold etmek yerine bu sözleşmeler oraya taşınacaktır.

### 4.4 Repo boundary karar kapısı

`apps/mobile/` ve `services/api/` şu anda yalnız placeholder README içerdiği için, yeni iki ürün yüzeyi bu repoda kendiliğinden varmış gibi kabul edilmeyecektir. P0 sonunda `docs/final_stage/adr/0001-client-backend-boundary.md` oluşturulup şu kararlar kilitlenecektir:

1. Çalışan mobil uygulama başka bir repo'da mı? Varsa owner/build erişimi doğrulanır ve bu repo yalnız ortak API schema, fixture ve runbook'u taşır; ikinci bir Android uygulama üretilmez.
2. Mobil uygulama bu repo'da kurulacaksa Gradle wrapper, application ID, min/target SDK, CI build, debug APK ve cihaz smoke'u bootstrap kabul kriteri olur.
3. Backend başka bir deployable repo/service içinde mi? Varsa mevcut deploy yoluna adapter yazılır; aynı işi yapan ikinci server kurulmaz.
4. Backend bu repo'da kurulacaksa framework/stdlib ADR'si, dependency/lisans kararı, process modeli ve VM deploy biçimi P5'ten önce onaylanır.
5. Repo dışı yüzey seçilirse contract test fixture'ları burada tutulur ve ilgili commit/tag/artefact sürümü evidence'a bağlanır.

**Kapı:** Boundary ADR'si ve en az bir build/health smoke kanıtı olmadan P5 backend implementation'ı veya P6 ekran implementation'ı başlamaz.

---

## 5. Bağımlılık sırası ve çalışma kolları

### 5.1 Zorunlu sıra

```text
P0 kaynak/assumption kilidi
  → P1 kanonik final veri paketi ve manifest
    → P2 GT evaluator ve ölçülebilir baseline
      → P3 inference/model iyileştirmeleri
        → P4 final Docker image ve performans kapısı

P0 API sözleşme kilidi
  → P5 gerçek Open Gateway client + backend
    → P6 Android HLS/NV/QoD/upload/result akışı
      → P7 VM/Web UI tam prova

P4 + P6
  → P7 tam entegrasyon
    → P8 freeze, SHA256 ve final runbook
```

Assumptions ve ortak API/FTR sözleşmeleri kilitlendikten sonra şu dört kol paralel yürüyebilir:

| Kol | Sahiplik sınırı | Diğer kollarla birleşme noktası |
| --- | --- | --- |
| Veri/evaluation | `data/final_stage/`, manifest, GT evaluator ve testleri | AI prediction JSON'u ve rapor çıktısı |
| AI/runtime | `main.py`, `analysis/model_inference.py`, FTR builder, weights, Docker | Sabit `/input`–`/output` sözleşmesi |
| Gateway/backend | `integration/`, `orchestration/`, `services/api/` | Mobil API contract ve image runner |
| Android | `apps/mobile/` | Backend OpenAPI/JSON contract ve HLS kaynağı |

Ortak dosyalar (`assumptions.md`, `README.md`, `pyproject.toml`, FTR contract) tek bir entegrasyon sahibi üzerinden değiştirilecek; paralel kollarda aynı dosyaya bağımsız edit yapılmayacaktır.

---

## 6. Sıralı uygulama aşamaları

## P0 — Kaynak gerçekliğini ve varsayımları kilitle

**Amaç:** Kod değişmeden önce yeni resmi bilgiler ile eski assumptions arasındaki bütün çelişkileri kaldırmak.

### Yapılacaklar

1. Yeni dosyaların boşluk/parantez/Türkçe karakter içermeyen kanonik repo kopyalarını üret; byte-for-byte SHA256 eşleşmesini doğruladıktan ve bütün referansları güncelledikten sonra incoming root-staging kopyalarını kaldır:
   - `docs/final_stage/final_yarisma_senaryosu.pdf`
   - `docs/final_stage/platform_operasyon_rehberi.pdf`
   - `docs/final_stage/open_gateway_demo_ux.pdf`
   - `docs/final_stage/open_gateway/ogw_teknofest.pdf`
   - `docs/final_stage/open_gateway/number-verification.yaml`
   - `docs/final_stage/open_gateway/quality-on-demand.yaml`
   - `docs/final_stage/open_gateway/teknofest.postman_collection.json`
   - `data/final_stage/faz2/ground_truth.json`
2. Dosya SHA256 değerlerini `data/final_stage/faz2/manifest.json` veya ayrı source inventory içinde kaydet; ikiz/orijinal dosya bırakma.
3. `assumptions.md` dosyasını **koddan önce** güncelle:
   - source-of-truth sırasını Bölüm 2.1'e getir;
   - DS-001/003/005/007/008 maddelerini Faz 2 HLS + event GT gerçeğiyle daralt;
   - DS-006'yı koru: speed şartnamede geçse de FTR schema ve Faz 2 GT'de yoktur, zorunlu çıktı değildir;
   - DS-010/011/015'i güncelle: NV/QoD canlı demo %25 yolunun kritik parçasıdır; yalnız KTR metninden çıkarılmış olması final entegrasyondan çıkarıldığı anlamına gelmez;
   - DS-013'ü güncelle: API dokümanı ve base URL mevcut, yalnız credential/SIM/callback provisioning dış bağımlılıktır;
   - Web UI zorunluluğu, `teknofest-2026/` image adı, 5/10 dakika limitleri ve 7 Ağustos freeze'i yeni operasyon varsayımları olarak ekle;
   - official final-day hidden GT ve timestamp toleransının hâlâ bilinmediğini açık tut.
4. `src/smart_road_safety/assumptions.py` kayıtlarını aynı değişiklikte `assumptions.md` ile birebir hizala; `print-assumptions` çıktısı ikinci bir eski gerçeklik anlatmasın.
5. Başlangıç evidence raporu oluştur: git SHA, Python/Docker/GPU sürümü, mevcut test sonuçları, eksik weight listesi ve HLS probe bilgisi.
6. Üç mevcut test fail'ini sınıflandır:
   - silinen legacy screenshot'lar gerçek gerekli fixture ise restore et;
   - değillerse manifest/adapter ve testi gerçek envantere göre değiştir;
   - DOCX caption kontrolünü metin extraction yerine OOXML/render doğrulamasıyla değiştir.
7. Bölüm 4.4'teki repo boundary ADR'sini tamamla; mobile/backend'in bu repo içinde mi dışında mı uygulanacağını, owner'ı ve build/deploy kanıtını kaydet.
8. **1 Ağustos external-dependency checkpoint'i** çalıştır:
   - `client_id`/`client_secret`, final SIM ve redirect URI talebinin sahibi ve teslim zamanı belli mi?
   - takım VM/IP/port bilgisi var mı?
   - Android HLS→MP4 spike'ı gerçek cihazda başlamış mı?
   - dış mobil/backend repo varsa erişim ve son çalışan build SHA'sı var mı?
   - cevap “hayır” olan her madde risk kaydına owner + son karar zamanı ile girilmiş mi?

### Değişecek ana yüzeyler

- `assumptions.md`
- `src/smart_road_safety/assumptions.py`
- `README.md`
- `docs/final_stage/adr/0001-client-backend-boundary.md`
- yeni `docs/final_stage/` ve `data/final_stage/faz2/`
- `tests/test_analysis.py`, `tests/test_data_adapters.py`, `tests/test_report_generation.py`

### Çıkış/kabul kriteri

- Assumption dokümanı ile Python registry aynı gerçekleri içerir.
- Yeni kaynakların tamamı stabil path ve checksum ile envanterlenmiştir.
- Baseline 49 testin tamamı geçer veya gerçekten dış bağımlı test açıkça skip değil ayrı live test olarak sınıflandırılmıştır.
- Mobil/backend repo sınırı ve stack sahibi ADR ile kilitlenmiş, seçilen yüzey en az build/health smoke üretmiştir.
- Credential/SIM/VM talepleri owner ve son tarihle açılmış; HLS→MP4 spike'ı gerçek cihazda yürütülmüştür.
- Bu aşama bitmeden ingestion, model veya API davranışı değiştirilmez.

---

## P1 — Faz 2 veri paketini, HLS varyantlarını ve manifest'i gerçek hale getir

**Amaç:** Faz 2 videosu ve GT'yi tekrar üretilebilir, doğrulanabilir ve leakage-safe bir geliştirme paketi yapmak.

### Yapılacaklar

1. Manifest sözleşmesini `ftr_results_json` annotation formatını ve `video_clip` sample unit'ini açıkça tanıyacak şekilde genişlet.
2. `FinalStageFtrAdapter` benzeri ayrı bir adapter uygula. Adapter:
   - bir video asset kaydı ile `ground_truth.json` ilişkisini kurmalı;
   - GT'yi `competition/ftr.py` validator'ından geçirmeli;
   - video süresi/çözünürlük/checksum metadata'sını expose etmeli;
   - eksik video, bozuk JSON, duplicate event, geçersiz label, negatif timestamp ve video süresi dışı timestamp için açık hata vermeli;
   - legacy three-video bundle veya support dataset adapter'larına özel davranışı taklit etmemeli.
3. `scripts/fetch_final_stage_hls.py` veya eşdeğer tek amaçlı bir araç ekle; organizer'ın verdiği exact master URL'yi manifest/config'e bir kez yaz, PDF'den her kullanımda yeniden elle kopyalama:
   - `https://teknofest-arge-turkcell.ercdn.net/hls/4/pZ/faz2/faz2.smil/playlist.m3u8`;
   - master playlist'i indir ve varyantları probe et;
   - 240p ve 1080p varyantlarını ayrı canonical MP4'e remux et;
   - yarım indirmeyi atomik temp dosyada tut;
   - başarıdan sonra checksum/duration/fps/codec/resolution değerlerini manifest'e yaz;
   - media dosyalarını git'e ekleme; `.gitignore` ve manifest source URL/checksum yaklaşımını kullan.
4. HLS URL'sini kodun farklı yerlerine kopyalama; config/manifest tek kaynak olsun.
5. GT için veri sızıntısı kuralı ekle:
   - aynı Faz 2 video segmenti hem fine-tune hem nihai raporlanan holdout metric'e giremez;
   - mümkünse kronolojik group split kullan;
   - tek video nedeniyle üretilen metrik “development calibration” olarak adlandırılır, hidden-final genellemesi olarak sunulmaz.
6. OpenALPR/Open Images gibi mevcut manifest'i olup registry adapter'ı olmayan destek kaynaklarını ya gerçek adapter ile bağla ya da manifest'i `unsupported` olarak açık işaretle; `.pyc` kalıntısına dayalı sessiz varsayım yapma.
7. `data/custom_dataset.yaml` içindeki başka makineye ait absolute path'i repo-relative/generated config ile değiştir.

### Önerilen dosyalar

- `data/final_stage/faz2/manifest.json`
- `data/final_stage/faz2/ground_truth.json`
- `src/smart_road_safety/data/final_stage.py`
- `src/smart_road_safety/manifest.py`
- `src/smart_road_safety/data/adapters.py`
- `scripts/fetch_final_stage_hls.py`
- `tests/test_final_stage_adapter.py`

### Çıkış/kabul kriteri

- `check-manifest` sonucu `pass` olur; bilinen gap'ler yanlışlıkla pass sayılmaz.
- `inspect-dataset` bir video sample, iki resolution artifact ve 34 doğrulanmış GT event raporlar.
- HLS fetch aracı aynı input'ta idempotent çalışır ve checksum eşleşmeyince fail eder.
- GT dosyası runtime inference tarafından import edilmez veya otomatik aranmaz.

---

## P2 — Gerçek FTR ground-truth evaluator'ını ekle

**Amaç:** Model değişikliklerini sentetik scenario skoru yerine sağlanan GT ile ölçmek.

### Yapılacaklar

1. `src/smart_road_safety/evaluation/ftr_metrics.py` içinde ayrı evaluator oluştur.
2. Değerlendirmeden önce hem prediction hem GT'yi mevcut FTR validator ile doğrula.
3. Araç bilgisi için şu metrikleri üret:
   - type exact match;
   - color exact match;
   - plate normalized exact match;
   - plate regex validity;
   - confidence range validity.
4. Event değerlendirmesinde kategori + label bazında bir-bir eşleme yap:
   - aynı kategori/label içindeki prediction ve GT event'lerini mutlak timestamp farkına göre eşle;
   - bir event yalnız bir kez eşleşsin;
   - tolerance config parametresi olsun;
   - varsayılan geliştirme toleransı resmi kural diye sunulmasın;
   - 0.5, 1.0, 2.0 ve 3.0 saniye sensitivity tablosu üret.
5. Per-label ve per-family TP/FP/FN, precision, recall, F1; macro/micro toplam ve timestamp MAE üret.
6. Repeated passenger/object event'lerini set'e indirgeme; her timestamp ayrı GT olayıdır.
7. Yeni CLI ekle:

   ```bash
   PYTHONPATH=src python3 -m smart_road_safety.cli evaluate-ftr \
     --prediction out/faz2/results.json \
     --ground-truth data/final_stage/faz2/ground_truth.json \
     --timestamp-tolerance 1.0 \
     --output out/final_stage/faz2_metrics.json
   ```

8. Markdown export'a vehicle ve event metric tabloları, yanlış/kaçırılan event listesi ve kullanılan tolerance bilgisini ekle.

### Zorunlu testler

- GT vs kendisi: bütün exact alanlar ve F1 `1.0`.
- Bir prediction iki yakın GT event'i eşleştiremez.
- Tolerance sınırındaki event deterministik davranır.
- Yanlış label FP+FN üretir.
- Bozuk schema metric üretmeden fail eder.
- Boş prediction ve boş category sıfıra bölünmeden raporlanır.
- Event sırasının değişmesi sonucu değiştirmez.

### Çıkış/kabul kriteri

- Düşük/yüksek/kayıt videosu sonuçları aynı evaluator ile karşılaştırılabilir.
- Her model değişikliği öncesi/sonrası metric JSON'u saklanır.
- “Başarı” sentetik scenario testine değil, GT metric ve hidden-data risk açıklamasına dayanır.

---

## P3 — Inference hattını final etiketlerine ve temporal olaylara hazırla

**Amaç:** Sabit/heuristik placeholder'lardan gerçek, ölçülebilir ve tüm FTR ailelerini üreten inference'a geçmek.

### P3.1 Runtime asset readiness

1. Zorunlu model envanteri tanımla: ana detector, driver-action classifier, plate detector/OCR, `teknocan`/bilgisayar detector ve yolcu/seat-position head'i.
2. Her weight için kaynak, lisans, dosya adı, SHA256, beklenen class mapping ve model sürümünü machine-readable bir runtime asset manifest'inde tut.
3. `check-runtime-assets` CLI komutu ekle; final modunda eksik/checksum yanlış/class mapping uyumsuz weight için non-zero çık.
4. `Dockerfile` içindeki `|| true`/warning-only kritik weight indirmelerini kaldır. Geliştirme için ayrı `ALLOW_DEGRADED_INFERENCE=1` modu gerekirse açık ve finalde yasak olsun.
5. `download_weights.sh`, Hugging Face upload listesi, `hf_readme.md` ve Dockerfile aynı envanteri kullansın.

### P3.2 Frame ve temporal işleme

1. Sabit 1 FPS yerine config edilebilir 3–5 FPS baseline kur; gerçek süre ölçümüne göre adaptive sampling değerlendir.
2. Video timestamp'ını sadece frame index varsayımıyla değil capture PTS/FPS bilgisiyle üret; monotonluk ve seek hatalarını test et.
3. Global sabit 3 saniye dedup yerine label-specific temporal state kullan:
   - davranış başlama/bitme ve minimum persistence;
   - object/passenger görünürlük transition'ı;
   - kısa davranışlar için uygun cooldown;
   - tekrar eden GT event'lerini yanlışlıkla tek event'e indirmeme.
4. `slalom` için tek-frame classifier kullanma; araç track merkezi/lateral hareket serisi üzerinden temporal motion head geliştir.
5. Event timestamp'ını davranışın ilk güvenilir görünür olduğu ana yaklaştır; pencere ortasını körlemesine kullanma.

### P3.3 Task head'leri

1. **Araç tipi/renk:** COCO coarse mapping'i final default olmaktan çıkar; calibrated classifier çıktısı ve belirsizlik politikası ekle.
2. **Plaka:** plate detector + OCR + Turkish normalization/regex; lower-frame fixed crop yalnız explicit dev fallback olsun.
3. **Sürücü eylemleri:** sekiz kesin etiketi kapsayan class mapping; one-label-per-frame varsayımının çoklu/ardışık davranışlara etkisini ölç.
4. **Emniyet kemeri:** sabit confidence üreten Hough heuristic'i final prediction kabul etme; model veya doğrulanmış geometry head ile değiştir.
5. **Nesneler:** `teknocan` ve `bilgisayar` için explicit training/validation ve class map.
6. **Yolcular:** `arka_koltuk_1`, `arka_koltuk_2`, `on_koltuk` için kamera geometrisine kalibre edilmiş detector/head; generic box-position heuristic'ini final default olmaktan çıkar.
7. Bütün head'ler confidence calibration raporu üretmeli; FTR confidence alanı sabit/hard-coded değer olmamalıdır.

### P3.4 Prediction assembly

1. `competition/ftr.py` kesin schema authority olarak korunur.
2. Model prediction'dan gelen her class explicit mapping tablosuyla FTR label'a çevrilir; unmapped label fail eder.
3. `build_ftr_result_from_analysis` tek sabit timestamp üreten bridge olarak final video yolunda kullanılmaz; video event timeline'ından doğrudan builder eklenir.
4. Prediction'lar timestamp'e göre stabil sıralanır; JSON serialization deterministik olur.
5. Araç bilgisi bulunamıyorsa sahte sedan/plaka/renk üretme; explicit inference failure sonucu oluştur ve container'ı başarısız say.

### Test ve ölçüm

- Sahte `VideoCapture` ve fake engine ile sampling/timestamp/dedup unit testleri.
- Faz 2 low/high üzerinde per-label metric karşılaştırması.
- Düşük çözünürlükte plate/small object regression seti.
- Aynı video iki kez çalıştığında schema ve event ordering deterministikliği.
- CPU setup smoke; final GPU üzerinde runtime ve bellek profili.

### Çıkış/kabul kriteri

- Faz 2 GT'deki 8 sürücü, 2 nesne ve 3 yolcu label'ı pipeline'da gerçek üretilebilir durumdadır.
- Zorunlu asset eksikliğinde image başlamaz; silent degraded inference yoktur.
- Low/high prediction'ları için kaydedilmiş metric baseline ve hata analizi vardır.
- Bir inference final GPU hedefinde 10 dakika bütçesinin altında, tercihen 8 dakika p95 sınırında biter.

---

## P4 — Competition Docker image'ı deterministic ve Web UI uyumlu paketle

**Amaç:** Hakem VM'inde tek image ile ağsız, tekrarlanabilir ve süresi ölçülmüş inference.

### Yapılacaklar

1. Image adını bütün doküman/scriptlerde `teknofest-2026/qode-final:<version>` olarak standardize et.
2. Runtime contract'ı sabitle:
   - input: `/app/data/input/video.mp4`;
   - output: `/app/data/output/results.json`;
   - output önce temp dosyaya yazılıp schema validation sonrası atomik rename edilir;
   - başarı exit code `0`, hata non-zero ve açıklayıcı stderr.
3. Build sırasında bütün weight ve OCR asset'lerini image'a dahil et; runtime network download yapma.
4. Base image, Python packages, CUDA/torch compatibility ve model checksum'larını build evidence'a yaz.
5. Container içinde input klasöründe tam bir video koşulunu doğrula; başka medya dosyaları varsa açık hata ver.
6. Health/readiness komutu ekle; bu komut GPU, weight, writable output, schema version ve model warm-up kontrolü yapmalı.
7. Low, high ve mobil kayıt MP4'lerini ayrı temiz input dizinlerinde çalıştır; her birinde wall time, GPU memory, peak disk ve output checksum kaydet.
8. Container'ın ürettiği success'i yalnız geçerli `results.json` ve exit code ile belirle; platformun göstereceği `EXECUTION COMPLETED – status: SUCCESS` metnini uygulama içinde taklit etme.
9. Final image'ı bir kez build et; `docker image inspect` RepoDigest/Id, tar SHA256 ve build metadata'yı `out/final_stage/freeze/` altında kaydet.

### Çıkış/kabul kriteri

- Üç video varyantı da Web UI üzerinden çalışır ve her biri 10 dakikadan kısa sürer.
- Image runtime'da internet olmadan çalışır.
- Output mevcut validator'dan geçer.
- Web UI Docker Images panelinde yalnız tek `teknofest-2026/qode-final:<frozen>` image kalır.
- 7 Ağustos 21:00'dan önce kayıt edilen SHA256 ile yarışma günü image değeri aynıdır.

---

## P5 — Gerçek Open Gateway client'larını ve final backend'i uygula

**Amaç:** Belgelenmiş OIDC/NV/QoD çağrılarını gerçek backend üzerinden çalıştırmak; mock'u yalnız test double olarak tutmak.

### P5.1 Config ve secret sözleşmesi

Önerilen env adları:

```text
OPENGW_API_ROOT=https://opengateway.turkcell.com.tr
OPENGW_CLIENT_ID=...
OPENGW_CLIENT_SECRET=...
OPENGW_REDIRECT_URI=http://<BACKEND_IP>:8080/api/auth/callback
OPENGW_SCOPES="openid dpv:RequestedServiceProvision#quality-on-demand:sessions:create dpv:FraudPreventionAndDetection#number-verification:verify"
OPENGW_QOS_PROFILE=teknofest2026
FINAL_AI_IMAGE=teknofest-2026/qode-final:<frozen>
FINAL_JOB_ROOT=/var/lib/qode/jobs
```

- Secret değerleri repoya, `.env.example` içine veya trace'e yazılmaz.
- `.env.example` yalnız değişken adlarını ve dummy değerleri gösterir.
- Access token mobile dönmez; backend memory store'da `expires_in` süresi boyunca tutulur.
- Telefon numarası loglarda maskelenir, access/refresh token hiçbir log seviyesinde gösterilmez.

### P5.2 OIDC Authorization Code Flow

1. `GET /api/auth/start` random, tek kullanımlık, TTL'li `state` üretir ve authorize URL'ye redirect eder.
2. Scope'lar dokümandaki üç exact değerle gönderilir.
   - Organizer Postman collection QoD için `dpv:RequestedServiceProvision#quality-on-demand:sessions:create` kullanır; final authorize request'te birincil authority budur.
   - CAMARA YAML security scope listesinde daha kısa `quality-on-demand:sessions:create` değeri de görünür. Contract test iki kaynağın farkını belgelemeli; canlıda scope reddedilirse organizer/Turkcell onayı alınmadan sessizce scope değiştirilmemelidir.
3. `GET /api/auth/callback` code+state doğrular; state mismatch/replay/expiry için fail eder.
4. Backend `/oauth2/token` çağrısını Basic `client_id:client_secret` ile yapar.
5. Token expiry takip edilir; süresi geçmiş token ile NV/QoD çağrısı yapılmaz, kullanıcı yeniden authorize edilir.
6. Sağlayıcı PKCE desteği resmi olarak doğrulanırsa eklenir; dokümanda olmayan parametre varsayılıp canlı akış kırılmaz.

### P5.3 Number Verification

- Endpoint: `POST /number-verification/v1/verify`.
- Request'te `phoneNumber` E.164 veya `hashedPhoneNumber` alanlarından yalnız biri olur.
- Final UX test numarası dokümandaki `+905390000020` ile config üzerinden verilir; kod içine ürün default'u olarak gömülmez.
- Bearer token ve unique `x-correlator` gönderilir.
- `devicePhoneNumberVerified=true` tek başarı ölçütüdür.
- False/401/403/422/timeout durumları kullanıcıya farklı, izlenebilir durum kodlarıyla döner.
- NV başarısızsa QoD/video adımları backend state machine tarafından engellenir.

### P5.4 Quality on Demand

- Endpoint: `POST /quality-on-demand/v1/sessions`.
- Final request tam olarak şu sabit alanları taşır:

  ```json
  {
    "duration": 60,
    "applicationServer": {"ipv4Address": "0.0.0.0/0"},
    "qosProfile": "teknofest2026"
  }
  ```

- Duration mobil UI'dan alınacaksa OpenAPI min/max sınırında doğrulanır; final demo default'u 60 saniyedir.
- 3-legged token kullanıldığı için request'e `device` eklenmez.
- `201 Created`, `sessionId` ve `qosStatus` parse edilir; `REQUESTED`, `AVAILABLE`, `UNAVAILABLE` ayrıştırılır.
- QoD başarısız/UNAVAILABLE olsa bile backend streaming'e devam izni verir ve trace'e reason yazar.

### P5.5 Final backend API ve job runner

Önerilen minimum surface:

| Method/path | İşlev | Başarı |
| --- | --- | --- |
| `GET /health` | Backend health; secret içermez | `200` |
| `GET /api/auth/start` | OIDC akışını başlatır | `302` |
| `GET /api/auth/callback` | code exchange ve session | `302/200` |
| `GET /api/session/{flow_id}` | verified/QoD özet kartı | `200` |
| `POST /api/number-verification/verify` | gerçek NV | `200` |
| `POST /api/qod/sessions` | gerçek QoD create | `201` veya kontrollü fail-open sonucu |
| `POST /api/videos` | multipart MP4 upload | `202`, `jobId` |
| `GET /api/jobs/{job_id}` | `PROCESSING/DONE/FAILED` | `200` |
| `GET /api/jobs/{job_id}/result` | doğrulanmış `results.json` | `200` yalnız DONE |
| `GET /api/jobs/{job_id}/trace` | redact edilmiş event trace | `200` |

Upload/job uygulaması:

1. Sadece izinli content type/MP4 signature ve üst boyut sınırı kabul edilir.
2. Client dosya adı path olarak kullanılmaz; random `job_id` altında sabit `input/video.mp4` yazılır.
3. Upload atomik yazılır, checksum ve duration probe edilir, sonra `202` dönülür.
4. `ContainerInferenceRunner` shell string değil sabit argument listesi kullanır; path traversal ve komut injection mümkün olmaz.
5. Runner frozen image digest'ini, read-only input mount'u ve job'a özel output mount'unu kullanır; GPU ve 570 saniye timeout uygular.
6. Container exit `0` olsa bile output validator geçmeden job `DONE` olmaz.
7. Job metadata disk üzerinde, token/session secret'ları process memory'de tutulur; TTL cleanup ve disk quota uygulanır.
8. Duplicate upload için idempotency key veya checksum-aware yeniden kullanım politikası tanımlanır.

### Kod yüzeyleri

- `src/smart_road_safety/integration/contracts.py`
- `src/smart_road_safety/integration/opengateway.py` (**yeni**)
- `src/smart_road_safety/integration/auth.py` (**gerekirse yeni**)
- `src/smart_road_safety/orchestration/service.py`
- `services/api/` (**final backend**)
- `src/smart_road_safety/local_api/server.py` (**dev compatibility adapter**)
- `tests/test_opengateway_clients.py`, `tests/test_final_backend.py`

### Çıkış/kabul kriteri

- Fake HTTP transport contract testlerinde exact URL/header/body doğrulanır.
- Credential mevcut ortamda gerçek NV sonucu ve `x-correlator` kaydedilir.
- QoD 201/REQUESTED veya dokümante edilmiş hata sonucu alınır; hata streaming'i engellemez.
- Upload 202 döner; status DONE olduğunda result schema-valid'dir.
- Log/trace içinde client secret, access token veya açık telefon numarası yoktur.

---

## P6 — Android mobil uygulamayı final UX akışına bağla

**Amaç:** Hakem karşısında tek akışla NV → QoD → HLS → MP4 → upload → AI result → trace göstermek.

### İlk teknik spike: HLS kayıt ve MP4 export

Bu, canlı demonun en yüksek teknik riskidir ve 2 Ağustos öğlene kadar çözülmelidir.

1. Native Android/Kotlin üzerinde AndroidX Media3 `1.10.1` ile master HLS playback ve ABR'yi kanıtla. Aynı sürümde `media3-exoplayer`, `media3-exoplayer-hls`, `media3-ui` ve `media3-transformer` modüllerini kullan.
   - UI kodundan önce gerçek geliştirme makinesinde Gradle dependency-resolution ve boş debug APK build smoke'u çalıştır; repository erişimi, Kotlin/AGP uyumu veya Android SDK eksiği deadline sırasında keşfedilmesin.
2. Tam VOD'u seçilen rendition ile yerel depoya indirip oynatılabilir `.mp4` üretme yolunu şu sırayla dene:
   - doğrudan VOD HLS URI → Media3 Transformer → `recorded.mp4`;
   - Media3 `DownloadService`/`DownloadManager`/`DownloadHelper` ile seçili `streamKeys` cache → offline `MediaItem` → Transformer → `recorded.mp4`;
   - iki Media3 yolu da cihaz/format nedeniyle çalışmaz veya süreyi aşarsa, lisans/ABI/image-size etkisi kabul edilebilir bir **non-GPL** FFmpeg build ile stream-copy/remux spike'ı;
   - server-side kayıt yalnız tanı/backup olabilir, “mobil uygulama MP4 dışa aktarır” kabul kriterinin yerine geçmez.
3. 240p ve 1080p için gerçek cihazda wall time, çıktı boyutu, duration, audio/video sync ve seek testleri yap.
4. Seçilen yaklaşımı kısa ADR ile kilitle; çalışan spike olmadan ekran geliştirmesine geçme.

Media3, AndroidX tarafından aktif tutulan resmi ve Apache-2.0 lisanslı yol olduğu için ilk tercihtir. Eski `arthenica/ffmpeg-kit` projesi emekli/archived olduğundan doğrudan production dependency yapılmayacaktır. Community FFmpeg fork'u ancak Media3 spike'ı fail ederse, source provenance ve LGPL/GPL bileşenleri incelenerek deadline fallback'i olabilir. GPL codec içeren build, lisans kararı alınmadan kullanılmaz.

Teknik karar kaynakları:

- <https://developer.android.com/jetpack/androidx/releases/media3>
- <https://developer.android.com/media/media3/exoplayer/downloading-media>
- <https://developer.android.com/media/media3/transformer/getting-started>
- <https://developer.android.com/media/media3/transformer/troubleshooting>
- <https://github.com/androidx/media>
- <https://github.com/arthenica/ffmpeg-kit>

### Ekran ve state machine

1. **Number Verification ekranı:** telefon, başlatma, browser/OIDC dönüşü, hata/retry.
2. **Verified Session kartı:** masked phone, Verified, Flow ID, Correlation ID.
3. **QoD Session kartı:** session ID, status, duration; hata halinde “streaming düşük kaliteyle devam edecek” açıklaması.
4. **Video kartı:** HLS player, anlık bitrate/resolution, indirme/kayıt progress'i, kalan süre ve MP4 export durumu.
5. **Upload kartı:** checksum, upload progress, retry/idempotency.
6. **AI Result tab:** `PROCESSING`, `DONE`, `FAILED`; vehicle card, detection list, raw JSON ve `ai-result-refresh`.
7. **Trace tab:** state geçişleri, flow/correlation/job ID; secret/token içermeyen hata ayrıntısı.

### Streaming politikası

- QoD `AVAILABLE/REQUESTED` başarılı yolunda 1080p'ye izin ver; ölçülen throughput yetmezse ABR'nin düşmesine izin ver.
- QoD başarısız/UNAVAILABLE yolunda maksimum 240p cap uygula; yüksek varyantı zorlayıp 5 dakika bütçesini tüketme.
- Oynatma ile kayıt aynı kaynak zaman çizelgesini kullanmalı; eksik segment, duplicate segment ve playlist discontinuity tespit edilmeli.
- Tam video süresi manifest/probe toleransında değilse upload aktif edilmemeli.
- Android lifecycle, ekran rotasyonu, ağ geçişi ve uygulamanın kısa süre background'a alınması state'i kaybettirmemeli.
- Lifebox paylaşımı için resmi API verilmemişse Android share sheet ile MP4 handoff ve checksum gösterimi sağla; otomasyon iddiasında bulunma.

### Backend entegrasyonu

- Mobile yalnız backend session cookie/token'ını tutar; Open Gateway client secret'ını asla içermez.
- Upload multipart alan adı ve response contract backend OpenAPI fixture'ından üretilir/ortak test edilir.
- Job status exponential backoff + manual refresh ile çekilir; DONE sonrası raw JSON olduğu gibi gösterilmeden önce schema-version kontrol edilir.
- Aynı butona çift basma duplicate QoD session veya inference job üretmemeli.

### Çıkış/kabul kriteri

- Gerçek cihaz + mobil şebekede NV tamamlanır; başarısızlıkta akış durur.
- QoD başarısızken 240p streaming ve upload devam eder.
- QoD başarılıyken yüksek kalite seçimi gözlemlenir veya ABR kararı trace'te açıklanır.
- Yaklaşık 113.92 saniyelik VOD, başlangıçtan oynatılabilir MP4'e kadar 5 dakikadan kısa sürer.
- MP4 backend'e yüklenir, job state ve FTR sonucu uygulamada görünür.

---

## P7 — CLI, local API, orchestration, export ve dokümantasyonu tek gerçek yola bağla

**Amaç:** Geliştirme yüzeyleri ile final backend'in farklı sonuç üretmesini önlemek ve bütün demo kanıtlarını dışa aktarabilmek.

### Yapılacaklar

1. `integration/contracts.py` domain sözleşmelerini gerçek API status/identifier alanlarını taşıyacak şekilde genişlet; HTTP ayrıntısını orchestration'a sızdırma.
2. `orchestration/service.py` içindeki “mock gateway” mesajlarını gerçek/mod bilgisine göre üret; production request'te `verification_should_pass` ve `qod_should_allow_boost` gibi sahte kontrol boolean'ları kabul etme.
3. Mock seçimini ayrı `--gateway-mode mock` veya test fixture'ı ile açık yap; default config auto-fallback yapmasın.
4. `local_api/server.py` mevcut JSON analysis endpoint'lerini korusun fakat final video upload/job yeteneğinin authority'si olmasın; `services/api` client/adapter'ı olarak çalışsın veya deprecation notu alsın.
5. CLI'ye şu operasyon komutlarını ekle:
   - `check-final-assets`;
   - `fetch-final-hls`;
   - `evaluate-ftr`;
   - `check-runtime-assets`;
   - `run-final-smoke`;
   - `freeze-image-evidence`.
6. Markdown export'a şunları ekle:
   - source/manifest/checksum;
   - low/high/recorded runtime;
   - GT metric tablosu ve tolerance;
   - NV/QoD canlı smoke sonucu;
   - image digest;
   - dış blocker/untested ayrımı.
7. README'yi güncelle:
   - final source order ve canonical dosya yolları;
   - gerçek vs mock mod;
   - env değişkenleri;
   - Docker adı ve Web UI çalışma adımları;
   - yeni CLI/backend/mobile akışı;
   - artık geçersiz “API dokümanı yok/QoD scope dışı” ifadelerini kaldır.
8. `apps/mobile/README.md`, `services/api/README.md`, `services/vision/README.md` placeholder metinlerini gerçek build/run/test talimatlarıyla değiştir.

### Local API → final backend migration matrisi

P5 başlamadan mevcut endpoint'lerin regression sözleşmesi snapshot testleriyle kilitlenir. Final backend eklendiğinde her satır açıkça `keep`, `shim` veya `deprecate` kararı alır:

| Mevcut local API | Karar | Final davranışı |
| --- | --- | --- |
| `GET /health` | **keep + align** | Local ve final backend aynı temel health alanlarını taşır; final backend ayrıca dependency readiness'i ayrı endpoint/alanla verir. |
| `POST /orchestration/run` | **keep as explicit mock/dev** | `gateway_setup` yalnız test/local modda kalır; gerçek NV/QoD final backend'in `/api/...` endpoint'lerinden yürür. |
| `POST /analysis-session/run` | **keep** | Dataset/support analysis geliştirme yüzeyi olarak korunur; video inference job'ıymış gibi sunulmaz. |
| `POST /competition/ftr-output` | **deprecate for final inference, keep compatibility** | Tek timestamp/sidecar builder legacy testler için kalır; final video prediction `main.py`/job runner sonucudur. Response'a deprecation bilgisi eklenir. |
| `POST /competition/validate-ftr-output` | **keep/share implementation** | Her iki server aynı `competition/ftr.py` validator'ını kullanır. |
| `POST /dataset/inventory` | **keep** | Geliştirme/manifest aracı; internetten veya kullanıcı path'inden keyfi dosya okumaya final backend üzerinden açılmaz. |
| `POST /evaluation/run-scenarios` | **keep as support** | Sentetik orchestration suite kalır; final GT evaluator ile karıştırılmaz. |
| `POST /export/report-markdown` | **keep/extend** | Final FTR metric export aynı domain exporter'ını kullanır; path güvenliği final backend'de ayrıca uygulanır. |

Migration uygulama sırası:

1. Mevcut request/response ve error payload'larını regression testleriyle kilitle.
2. Paylaşılan domain service/validator/evaluator fonksiyonlarını HTTP handler'lardan ayır.
3. Final backend bu servisleri import etsin; local API'yi final backend'e proxy eden döngüsel bağımlılık kurma.
4. Shim/deprecation davranışını README ve response metadata'da duyur.
5. Mevcut `tests/test_local_api.py` ile yeni backend contract testlerini birlikte çalıştır; iki server'ın ortak işlemlerde aynı sonucu verdiğini parity test ile doğrula.

### Çıkış/kabul kriteri

- CLI, backend ve exporter aynı validator/evaluator/domain contract'larını import eder.
- Production akışında fake behavior boolean'ı veya silent mock yoktur.
- README'deki bütün kopyalanabilir komutlar temiz checkout'ta çalışır.
- Export edilmiş kanıt dosyası sentetik ve gerçek sonucu açıkça ayırır.
- Migration matrisindeki her endpoint için regression/parity testi ve `keep/shim/deprecate` kararı vardır; iki bağımsız domain davranışı oluşmamıştır.

---

## P8 — VM/Web UI provası, freeze ve final operasyonu

**Amaç:** Kodun çalışmasından öte, hakemin uygulayacağı exact operasyonu süre içinde ve hatasız prova etmek.

### VM preflight

1. Takım VM IP/SSH kullanıcısı ve callback URI'sini doğrula.
2. GPU driver, Docker runtime, disk, port 8080 erişimi ve HTTP callback erişilebilirliğini ölç.
3. `http://<VM_IP>` Web UI'ya eriş; HTTPS kullanma.
4. Final backend service ve callback portunu güvenlik duvarı/proxy ile doğrula.
5. `teknofest-2026/qode-final:<candidate>` image'ının Web UI sağ panelde göründüğünü kontrol et.

### En az iki tam prova

Her prova ayrı evidence dizinine kaydedilir:

1. Mobile OIDC/NV success.
2. QoD success yolu; ayrıca QoD failure yolu.
3. HLS 1080p/240p seçim kanıtı.
4. Tam MP4 export süresi ve checksum.
5. Lifebox/share handoff.
6. Backend upload 202 ve job timeline.
7. Mobile DONE ekranı ve raw JSON.
8. Web UI ile low video inference.
9. Web UI ile high video inference.
10. Web UI ile kaydedilmiş video inference.
11. Her output için FTR validation ve GT metric.
12. Her inference wall time <10 dakika.

### Freeze prosedürü — 7 Ağustos 2026

1. Son aday image en geç öğlene kadar üç video üzerinde tam test edilir.
2. 18:00'dan sonra yalnız blocker düzeltmesi yapılır; yeni özellik/model deneyi yapılmaz.
3. Son image `teknofest-2026/qode-final:<frozen-tag>` adıyla tek kez build edilir.
4. Image ID/digest/tar SHA256, git SHA, model checksum ve build zamanı kaydedilir.
5. Image offline export/backup alınır ve geri yükleme smoke'u yapılır.
6. Web UI panelinden eski aday image'lar kaldırılır; yalnız frozen image bırakılır.
7. 21:00'dan önce son Web UI smoke ve checksum karşılaştırması tamamlanır.
8. 21:00 sonrası repo/model/image değişmez; yalnız sunum/runbook kopyaları çoğaltılır.

### Final günü runbook'u

- Birincil operatör, mobil operatör ve anlatıcı rolleri önceden atanır.
- 10 dakikalık sunum için zaman kutulu akış ve yedek ekran görüntüleri hazırlanır.
- Credential/token expiry, QoD failure, HLS yavaşlığı, upload retry ve backend restart için tek sayfalık recovery kartı olur.
- QoD başarısızlığında streaming'in devam ettiği özellikle prova edilir.
- NV başarısızsa kurala uygun olarak sonraki adımlara geçilmez; fake success gösterilmez.
- Hakem image SHA istediğinde kayıtlı digest anında sunulur.

---

## 7. Gün gün önerilen takvim

| Tarih | Öncelikli sonuç | Gün sonu stop condition |
| --- | --- | --- |
| **1 Ağustos** | P0: kaynakların kanonikleşmesi, assumptions güncellemesi, 49 test baseline'ının temizlenmesi, HLS/mobile kayıt spike'ının başlaması | Varsayımlar kilitli; mevcut testler yeşil; teknik blocker listesi sahibiyle açık. |
| **2 Ağustos** | P1 + P2: low/high asset manifest, GT adapter, evaluator; HLS→MP4 mobil yaklaşım kararı | GT identity test 1.0; low/high indirilebilir; Android kayıt yaklaşımı gerçek cihazda kanıtlı. |
| **3 Ağustos** | P3: runtime asset fail-fast, sampling/temporal event mantığı, bütün label head'leri | Faz 2 prediction ve per-label hata raporu mevcut; silent fallback yok. |
| **4 Ağustos** | P3/P4 + P5: model iyileştirme, Docker candidate, gerçek client/backend contract testleri | Candidate image valid output üretir; OIDC/NV/QoD fake-transport testleri yeşil. |
| **5 Ağustos** | P5/P6: live credential smoke, Android ekran akışı, upload/job/result | Uçtan uca mobil akış staging'de tamam; QoD failure yolu da çalışır. |
| **6 Ağustos** | P7/P8: VM/Web UI tam entegrasyon ve ilk iki prova | Üç video <10 dk; mobile export <5 dk; trace/evidence eksiksiz. |
| **7 Ağustos** | Regression, ikinci tam prova, frozen image, SHA256, backup | 21:00 öncesi tek final image ve imzalı evidence; açık P0/P1 hata yok. |
| **8–9 Ağustos** | Sunum ve final runbook uygulaması | Yalnız frozen artifact çalıştırılır; gerçek sonuç gösterilir. |

Takvim geriye düşerse öncelik sırası: **schema-valid ve zamanında AI inference → NV → QoD → mobil MP4/upload/result → rapor/polish**. QoD başarısızlığının streaming'i engellememesi sayesinde canlı akış korunur; fakat NV hiçbir zaman atlanmaz.

---

## 8. Test ve doğrulama matrisi

### 8.1 Statik ve unit kapısı

```bash
python3 -m compileall -q src tests main.py
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Proje lint/typecheck aracı sabitlenirse temiz config üzerinden çalıştırılır. `ruff`/`pyright` sistemde bulunmuyor diye kontrol yapılmış sayılmaz; ya dev dependency/CI kararı alınır ya da eksiklik evidence'a yazılır.

### 8.2 Manifest ve GT kapısı

```bash
PYTHONPATH=src python3 -m smart_road_safety.cli check-manifest \
  data/final_stage/faz2/manifest.json
PYTHONPATH=src python3 -m smart_road_safety.cli inspect-dataset \
  data/final_stage/faz2/manifest.json --dataset-root data/final_stage/faz2
PYTHONPATH=src python3 -m smart_road_safety.cli validate-ftr-output \
  data/final_stage/faz2/ground_truth.json
```

### 8.3 Inference/evaluation kapısı

```bash
PYTHONPATH=src python3 -m smart_road_safety.cli check-runtime-assets

python3 main.py \
  --input-dir out/final_stage/inputs/faz2-low \
  --output-dir out/final_stage/predictions/faz2-low

PYTHONPATH=src python3 -m smart_road_safety.cli validate-ftr-output \
  out/final_stage/predictions/faz2-low/results.json

PYTHONPATH=src python3 -m smart_road_safety.cli evaluate-ftr \
  --prediction out/final_stage/predictions/faz2-low/results.json \
  --ground-truth data/final_stage/faz2/ground_truth.json \
  --output out/final_stage/metrics/faz2-low.json
```

Aynı işlem `faz2-high` ve `mobile-recorded` için tekrarlanır.

### 8.4 Docker/Web UI kapısı

```bash
docker build -t teknofest-2026/qode-final:candidate .
docker image inspect teknofest-2026/qode-final:candidate --format '{{.Id}}'

docker run --rm --gpus all \
  -v "$PWD/out/final_stage/inputs/faz2-low:/app/data/input:ro" \
  -v "$PWD/out/final_stage/docker/faz2-low:/app/data/output" \
  teknofest-2026/qode-final:candidate
```

Docker CLI smoke geliştirici kanıtıdır; final kabulünde aynı image ayrıca Web UI `Execute` akışıyla çalıştırılacaktır.

### 8.5 Gateway/backend kapısı

- Unit/contract: HTTP fake transport ile authorize, token, NV, QoD exact request/response.
- Negative: state mismatch, token expiry, NV false, 401/403/422/5xx, QoD UNAVAILABLE, timeout.
- Upload: invalid content, oversize, duplicate, partial upload, runner timeout, invalid result JSON.
- Live smoke: gerçek credential + final SIM ile NV ve QoD; secret-redaction kontrolü.

### 8.6 Mobil kapı

- Gerçek Android cihaz ve mobil şebeke.
- QoD success/high-quality ve QoD failure/240p senaryoları.
- Uçak modu/ağ geçişi, lifecycle, retry ve duplicate-tap.
- MP4 duration/codec/playability, 5 dakika wall time, upload checksum.
- PROCESSING→DONE ve PROCESSING→FAILED ekranları.

### 8.7 Evidence dosyaları

Git'e büyük media/log eklemeden aşağıdakiler `out/final_stage/` altında üretilir:

```text
out/final_stage/
  baseline/environment.json
  manifests/hls_probe.json
  metrics/faz2-low.json
  metrics/faz2-high.json
  metrics/mobile-recorded.json
  docker/runtime-matrix.json
  gateway/live-smoke-redacted.json
  mobile/export-timings.json
  rehearsals/<timestamp>/...
  freeze/image-digest.txt
  final-verification.md
```

Özet ve yeniden üretme komutları `docs/final_stage/verification.md` içinde tutulur; token, secret, açık telefon numarası veya büyük video commit edilmez.

---

## 9. Kabul kapıları

| Kapı | Geçiş şartı | Kapı geçmeden yapılamayacak iş |
| --- | --- | --- |
| **G0 — Reality lock** | Assumptions + registry + source inventory güncel; başlangıç testleri yeşil | Model/API behavior değişikliği |
| **G1 — Data ready** | Final manifest pass; low/high asset checksum/probe; 34 GT event valid | Metric iddiası |
| **G2 — Evaluation ready** | GT identity 1.0; deterministic temporal scorer ve report | Model seçimi/freeze kararı |
| **G3 — AI ready** | Tüm FTR aileleri gerçek head'lerden; weight fail-fast; low/high ölçüm | Final image candidate |
| **G4 — Container ready** | Üç video schema-valid ve <10 dk; offline runtime | SHA freeze |
| **G5 — Gateway ready** | Contract tests; credential varsa live NV/QoD; secret redaction | Canlı demo provası |
| **G6 — Mobile ready** | HLS→MP4 <5 dk; QoD fail-open; upload/result/trace | Tam prova |
| **G7 — Platform ready** | Web UI ile iki tam prova, tek image, recovery drill | Freeze |
| **G8 — Frozen** | Image/git/model checksum kayıtlı ve 7 Ağustos 21:00 öncesi | Final günü artifact değişikliği |

Bir kapı başarısızsa aşağı akış “muhtemelen çalışır” kabul edilmez. Hata düzeltilir ve kapı yeniden çalıştırılır.

---

## 10. Risk kaydı ve azaltma planı

| Risk | Etki | Erken sinyal | Azaltma / fallback |
| --- | --- | --- | --- |
| Open Gateway credential/SIM gelmez | Live NV/QoD kanıtlanamaz | 2 Ağustos'ta credential yok | Gerçek client ve contract test tamamlanır; provisioning açık dış blocker olarak günlük takip edilir; mock başarı diye sunulmaz. |
| Callback VM'den erişilemez | OIDC tamamlanmaz | Auth redirect sonrası timeout | 3 Ağustos'a kadar public HTTP callback/port testi; sabit redirect URI; runbook'ta network kontrolü. |
| Mobil HLS MP4 remux 5 dk'yı aşar | Canlı demo video yolu kaybedilir | 2 Ağustos spike başarısız | Aynı gün alternatif mux yolu seç; 240p fail-open; server-side kayıt yalnız tanı/yedek, kabulün yerine geçmez. |
| High video inference >10 dk | %25 değerlendirme kaybı | 4 Ağustos profile >8 dk p95 | Sampling/model resolution/batch optimize; warm-up; gereksiz OCR tekrarlarını azalt; accuracy/runtime metriğini birlikte izle. |
| 1 FPS kısa olayları kaçırır | Recall düşer | GT hata analizi kısa event FN gösterir | 3–5 FPS/adaptive sampling ve temporal state; runtime kapısıyla birlikte tune et. |
| Tek Faz 2 video overfit'i | Hidden videoda çöküş | Faz2 iyi, support/holdout kötü | Chronological/group holdout; public support datasets; augmentation; metric'i dev calibration diye raporla. |
| Eksik/yanlış weight image'a girer | Sessiz boş sonuç | Startup uyarı verip devam eder | Runtime asset manifest + checksum + fail-fast; offline image smoke. |
| Heuristik fixed confidence | Yanlış score/calibration | Çok sayıda 0.62/sabit değer | Head bazlı calibration; final modda heuristik fallback yasağı. |
| Backend Docker runner injection/path riski | VM güvenliği ve demo kaybı | Kullanıcı path'i shell'e girer | Random job dirs, fixed argv, no shell, size/type/path validation, timeout/quota. |
| Disk upload/job ile dolar | Backend durur | Free disk alarmı | Boyut limiti, TTL cleanup, quota, preflight free-space gate. |
| Token/telefon loglara sızar | Credential ihlali | Trace'te bearer/MSISDN | Merkezi redact filter, test assertion, token mobile'a verilmez. |
| Web UI image'ı görmez | Hakem çalıştıramaz | Prefix yanlış/çok image var | `teknofest-2026/` lint/check; freeze sırasında tek image. |
| Resmi timestamp toleransı bilinmiyor | Offline metric final skorunu temsil etmez | Sadece tek tolerance raporu | Multi-tolerance sensitivity; official script gelirse aynı evaluator policy'sini güncelle. |
| Lifebox API/credential yok | Paylaşım gecikir | Otomasyon yolu belirsiz | Android share sheet + manuel doğrulanmış runbook; API varmış gibi davranma. |

---

## 11. Dış bağımlılıklar ve netleştirilecek maddeler

Aşağıdakiler repo içinde icat edilmeyecek, fakat kod geliştirmesini de gereksiz yere durdurmayacaktır:

1. Turkcell `client_id`, `client_secret`, takım SIM/device binding ve izinli redirect URI.
2. Takım Google Cloud VM IP'si, SSH hesabı, GPU/runtime sürümü ve açılacak callback portu.
3. Final-day hidden low/high videoların exact duration/codec ve ground truth'u.
4. Resmi timestamp eşleme toleransı ve canlı demo %25 içindeki NV/QoD dışındaki 15 puanın exact hesabı.
5. Lifebox paylaşımı için API/credential olup olmadığı; yoksa manuel share akışı kullanılacaktır.
6. Repo dışında mevcut bir Android uygulama kod tabanı olup olmadığı.

Bu maddeler `docs/final_stage/open_questions.md` içinde owner, son tarih ve durumla takip edilir. Eksik credential, gerçek client implementasyonunu veya fake-transport testlerini engellemez; yalnız G5 live-smoke alt kapısını engeller ve açıkça raporlanır.

---

## 12. Önerilen commit dilimleri

Bu plan uygulanırken diff'ler aşağıdaki küçük, geri alınabilir dilimlerde tutulmalıdır:

1. Final kaynaklarını kanonikleştir ve assumptions'ı güncelle.
2. Faz 2 manifest/adapter/GT validation ekle.
3. Deterministic FTR evaluator ve export ekle.
4. Runtime asset manifest ve fail-fast packaging ekle.
5. Temporal inference ve task head'lerini label ailesi bazında iyileştir.
6. Competition Docker/Web UI sözleşmesini sabitle.
7. OIDC/Open Gateway gerçek client ve contract testlerini ekle.
8. Final backend upload/job/result akışını ekle.
9. Android HLS/NV/QoD/upload/result akışını ekle.
10. Final dokümantasyon, prova evidence ve freeze runbook'unu tamamla.

Her commit Lore formatında neden odaklı intent, constraint, rejected alternatives, tested ve not-tested trailer'larını taşımalıdır. Bu planı hazırlayan turda commit/push yapılmayacaktır.

---

## 13. Definition of Done kontrol listesi

- [ ] Yeni resmi dosyalar stabil path/checksum ile envanterlendi.
- [ ] `assumptions.md` kod değişikliğinden önce güncellendi.
- [ ] `src/smart_road_safety/assumptions.py` dokümanla hizalandı.
- [ ] Mevcut 3 test hatası gerçek fixture/validation ile kapatıldı.
- [ ] Faz 2 low/high asset'leri tekrar üretilebilir şekilde indirildi ve manifest pass ediyor.
- [ ] Faz 2 GT runtime leakage olmadan adapter/evaluator'a bağlandı.
- [ ] GT identity ve temporal metric testleri geçiyor.
- [ ] Tüm zorunlu model weight'leri checksum'lı ve final modunda fail-fast.
- [ ] Araç/plaka/renk/8 driver/2 object/3 passenger etiketi gerçek inference yolunda üretilebilir.
- [ ] Low/high/recorded sonuçları schema-valid ve her biri <10 dakika.
- [ ] Gerçek OIDC/NV/QoD client'ları exact contract testlerinden geçiyor.
- [ ] Credential/SIM mevcutsa canlı NV ve QoD smoke kanıtı kaydedildi.
- [ ] QoD failure streaming'i engellemiyor; NV failure akışı durduruyor.
- [ ] Android tam HLS kaydı oynatılabilir MP4'e <5 dakikada dönüşüyor.
- [ ] Upload 202 → PROCESSING → DONE/FAILED → result/trace akışı çalışıyor.
- [ ] Web UI'da yalnız `teknofest-2026/` önekli tek final image bulunuyor.
- [ ] Image runtime'da ağsız çalışıyor ve output validator'dan geçiyor.
- [ ] İki tam VM/Web UI provası ve recovery drill tamamlandı.
- [ ] README, örnekler ve component README'leri gerçek akışı anlatıyor.
- [ ] Unit/integration/static/manual QA temiz; gerçek ve mock kanıt ayrımı açık.
- [ ] Frozen image/git/model SHA256 değerleri 7 Ağustos 21:00 öncesi kaydedildi.
- [ ] Final 10 dakikalık sunum ve tek sayfalık operasyon runbook'u hazır.

---

## 14. İlk yürütme paketi

Uygulama başladığında ilk paket aşağıdaki sırada açılacaktır:

1. P0 assumptions/source inventory patch'i.
2. Mevcut üç test fail'ini kapatan regression patch'i.
3. P1 canonical Faz 2 manifest + GT adapter patch'i.
4. P2 evaluator patch'i ve ilk low/high baseline raporu.
5. Aynı gün paralel olarak Android HLS→MP4 spike ve Open Gateway fake-transport contract testleri.

İlk paketin stop condition'ı: **G0, G1 ve G2 geçmeden model tuning veya UI polish yapılmaz.** Bu sıra, final haftasında “ekran hazır fakat ölçülebilir AI/container yok” veya “model hazır fakat mobil kayıt çalışmıyor” risklerini erken görünür kılar.
