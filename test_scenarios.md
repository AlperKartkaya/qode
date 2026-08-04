# Teknofest QoDe Projesi Test Senaryoları (Uçtan Uca)

Bu doküman, Teknofest yarışma jürisi karşısında ve öncesinde sistemin tüm yeteneklerini (Docker, Backend, Yapay Zeka, Mobil Uygulama) doğrulamak için hazırlanmış **Kapsamlı Test Senaryolarını** içerir.

---

## 🧪 BÖLÜM 1: Çevrimdışı Jüri Testi (Offline Inference - %50 Puan)

Jürinin yarışma ortamında bizim uygulamamıza/sunucumuza ihtiyacı olmadan yapacağı bağımsız Docker testinin simülasyonudur.

### Senaryo 1.1: Standart Video Analizi (Başarı Durumu)
* **Önkoşul:** Docker imajı VM'de başarıyla derlenmiş olmalı (`teknofest-2026/qode-final:latest`).
* **Adımlar:**
  1. Sunucuda `/app/data/input` klasörüne örnek bir `video.mp4` dosyası kopyalanır.
  2. Docker imajı çalıştırılır:
     ```bash
     docker run -v $(pwd)/data/input:/app/data/input -v $(pwd)/data/output:/app/data/output teknofest-2026/qode-final:latest
     ```
* **Beklenen Sonuçlar:**
  - [ ] İmaj sorunsuz şekilde başlar (İnternet veya dış bağlantı hatası vermez, modeller imajın içindedir).
  - [ ] Analiz **10 dakikadan kısa** sürede tamamlanır.
  - [ ] `data/output/results.json` dosyası oluşur.
  - [ ] JSON formatı tam olarak FTR standartlarındadır: `video_id`, `arac_bilgisi` (`tip`, `plaka`, `renk`, `confidence_score`), ve `tespitler` (`zaman_saniye`, `kategori`, `etiket`, `confidence_score`).

### Senaryo 1.2: Olay Tekilleştirme (Deduplication) Testi
* **Adımlar:** Sürücünün uzun süre (örn: 5 saniye) telefonla konuştuğu bir video ile Senaryo 1.1 tekrar edilir.
* **Beklenen Sonuç:**
  - [ ] `results.json` içerisindeki `tespitler` listesinde ardı ardına saniyelerce aynı etiket yığılmaz.
  - [ ] Eylem sadece **başlangıç saniyesi** ve olayın en yüksek doğruluk (confidence) skoruyla **tek bir kayıt** olarak çıkar.

---

## 📱 BÖLÜM 2: Canlı Demo ve Sunum Testi (Live Demo - %25 Puan)

Sizin telefonunuzdan jüri karşısında yapacağınız uçtan uca canlı şov testidir. Mobil uygulamanın VM sunucunuzla entegre çalışması gerekir.

### Senaryo 2.1: Telekom Doğrulama (NV) ve QoD Entegrasyonu
* **Önkoşul:** Android uygulamanız VM IP'sine bağlıdır.
* **Adımlar:**
  1. Telefon numaranızı girip "Sign in" butonuna basarsınız.
  2. Doğrulama başarılı olduktan sonra "QoD Session" kartındaki **"Activate Quality-on-Demand"** butonuna basarsınız.
* **Beklenen Sonuç:**
  - [ ] OIDC (Numara Doğrulama) geçilir ve Home sekmesine yönlendirilir.
  - [ ] Telefon numaranız, Flow ID ve Correlation ID ekranda görünür.
  - [ ] QoD aktif olur ve statüsü yeşil (↑ 1080p Boosted) olarak güncellenir.
  - [ ] Alt sekmedeki **Trace** bölümünde Open Gateway API logları listelenir (`POST /nv/verify` -> 200 OK, `POST /qod/session` -> 201 Created).

### Senaryo 2.2: Canlı Yayın (HLS) Kaydı ve Lifebox'a Aktarım
* **Adımlar:**
  1. Kaynak olarak "HLS" seçilir.
  2. **"Teknofest Start"** butonuna basılır.
* **Beklenen Sonuç:**
  - [ ] Ekranda ExoPlayer açılır ve video canlı oynamaya başlar.
  - [ ] Kayıt devam ederken alttaki upload ve paylaşım butonları **"Recording Stream... Please Wait"** şeklinde devre dışı (disabled) kalır.
  - [ ] Kayıt bitince butonlar aktif olur ve video başarıyla `.mp4` formatında cihaz belleğine alınır.
  - [ ] **"ZIP & Share via Lifebox"** butonuna basıldığında Android Paylaşım Ekranı açılır (ve MP4 kayıpsız zip'lenmiş durumdadır).

### Senaryo 2.3: Backend Yükleme ve Yapay Zeka Sonucu Gösterimi
* **Adımlar:**
  1. Senaryo 2.2 tamamlandıktan sonra **"Upload Video to Backend"** butonuna basılır.
  2. Uygulama otomatik olarak **AI Result** sekmesine geçer.
* **Beklenen Sonuç:**
  - [ ] Video VM sunucusuna (`/upload`) başarıyla iletilir.
  - [ ] Ekranda **canlı ilerleme çubuğu** (Progress Bar) %0'dan %100'e doğru adımlarıyla (YOLO11x yükleniyor, OCR çalışıyor vb.) animasyonlu şekilde akar.
  - [ ] Analiz bitince (Backend 100% DONE dönünce):
    - [ ] Araç Detayları kartı belirir (Tip, Plaka, Renk, Confidence).
    - [ ] İhlaller Zaman Çizelgesi (Timeline) formatında, saniye saniye ikonlarla listelenir.
    - [ ] Ham (Raw) JSON yeşil terminal fontuyla gösterilir.

---

## 🛑 BÖLÜM 3: Hata Toleransı ve Kesinti Testleri (Resilience)

Sistemlerin terslik durumunda çökmemesi ve alternatif yollara girebilmesini sınar.

### Senaryo 3.1: QoD API Çökmesi Durumu
* **Adımlar:** Backend'deki QoD API çağrısı kasıtlı olarak başarısız yapılır (veya Turkcell API hata döner).
* **Beklenen Sonuç:**
  - [ ] Uygulama çökmez.
  - [ ] Kullanıcıya "QoD Açılamadı" uyarısı verir ancak **video indirme işlemi engellenmeden** normal kalitede devam eder (Şartname kuralı).

### Senaryo 3.2: Canlı Yayına Ulaşılamaması (Offline HLS)
* **Adımlar:** Teknofest m3u8 linki bozulur veya internet kesilir.
* **Beklenen Sonuç:**
  - [ ] Uygulama çökmez.
  - [ ] Cihaz içine gömülü (fallback) demo video üzerinden analiz adımları aynen sürdürülür (Böylece sunum yarıda kalmaz).

---

> **Not:** Yukarıdaki senaryolar onaylandığında, Deploy işlemi bittikten hemen sonra **Bölüm 2 ve Bölüm 3**'teki Canlı Demo Senaryolarını fiziksel olarak telefon/emülatör üzerinden test edebilirsiniz.
