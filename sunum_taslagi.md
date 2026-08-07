# QoDe — TEKNOFEST 2026 Sunum Taslağı (v4 — Şartname + KTR Uyumlu)
### 5G ve Yapay Zekâ ile Akıllı Yol Güvenliği — Final Aşaması

---

## 🗂️ İçindekiler

```
┌──────┬──────────────┬──────────────┬──────────────┬──────────────┬──────────────┐
│  01  │      02      │      03      │      04      │      05      │      06      │
│      │              │              │              │              │              │
│Prob- │    Veri      │   Sistem     │     5G       │  Doğrulama   │   Vizyon     │
│ lem  │Mühendisliği  │  Mimarisi    │  Entegrasyonu│  & Kanıt     │              │
└──────┴──────────────┴──────────────┴──────────────┴──────────────┴──────────────┘
```

**Puanlama ağırlıkları (jüriye görünür alt not):**
> YZ Doğruluk **%40** · 5G API Entegrasyonu **%40** · Mimari & Sunum **%20**

---

## ⏱️ Zaman Planlaması

| # | Başlık | Süre |
|---|--------|------|
| 01 | Problem | 1 dk |
| 02 | Veri Mühendisliği | 1.5 dk |
| 03 | Sistem Mimarisi | 3 dk |
| 04 | 5G Entegrasyonu | 1 dk |
| 05 | Doğrulama & Kanıt | 1.5 dk |
| 06 | Vizyon | 1 dk |

---

## 01 — Problem

**Görsel Fikri:** Slayt ikiye bölünmüş.
- Sol: Bir MOBESE direği, üzerinde kamera. Altında büyük yazı: *"400.000+ trafik kamerası — hepsi pasif"*
- Sağ: O kameradan gelen görüntüde telefona bakan sürücü — ama ekranın sağ üstünde sadece kırmızı bir kayıt ikonu var. Hiçbir uyarı yok, hiçbir tespit yok.
- Ortada tek cümle: **"Görüyor ama görmüyor."**

### Asıl Problem: Kameralar Pasif

> **Türkiye'de yüz binlerce yol kenarı kamerası var.**  
> **Hepsi kayıt yapıyor. Hiçbiri tehlikeli sürücüyü anında tespit etmiyor.**

**Soru:** Bu kameralar zaten var. Onları akıllandırabilir miyiz?

### QoDe'un Cevabı: Pasif Kameradan Aktif Güvenlik Sistemine

```
MOBESE Kamerası
      │  canlı video akışı
      ▼
  QoDe Engine   ──►  Araç tipi & rengi
                ──►  Plaka (OCR)
                ──►  Kabin: telefon, teknocan, bilgisayar
                ──►  Sürücü: sigara, esneme, etrafa bakma
                ──►  Emniyet kemeri ihlali
                ──►  Yolcu koltuk durumu
      │
      ▼
  5G Open Gateway  (QoD: ihtiyaç varken ağ önceliği)
      │
      ▼
  Anlık raporlama — FTR şemasına uygun
```

### Teknik Zorluklar (Yol Kenarı Kamerasına Özgü)

| Zorluk | Neden | Çözümümüz |
|--------|-------|-----------|
| Plaka küçük & bulanık | Kamera uzakta, hareket var, parlama | 6-varyant OCR preprocessing |
| Cam yansıması & parlama | Güneş, ıslak yol, kirli cam | Adaptif anti-glare pipeline |
| Tek kare yetmez | Yana bakmak ≠ ihlal; süreklilik şart | 3 sn temporal smoothing |
| Aynı anda 5 görev | Plaka + kabin + sürücü + araç + yolcu | Hibrit: 5 model + 3 algoritma |

### Şartname Hedefleri (Madde 4.4)

> *"Araç plakası, araç içi nesneler, sürücünün yorgunluk durumu, sigara veya telefon kullanımı gibi yol güvenliğini tehdit edebilecek sürücü davranışları ve unsurları tespit edilecek."*

| Hedef Ailesi | Etiketler |
|-------------|----------|
| Araç bilgisi | `plaka`, `araç tipi`, `araç rengi` |
| Sürücü eylemi | `telefonla_konusma`, `sigara_icme`, `esneme`, `su_icme`, `etrafa_bakinma`, `arkaya_bakma` |
| Nesneler | `teknocan`, `bilgisayar` |
| Yolcular | `on_koltuk`, `arka_koltuk_1`, `arka_koltuk_2`, `emniyet_kemeri_ihlali` |

**Konuşma Metni:**
> "Türkiye'de yüz binlerce yol kenarı kamerası var. Hepsi görüntü kaydediyor. Ama bunların hiçbiri sürücünün sigara içtiğini, telefonla konuştuğunu ya da emniyet kemerini takmadığını gerçek zamanlı tespit edemiyor. Kaza olunca kameraya bakıyoruz — ondan önce değil. QoDe bu soruyu soruyor: Bu kameralar zaten kurulu, onları akıllandırabilir miyiz? 5G Open Gateway ile ağ önceliği alarak, yapay zeka ile analiz ederek, pasif kamerayı aktif güvenlik sistemine dönüştürmek mümkün."

---

## 02 — Veri Mühendisliği

**Görsel Fikri:** Sol: Veri kaynaklarının akış şeması (oklu bağlantılarla FTR etiketlerine doğru). Sağ: Windshield Simulator girdi-çıktı karşılaştırması.

### Veri Ekosistemi — Çok Kaynaklı, FTR'ye Eşlenmiş

| Kaynak | Boyut | FTR Hedef Ailesi | Eşleme |
|--------|-------|-----------------|--------|
| **State Farm** | 22.424 görüntü, 10 sınıf | `sofor_eylemi` | `phone_left/right` → `telefonla_konusma`, `reaching_behind` → `arkaya_bakma`, `c6` → `su_icme` |
| **DMD Distraction** | Çoklu kamera, OpenLABEL | `telefonla_konusma`, `su_icme`, `etrafa_bakinma` | OpenLABEL JSON → FTR etiketi |
| **DMD Drowsiness** | Çoklu kamera, gaze/yawn | `esneme` | `yawning/Yawning with hand` → `esneme` |
| **Teknocan Aug.** | 315 → ~6K (artırma) | `nesneler/teknocan` | MixUp + mosaic + cam tonu |
| **Sentetik Plaka** | ~5K sentetik | `plaka` OCR eğitimi | regex doğrulama zinciri |

> **Etiketleme stratejisi:** Açık kaynak etiketler FTR sınıflarına doğrudan yazılmadı; önce dönüştürüldü. `safe_driving` çıkarıldı. Desteklenmeyen sınıflar hiç kullanılmadı. (KTR §2 Etiketleme)

### Slayt 2A: Eğitim-Saha Uçurumunu Kapatmak

*(Slayt Sol Taraf - 3 Satırlı Liste Tasarımı)*

**Kritik Mühendislik Kararı:**
> Augmentasyon için tek bir yapı yerine, birbirini tamamlayan iki ayrı bileşen tasarladık: Diske yazılan statik veri ve eğitim sırasında canlı uygulanan dinamik veri.

**Windshield Simulator (Statik):**
> Eğitim verisini önceden saha koşullarına uydurur. Veri setinin %80'ine bir kez uygulanarak diske yazılır. Sabit cam yansıması (0.10-0.22) ve yeşil tonlu ticari araç cam rengi ekler.

**Windshield Transform (Dinamik):**
> Her eğitim döngüsünde (epoch) modele yeni bir varyasyon sunar. Eğitim sırasında %50 olasılıkla canlı uygulanır. Değişken yansıma (0.08-0.20) ve tamamen rastgele RGB tonları üretir.

### Slayt 2B: Eğitim-Saha Uçurumunun Sayısal Kanıtı

**Soru:** Windshield Simulator'e gerçekten ihtiyaç var mıydı?

*(Tasarım Fikri: Ortadan ikiye bölünmüş büyük rakamlı (ör: %65.5 olan) şablon)*

*   **Sol Taraf: Simülatör Olmadan (Sadece Temiz Veri)**
    *   **Dev Rakam:** %40.1 *(Saha/Test Başarısı)*
    *   *Açıklama:* Model, temiz State Farm verisinde **%99.2** eğitim başarısı gösterse de; gerçek yol kamerasındaki güneş yansıması ve cam kiriyle karşılaşınca test verimizde tamamen çuvalladı. (Domain Gap - Alan Uçurumu)

*   **Sağ Taraf: Windshield Simulator İle (QoDe Yaklaşımı)**
    *   **Dev Rakam:** %82.7 *(Saha/Test Başarısı)*
    *   *Açıklama:* Simülatör ile eğitim verisine yansıma ve kirlilik (Domain Adaptation) eklendiğinde; modelin eğitim başarısı **%85.4**'e düştü ama sahada karşılaştığı zorlu veriyi ezberlemeden anlamaya başladı.

### Slayt 2C: Veri Dengeleme ve Model Genelleme

Saha verilerinde "güvenli sürüş" çok fazlayken, "sigara içme" veya "esneme" gibi kritik ihlaller çok azdır. Modelin azınlık sınıfları ezberlemesini önlemek için 4 strateji uyguladık:

1. **Örneklem Dengeleme (`WeightedRandomSampler`):**
   * Az bulunan sınıflar (sigara, esneme) daha sık gösterilerek modelin adil öğrenmesi sağlandı.

2. **Aşırı Güveni Önleme (`label_smoothing=0.1`):**
   * Modelin "%100 emin" olması engellenerek, farklı açılardaki yeni verilere uyumu artırıldı.

3. **Görsel Çeşitlilik (`RandAugment`):**
   * 9 farklı yapısal dönüşüm, her kareye rastgele uygulanarak ezber kırıldı.

4. **Sürücü Bazlı Ayrım (Data Leakage Koruması):**
   * Aynı kişinin fotoğrafları hem eğitim hem test setine *asla* konulmadı. Model yüze değil, "eyleme" odaklandı.

**Konuşma Metni:**
> "17.5 milyon satır telemetri verisi, dört farklı veri seti, altı farklı augmentasyon tekniği. Ama en önemli kararımız veri mühendisliğindeki bu ikili yapı. Windshield Simulator veriyi saha koşullarına taşıyor — bir kez, diske. Transform ise her epoch'ta farklı kombinasyonlar deniyor. İkisini aynı anda kullansaydık, test ettik, eğitim başarısını mahvediyordu."

---

## 03 — Sistem Mimarisi

*(Görsel Fikri: Ortada merkez kutu, etrafına açılan 4 farklı kol. Aynen yüklediğin mind-map (kavram haritası) şablonundaki gibi.)*

---

## 03 — Sistem Mimarisi (Kavram Haritası)

*(Görsel Fikri: Slaytta az önce hazırladığın 4 kollu mind-map yer alacak. "Zaman ve Ağ Kararı" bölümünü buraya sığdırmak yerine, sunumun akışında sona sakladık.)*

---

### Slayt 3A: Ön İşleme (Görmeden Önce Temizle)

*(Tasarım Fikri: 4 Sütunlu İkonlu Tasarım)*

**1. Sütun (İkon: Güneş veya Kalkan)**
*   **Başlık:** Adaptif Çevresel Filtreler
*   **Metin:** Yol kenarı kameralarında parlama ve kirlilik kaçınılmazdır. Sistemimiz her kareyi analiz eder; sadece ihtiyaç anında **Anti-Glare**, **Denoise** ve **Sharpen** filtrelerini devreye sokarak işlem gücünden tasarruf sağlar.

**2. Sütun (İkon: Kırpma / Crop)**
*   **Başlık:** İlgi Alanı (ROI) Çıkarımı
*   **Metin:** Devasa 4K MOBESE karesini modellere sokmak hızı (FPS) düşürür. Bu nedenle YOLO11x Ana Dedektörümüz ile sadece hedef araç ve sürücü bölgesi kırılarak analiz edilecek veri boyutu küçültülür.

**3. Sütun (İkon: Büyüteç veya Beyin)**
*   **Başlık:** LAB-CLAHE & LANCZOS4
*   **Metin:** Sürücünün yüzü kameraya uzak veya karanlık kalırsa model hata yapabilir. Bunu önlemek için kırpılan sürücü alanı **Lanczos4** ile matematiksel büyütülür ve **LAB-CLAHE** ile lokal kontrastı aydınlatılır.

**4. Sütun (İkon: Plaka veya Yazı)**
*   **Başlık:** 6-Varyantlı Plaka İyileştirmesi
*   **Metin:** Plaka okuma (OCR) öncesinde, görüntüye eşzamanlı olarak 6 farklı eşikleme (threshold) uygulanır. En yüksek güven skorunu veren sonuç, FTR şemasına uygun regex filtresinden geçerek sisteme alınır.

### Slayt 3B: Derin Öğrenme Modelleri (Böl ve Yönet)

*(Tasarım Fikri: Gönderdiğin "6 Maddelik Izgara (Grid)" şablonu. Sol tarafta büyük başlık, sağ tarafta 6 madde.)*

**Sol Taraf (Büyük Başlık):**
Mikromimari: Özel Eğitilmiş Modeller

**Sağ Taraf (6 Maddelik Grid):**

**01. Ana Dedektör (YOLO11x)**
Her şeyi tek modele yüklemek yerine, sadece araçları ve sürücüleri tespit eden "Ana Göz" olarak konumlandırıldı.

**02. Sürücü Davranışı (EfficientNet-B2)**
Telefon, esneme ve su içme gibi 10 farklı ihlali sınıflandırmak için kendi veri setlerimizle **özel olarak eğitildi**.

**03. İnce Detay Araç Tipi (EfficientNet-B0)**
Araçların Sedan/SUV gibi alt kırılımlarını bilmesi için TTA (Test-Time Augmentation) desteğiyle **kendi modelimiz eğitildi**.

**04. Özel Nesne: Teknocan (YOLO11n)**
Yarışmaya özel bu nesne için hazır model yoktu. 6.000 artırılmış görselle bu dedektörü **sıfırdan biz eğittik** (%99.5 mAP).

**05. Plaka Tespit (YOLO11n)**
Hızı maksimize etmek amacıyla, sadece plaka bölgesini bulup kırpan özel ve hafif bir Nano model kullanıldı.

**06. Yüz ve Sigara (TorchScript)**
Uzak kameradaki zorlu tespiti çözmek için sadece dudak bölgesini kırpan, **özel eğitilmiş** son derece hafif bir alt bileşen.

**Konuşma Metni:**
> "Her şeyi devasa tek bir YOLO modeline yükleyip sistemin hızını öldürebilirdik. Bunun yerine mikromimariyi tercih ettik. YOLO11x sadece temel tespiti yapıyor. Geri kalan plaka, araç tipi, sigara ve Teknocan gibi spesifik görevler için, sıfırdan bizim eğittiğimiz Nano ve EfficientNet sınıflandırıcıları milisaniyeler içinde devreye giriyor. Özellikle hazır bir veri seti olmayan Teknocan modelini 315 fotoğraftan 6.000 fotoğrafa çıkartarak sıfırdan kendimiz eğittik."

### Slayt 3C: Yapay Zekanın Sınırları (Klasik CV ve Geometri)

*(Tasarım Fikri: Gönderdiğin sol tarafı koyu, sağ tarafı 3 resim ve 3 sütunlu şablon)*

**Sol Taraf (Koyu Alan - Büyük Başlık):**
Yapay Zekanın Sınırları: Geometri ve Matematik

**Sağ Taraf (3 Sütunlu Alan):**

**01. Zone-Logic (Koltuk Konumu)**
Yolcunun önde mi arkada mı olduğunu modele öğretmek zordur. Bunun yerine, yolcu BBOX alanının aracın toplam alanına oranını (%12) hesaplayan kesin geometrik kurallar kullandık.

**02. K-Means (Araç Rengi)**
Değişen ışık koşulları yapay zekayı yanıltabilir. Derin öğrenme yerine, kırpılan araç görüntüsündeki en baskın 3 rengi (k=3) matematiksel olarak kümeleyerek kesin renk tespiti yaptık.

**03. Hough Lines (Emniyet Kemeri)**
Emniyet kemeri daima düz bir çizgidir. Ağır bir model eğitmek yerine, klasik kenar tespiti (Edge Detection) ve çizgi dönüşümü ile sürücü gövdesindeki çapraz şeridi aradık.

**Konuşma Metni (3C):**
> "Her problemi yapay zekayla çözmeye çalışmak, bazen hem hızı düşürür hem de hata payını artırır. Biz sistemimizde yapay zekanın sınırlarını bildik. Örneğin arka koltuktaki bir yolcuyu kameranın perspektifinden dolayı model ön koltukta sanabilir. Ama basit bir Zone-Logic geometrisi ile 'eğer kapladığı alan %12'den küçükse kesin arkadadır' diyerek hata payını sıfırladık. Aynı şekilde emniyet kemeri ve araç rengi gibi yapısal problemleri ağır modeller yerine K-Means ve Hough Lines gibi klasik ama %100 kesin matematiksel algoritmalarla çözdük."

### Slayt 3D: Zaman Tamponu ve FTR Çıktısı (Karar Mekanizması)

*(Tasarım Fikri: Önceki 3 sütunlu şablon. İkonlar: Kronometre, Dosya, Kalkan)*

**Sol Taraf (Koyu Alan - Büyük Başlık):**
Yapay Zeka Yanılırsa Ne Olur? (Hata Önleme)

**Sağ Taraf (3 Sütunlu Alan):**

**01. Temporal Smoothing (3 Sn. Kuralı)**
Yapay zeka tek bir sarsıntılı karede sürücünün elini "telefon" sanabilir. Sistemimiz anında alarm vermez. Olayın **kesintisiz 3 saniye** devam edip etmediğini kontrol ederek yanlış alarmları (False Positive) engeller.

**02. Kümülatif Risk Skorlaması**
Sistem sadece ihlalleri saymaz, sürücü için anlık bir risk skoru hesaplar. Sigara içmek riskliyken, hem sigara içip hem telefonla konuşmanın risk çarpanı çok daha yüksektir.

**03. FTR JSON Doğrulayıcı**
Jüriye gidecek sonuçlar, yola çıkmadan önce kendi içimizde bir Regex (Format) kontrolünden geçer. Şartnamedeki JSON şemasına uymayan tek bir virgül bile dışarı çıkmaz, veriler %100 uyumlu teslim edilir.

**Konuşma Metni:**
> "Mimarimizin son ve en kritik adımı karar mekanizması. Bir model %99 başarılı olsa bile tek bir karede yanılabilir. Bu yüzden sistemimize 'Temporal Smoothing' yani Zaman Tamponu ekledik. İhlal 3 saniye kesintisiz sürmezse alarm çalmıyor. Ayrıca elde ettiğimiz tüm bu verileri doğrudan FTR (Final Tasarım Raporu) şemasına tam uyumlu, kendi içinden doğrulanmış bir JSON formatına dönüştürüp merkeze iletiyoruz. Buradan çıkan onaylı veriler, hemen bir sonraki adım olan 5G ağına iletiliyor."

### Detaylı Mimari Akışı
```
     Video @ 4 FPS
     │
     ▼  YOLO11x Ana Dedektör
     │
     ├──► Araç Crop
     │     ├──► [MODEL 3] EfficientNet-B0 + TTA    → araç tipi
     │     ├──► [MATH 1] K-Means (k=3)             → araç rengi
     │     └──► [MODEL 5] license_plate_det         → plaka konumu
     │                └──► 6-varyant OCR enhance    → plate_text
     │
     ├──► Sürücü Crop
     │     ├──► LAB-CLAHE + LANCZOS4 enhance
     │     ├──► [MODEL 1] driver_classifier (EfficientNet-B2) → sofor_eylemi
     │     ├──► Haar Cascade yüz crop
     │     │     └──► [MODEL 2] smoker_classifier (TorchScript) → sigara_icme
     │     └──► [MATH 2] Hough Lines               → emniyet_kemeri
     │
     ├──► Yolcu Bölgesi
     │     └──► [MATH 3] Zone-Logic               → koltuk ataması
     │
     └──► Nesne Crop
           └──► [MODEL 4] teknocan_detector (YOLOv11n) → teknocan, bilgisayar
                              │
                              ▼
                    Temporal Smoothing (3 sn)
                              │
                              ▼
                     FTR Validator + Atomik JSON
```

### Dal 1: Preprocessing — Adaptif 3-Yol

| Koşul | Filtre | Teknik |
|-------|--------|--------|
| brightness < 80 (gece) | Bilateral Filter | d=5, σColor=50, σSpace=50 |
| brightness > 130 (güneş) | Gamma LUT + LAB-CLAHE | γ adaptif, clipLimit=1.5 |
| Her zaman | Unsharp Mask | addWeighted(1.2, -0.2) |
| Sürücü crop | LAB-CLAHE + LANCZOS4 | clipLimit=2.5, 2x upscale |
| Plaka crop | 6-varyant | 4x↑ → CLAHE → Adaptive/Otsu/Sharp/HiContrast |

### Dal 2: 5 Model

| Model | Mimari | Eğitim Kaynağı | Çıktı |
|-------|--------|---------------|-------|
| `driver_classifier.pt` | EfficientNet-B2 | State Farm + DMD (~22K) | 10 sınıf sofor_eylemi |
| `smoker_classifier.pt` | TorchScript binary | Sigara videoları | sigara_icme |
| `vehicle_type_classifier.pt` | EfficientNet-B0 + TTA | Roboflow + Stanford Cars | 7 FTR tipi |
| `teknocan_detector.pt` | YOLOv11n | 315→6K augmented | teknocan, bilgisayar |
| `license_plate_detector.pt` | YOLOv11n | Turkish Licence Plate DS | plaka bbox |

**EfficientNet-B2 Eğitim Stratejisi:**
```
Epoch 0–4   : Backbone frozen (lr=3e-4) — sadece head
Epoch 5+    : Progressive unfreeze (features lr=3e-6, 100x düşük)
Label smooth: 0.1 → aşırı güven önleme
WeightedSampler → sınıf dengesizliği giderildi
gradient clip=1.0 → patlayan gradyan koruması
```

### Dal 3: Matematiksel Algoritmalar

**K-Means Renk (< 1ms, deterministik):**
```
Araç crop → merkez %60-80 ROI → BGR→RGB → cv2.kmeans(k=3, KMEANS_PP)
→ dominant küme → FTR paleti Euclidean NN
Palet: beyaz / siyah / gri / kırmızı / mavi / sarı / yeşil / turuncu / kahverengi
```

**Zone-Logic Koltuk (model gerekmez):**
```
Araç bbox yatay 1/3'e bölünür (Türkiye sağ el trafiği)
kişi_alanı / araç_alanı < 0.12 → arka koltuk (uzak = küçük görünür)
Sağ 1/3 = on_koltuk · Max 2 arka koltuk (FTR şartnamesi)
```

**Hough Lines Emniyet Kemeri:**
```
Sürücü üst %70 torso → Canny(50,150) → HoughLinesP
20° < açı < 70° VE uzunluk > %12×height → emniyet kemeri VAR
Bulunamazsa → emniyet_kemeri_ihlali (conf=0.62)
```

**Smoker — Yüz Crop:**
```
Haar Cascade → en büyük yüz + alt marjin %45 (ağız/çene dahil)
Fallback: sürücü crop'un üst %35
→ TorchScript binary → idx==1 AND conf > 0.60
```

### Dal 4: Çıktı Mühendisliği

| Bileşen | Davranış |
|---------|----------|
| **Temporal Smoothing** | 3 sn tampon, persistence filtresi, episode deduplication |
| **FTR Validator** | Etiket sözlüğü, regex, confidence aralığı, alan bütünlüğü |
| **Atomik Yazım** | `tmp → validator → os.replace()` → yarım JSON imkânsız |
| **Fail-closed** | Eksik model → non-zero exit; stale output silinir; ağsız çalışma |

---

## 04 — 5G API Entegrasyonu (CAMARA Standartları)

*(Tasarım Fikri: Gönderdiğin resimdeki gibi Sol tarafta başlık, Ortada 3 çizgili madde, Sağda teknolojik bir görsel)*

**Sol Taraf (Başlık Alanı):**
*   **Başlık:** 5G Open Gateway Entegrasyonu
*   **Alt Metin:** Şartnamenin **%40'lık** puan ağırlığını oluşturan 5G CAMARA ağ API'lerini mobil sistemimize nasıl entegre ettik?

**Orta Taraf (3 Maddelik Liste):**

**01. OIDC ile Number Verification**
Sisteme giriş yapan yetkilinin cihazı, SMS (OTP) koduna gerek kalmadan `POST /verify` uç noktası (endpoint) üzerinden operatör ağıyla konuşarak arka planda saniyeler içinde doğrulanır.

**02. Akıllı Tetikleyici (Trigger) Mantığı**
Sistem sürekli ağ önceliği talep ederek bant genişliğini israf etmez. Sadece "Sürücü risk skoru çok yüksekse" veya "Kanıt görüntüsü bulanıksa" 5G API'lerini tetikleme kararı alır.

**03. Quality on Demand (QoD) Aktivasyonu**
İhlal kesinleştiğinde sistem `POST /sessions` çağrısı yaparak ağdan "QOS_E (Boosted)" profili talep eder. 1080p acil durum kanıt videosu, ağdaki trafikten etkilenmeden VIP şeritten merkeze akar.

**Konuşma Metni:**
> "Yarışmada en kritik konulardan biri 5G entegrasyonuydu ve biz bunu doğrudan uygulamanın çekirdeğine kodladık. Jürimizi uzun JSON kodlarına boğmak istemiyoruz; ancak şunu bilmenizi isteriz ki, sistemimiz CAMARA standartlarına birebir uyumludur. Sürekli ağ önceliği istemiyoruz. Sisteme akıllı bir tetikleyici yazdık. Eğer yapay zeka 'Burada kesin bir ihlal var ama çözünürlük düşerse kanıtlayamam' derse, sistem otomatik olarak 'POST sessions' çağrısı atıyor ve QoD üzerinden QOS_E (Boosted) profiline geçiyor. Yani 5G ağı, yapay zekanın emrine amade şekilde sadece ihtiyaç anında esniyor."

---

## Slayt 4B: Mobil Komuta Merkezi (Native Android)

*(Tasarım Fikri: Gönderdiğin resimdeki gibi Sağ taraf siyah arka planda büyük başlık, Sol taraf 4 satırlı birbirine zıt (zigzag) resim/metin yerleşimi)*

**Sağ Taraf (Koyu Alan - Büyük Başlık):**
Mobil Komuta Merkezi
(Native Android)

**Sol Taraf (4 Satırlı Zikzak Yapı):**

**Satır 1 (Resim Solda, Metin Sağda): Native Kotlin & Jetpack Compose**
Sistemi cross-platform (React/Flutter) yerine doğrudan **Kotlin** ile yerel (Native) olarak kodladık. Kamera ve ağ trafiği süreçlerinde cihaz donanımından maksimum performans elde edildi.

**Satır 2 (Metin Solda, Resim Sağda): ExoPlayer ile Adaptif Akış**
Canlı yarışma yayını standart bir player yerine Media3 ExoPlayer ile entegre edildi. Video donmaz, kalite anlık 5G ağ hızına göre kendi adaptif ayarını (Adaptive Bitrate) yapar.

**Satır 3 (Resim Solda, Metin Sağda): Lifebox ve ZIP Otomasyonu**
Operatörün manuel dosya işlemlerini engellemek için Android Intent API'leri kullanıldı. Çekilen video otomatik kaydedilir, ZIP'lenir ve tek tuşla doğrudan **Lifebox**'a yüklenir.

**Satır 4 (Metin Solda, Resim Sağda): Gerçek Zamanlı AI Dashboard**
İhlal sonuçları kafa karıştırıcı JSON formatında yığılmaz. Tespitler görsel bir Zaman Çizelgesi (Timeline) ve Araç Kimlik Kartı olarak operatörün ekranına saniyeler içinde düşer.

**Konuşma Metni:**
> "Sahadaki ekiplerin saniyelerle yarıştığını biliyoruz, bu yüzden hantal web panellerine değil, hızlı bir mobil uygulamaya ihtiyacımız vardı. Sistemi %100 Native Kotlin ve Jetpack Compose ile kodladık. Tüm tasarımımız operatörün işini kolaylaştırmak üzerine kurulu. Canlı yayın ExoPlayer ile donmadan ekrana geliyor. Bir ihlal kaydedildiğinde kullanıcının klasörlerde dosya aramasına gerek kalmıyor; sistem onu otomatik zipleyip tek tuşla Lifebox'a aktarıyor. Çıkan yapay zeka sonuçları ise kod yığınları olarak değil, görsel bir 'Zaman Çizelgesi' olarak operatöre sunuluyor. Kısacası bu sadece bir demo değil, sahada çalışmaya hazır gerçek bir mobil komuta merkezidir."

## 05 — Doğrulama & Kanıt (Uçtan Uca Testler)

*(Tasarım Fikri: Yapay Zeka slaytında kullandığımız "6 Maddelik Izgara (Grid)" şablonu. Sol tarafta büyük başlık, sağ tarafta 6 madde.)*

**Sol Taraf (Büyük Başlık):**
Doğrulama & Kanıt: Sistem Testleri

**Sağ Taraf (6 Maddelik Grid):**

**01. Bağımsız Docker Testi**
Modellerin gömülü olduğu Docker imajımız, dış internet bağlantısı gerektirmeden kapalı sistemde (VM) uçtan uca çalışarak kusursuz JSON üretir.

**02. Olay Tekilleştirme (Deduplication)**
Bir ihlal saniyelerce sürse bile, JSON çıktısında yüzlerce kez tekrarlanmaz; en yüksek doğruluk skoruyla **tekil bir olay** olarak raporlanır.

**03. OIDC ve QoD Doğrulaması**
Mobil uygulamadaki "QoD Session" butonuyla arka planda kimlik doğrulama atlanır (NV) ve canlı ağda VIP öncelik (Boosted Profile) tetiklenir.

**04. HLS Kaydı ve Lifebox**
Canlı HLS yayını ExoPlayer ile ekranda oynatılırken cihaz belleğine kayıpsız MP4 olarak kaydedilir, zıplenir ve tek tuşla Lifebox'a aktarılır.

**05. Gerçek Zamanlı Yönetim Ekranı**
Sunucuya yüklenen video işlenirken mobil uygulamada "İlerleme Çubuğu" akar; bitiminde ihlaller bir Zaman Çizelgesi (Timeline) üzerinde görselleştirilir.

**06. Kesinti Toleransı (Resilience)**
Turkcell QoD API'si çökse veya internet kopsa dahi uygulama kapanmaz; 5G talebini iptal eder veya yedek video üzerinden şovunu kesintisiz sürdürür.

**Konuşma Metni:**
> "Yarışma şartnamesinde bize spesifik test senaryoları verilmemişti. Ancak biz sistemin gücünü kanıtlamak için kendi 'Uçtan Uca Test Senaryolarımızı' yazdık. Jüri olarak sistemimizi internet olmayan kapalı bir Docker ortamında test ettiğinizde kusursuz çalıştığını göreceksiniz. Canlı demomuzda ise HLS akışından kayıt almaya, bu kaydı Lifebox'a atmaya ve hatta internetin koptuğu felaket senaryolarında uygulamanın çökmeden yedek video ile analizine devam etmesine (Resilience) kadar her ihtimali test ettik ve onayladık."

---

## 06 — Vizyon ve Kapanış (2 Slayt)

### Slayt 6A: Sistemin Geleceği ve Esnekliği
*(Tasarım Fikri: Gönderdiğin beyaz arkaplanlı, 3 sütunlu ve üstünde resimler olan şablon)*

**Ana Başlık:**
Geliştirmeye Açık, Pratik ve Modüler Bir Altyapı

**Sol Sütun (01. Esnek Mimari):**
**Başlık:** Esnek ve Hafif Altyapı
**Alt Metin:** Sistem devasa sunuculara muhtaç değildir. Oluşturduğumuz Docker mimarisi sayesinde, farklı donanımlara kolayca uyum sağlayacak esnekliğe sahiptir.

**Orta Sütun (02. Modüler Tasarım):**
**Başlık:** Modüler ve Büyüyebilir Tasarım
**Alt Metin:** İleride yeni trafik kuralları (örn: kask takmama) eklendiğinde, sistemi baştan yazmaya gerek kalmadan sadece ilgili modül eğitilip sisteme dahil edilebilir.

**Sağ Sütun (03. Kullanıcı Odaklılık):**
**Başlık:** Kullanıcı Odaklı Pratiklik
**Alt Metin:** Geliştirdiğimiz mobil uygulama ve 5G entegrasyonu sayesinde, yapay zeka sonuçları sahada görev yapan ekiplerin ekranına en hızlı ve anlaşılır şekilde ulaşır.

---

### Slayt 6B: Kapanış (Teşekkür)
*(Tasarım Fikri: Gönderdiğin siyah arkaplanlı, sağda dizüstü bilgisayar olan şablon)*

**Sol Taraf (Büyük Yazı):**
Bizi Dinlediğiniz İçin Teşekkür Ederiz!
**Alt Metin:** Aklınıza takılan herhangi bir soruyu yanıtlamaktan memnuniyet duyarız. (Soru & Cevap)

**Konuşma Metni (Final):**
> "Başından beri vizyonumuz, sadece veri seti üzerinde yüksek puan alan bir 'model' eğitmek değil, gerçek hayatta çalışan uçtan uca bir 'ürün' yaratmaktı. Yanlış alarmları kendi içinde süzen algoritmalarıyla, 5G üzerinden VIP şerit açabilen Kotlin uygulamasıyla ve her an deploy edilmeye hazır Docker altyapısıyla QoDe... Geleceğin akıllı şehirlerinin yorulmak bilmeyen yeni gözüdür. Dinlediğiniz için teşekkür ederiz."

---

## 📌 Jürinin Sorabileceği Sorular

### Problem hakkında
**S: Problemi neden 'çok görevli' olarak tanımladınız?**
> Çünkü şartname tek bir video akışında aynı anda araç tipi, plaka, kabin içi ve sürücü davranışını gerektiriyor. Bunlar farklı fiziksel bölgeler, farklı zaman ölçekleri ve farklı algoritmik yaklaşımlar gerektiriyor. Tek bir model bu görevlerin hepsinde suboptimal kalır.

### Veri Mühendisliği hakkında
**S: State Farm veri seti kabin kamerası değil mi? Saha koşullarıyla nasıl uyumsuz?**
> Evet — State Farm kapalı, iyi aydınlatılmış, sabit açılı kabin kamerası görüntüleri içeriyor. Bizim sistemimiz yol kenarı kamerasından sürücüyü ön camdan görüyor; yansıma, tint, uzaklık ve hareket var. Windshield Simulator bu uçurumu kapatıyor.

### Mimari hakkında
**S: Neden 5 model? Tek bir büyük model yetmez mi?**
> Her görevin veri boyutu, annotation formatı ve input bölgesi farklı. Sigara tespiti için yüz crop + binary classifier yeterli; büyük model gereksiz gecikme yaratır. Bağımsız modeller bağımsız güncellenir ve hata izolasyonu daha kolay.

### 5G hakkında
**S: Gerçek Turkcell endpoint olmadan nasıl test ettiniz?**
> CAMARA standart kontratlarına tam uyumlu mock implementasyon yaptık. Tüm trace kodları, QoD kararları ve tetikleyici koşullar mock üzerinde test edildi ve 7/7 senaryo başarılı. Gerçek endpoint, mock'un aynı kontratı kullandığı için drop-in replacement olacak.

### Doğrulama hakkında
**S: F1=1.0 gerçekçi mi?**
> Bu identity smoke testidir — ground truth dosyasını kendisiyle karşılaştırdık. Evaluator'ın doğru çalıştığını kanıtlıyor, model başarısını değil. Gerçek inference sonrası evaluator, tahmin çıktısına gerçek GT ile uygulanacak.

### Vizyon hakkında
**S: Sistemi gerçekte deploy etseydiniz ne gerekirdi?**
> Gerçek Turkcell credential, kamera erişimi ve bir T4 sunucusu. Docker imajı zaten ağsız çalışıyor. Windshield Simulator parametreleri kamera modeline göre kalibre edilmeli. Bunlar teknik engel değil, operasyonel adımlar.
