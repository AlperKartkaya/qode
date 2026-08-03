# QoDe - TEKNOFEST 2026 Sunum Taslağı ve Konuşma Metni

Bu doküman, "5G ve Yapay Zeka ile Akıllı Yol Güvenliği Yarışması" (FTR Aşaması) için hazırlanan 10 dakikalık sunumun detaylı planını, slayt içeriklerini, görselleştirme (grafik/tablo) fikirlerini ve sunucu konuşma metinlerini içermektedir.

---

## 🕒 Zaman Planlaması (10 Dakika)
- **Giriş ve Problem Tanımı:** 1 Dakika
- **Yapay Zeka Mimarisi ve Teknoloji Matrisi:** 2.5 Dakika
- **Veri Kaynakları ve Windshield Simulator:** 3 Dakika
- **Kusursuz Çıktı (FTR) ve Kotlin App:** 2 Dakika
- **Başarılar, Metrikler ve Sonuç:** 1.5 Dakika

---

## 🚀 Bizi Farklı Kılan Özelliklerimiz (Unique Selling Points - USP)
1. **Sentetik Veri Üretimi ve "Windshield Simulator":** Rakiplerimiz standart açık kaynak veri setlerini kullanırken, biz State Farm gibi net çekilmiş verilerin üzerine algoritmik olarak "Cam Yansıması (Windshield)" ve kirlilik filtreleri uyguladık. Modelimizi steril lab ortamına göre değil, yol kenarı kamerasının yansımalı ve zorlu gerçek dünyasına göre eğittik.
2. **Kapsamlı ve Özel Veri Toplama:** Sadece tek bir veri setiyle yetinmedik. İnternetten topladığımız veriler, DMD Distraction/Drowsiness çoklu kamera setleri ve tam 17.5 Milyon satırlık DriverSVT telemetri verisini bir araya getirerek çok boyutlu bir veri ekosistemi kurduk.
3. **Hibrit Teknoloji Matrisi:** Bütün problemleri tek bir modele (sadece YOLO) çözdürmek yerine; her problemi kendi alanının en iyi algoritmasıyla çözdük. OCR için EasyOCR, Renk tespiti için K-Means, Sınıflandırma için EfficientNet, Tespit için YOLO11 kullandık.
4. **Özel Ajan Modeli (Teknocan):** Standart nesnelerin (laptop, telefon) dışında, yarışmaya özel "Teknocan" nesnesini tespit etmek için "Teknocan Augmented" özel YOLOv11n ajan modelini sıfırdan eğittik.
5. **Tamamlayıcı Native 5G Ürün:** Elde ettiğimiz kusursuz yapay zeka gücünü, 5G Open Gateway (Number Verification & Quality on Demand) entegreli Native Kotlin Android uygulaması ile son kullanıcıya ve hakem paneline ulaştırıyoruz.

---

## 📊 Slayt Planı ve Görsel Fikirleri

### Slayt 1: Başlık
- **Görsel Fikri:** QoDe logosu, arka planda soyut bir yol ve veri setlerini temsil eden kod blokları. Alt kısımda TEKNOFEST 2026 logosu.
- **Slayt Metni:** 
  - QoDe: Akıllı Yol Güvenliği Ekosistemi
  - Verinin Gücüyle Şekillenen Yapay Zeka
- **Konuşma Metni:** "Değerli jüri üyeleri, değerli konuklar; hoş geldiniz. Bugün sizlere trafik kazalarını oluşmadan önce tespit edebilecek, verinin gücünü ve yapay zekanın sınırlarını zorladığımız akıllı yol güvenliği projemiz QoDe'u sunmaktan gurur duyuyoruz."

### Slayt 2: Problem ve Çözüm
- **Görsel Fikri:** Ekran ikiye bölünmüş. Solda yansımalı/kirli bir trafik anı, sağda sistemin bunu `results.json` formatına dönüştürdüğünü gösteren bir infografik.
- **Slayt Metni:** 
  - **Problem:** Kamera yansımaları, yetersiz veri, standart modellerin saha başarısızlığı.
  - **Çözüm:** Çoklu veri havuzu, sentetik augmentasyon, göreve özel (spesifik) algoritmalar.
- **Konuşma Metni:** "Kameralar gerçek dünyada laboratuvar ortamı gibi net değildir. Cam yansımaları ve düşük çözünürlük standart yapay zeka modellerini yanıltır. Biz çözümü sadece model değiştirmekte değil, veriyi manipüle ederek sistemi zorlu gerçek dünyaya hazırlamakta ve her problem için en doğru algoritmayı seçmekte bulduk."

### Slayt 3: Teknoloji Matrisimiz (Göreve Özel Modeller) 🌟 YENİ
- **Görsel Fikri:** Ortada video girişi, etrafında ikonlarla dağılan görevler ve her görevin altında kullanılan teknolojinin yazdığı şık bir harita/tablo.
- **Slayt Metni:** 
  | Tespit Kategorisi | Kullanılan Teknoloji / Model |
  |-------------------|-----------------------------|
  | **Genel Kutu Tespiti (Araç, İnsan)** | YOLO11x (Ağır Tespit Modeli) |
  | **Sürücü Davranışları** | EfficientNet-B2 (Hafif Sınıflandırıcı) |
  | **Araç Tipi Sınıflandırma** | EfficientNet-B0 (Ultra Hafif) |
  | **Araç Rengi** | K-Means Kümeleme (Matematiksel k=3) |
  | **Plaka Okuma (OCR)** | EasyOCR (Sentetik Türk Plakası Eğitimi) |
  | **Özel Nesne (Teknocan, Bilgisayar)** | YOLOv11n (Özel Eğitilmiş Nano Ajan) |
- **Konuşma Metni:** "Gördüğünüz gibi her şeyi tek bir ağır YOLO modeline yükleyip sistemin hızını düşürmedik. Hibrit bir 'Teknoloji Matrisi' kurduk. Genel tespitleri YOLO11x ile yapıp kırpılan görüntüleri spesifik ağlara yolladık. Araç rengi için yorucu yapay zeka yerine K-Means matematiksel kümelemesini kullandık. Sürücü ve araç sınıflandırmaları için çok hafif EfficientNet'leri, plaka için EasyOCR'ı ve sadece Teknocan/Bilgisayar tespitine odaklanan tamamen bizim eğittiğimiz YOLOv11 nano ajanını sisteme entegre ettik."

### Slayt 4: Veri Havuzumuz ve Kaynaklar Tablosu 🌟 YENİ
- **Görsel Fikri:** Büyük veri havuzunu gösteren net ve şık bir tablo.
- **Slayt Metni:** 
  | Veri Seti / Kaynak | Boyut / Tip | Kullanım Amacı |
  |--------------------|-------------|----------------|
  | **State Farm Distracted Driver** | ~102K Görsel | Sürücü eylemi (Telefon, Su içme vb.) ana eğitim |
  | **DMD Distraction & Drowsiness** | ~43K Etiketli Kare (Çoklu Kamera) | Farklı açılardan sürücü (Esneme, Arkaya Bakma) |
  | **DriverSVT** | 17.5 Milyon Satır (Telemetri) | Tehlikeli sürüş/slalom desteği ve zemin doğrulama |
  | **İnternet Verileri & Sentetik Üretim** | Sürekli Genişleyen Set | Cam yansımaları, Sentetik Türk Plakaları |
- **Konuşma Metni:** "Bu kusursuz mimariyi devasa bir veri havuzuyla besledik. Sadece yarışmanın sunduğu kısıtlı videolarla yetinmedik. Sürücü davranışı için 100 binin üzerinde State Farm görseli, farklı açılar için DMD çoklu kamera setlerini kullandık. İşin görsel olmayan ama fiziksel doğrulamasını yapmak için 17.5 milyon satırlık DriverSVT telemetri verisini entegre ederek anlamsal bir derinlik sağladık."

### Slayt 5: "Windshield Simulator" ve Sentetik Augmentasyon
- **Görsel Fikri:** Solda net bir State Farm sürücü fotoğrafı. Ortada "Windshield Simulator" algoritması ikonları. Sağda cam yansımaları olan sentetik görsel.
- **Slayt Metni:** 
  - Laboratuvar Değil, Gerçek Dünya Şartları
  - "Windshield (Cam Yansıması) Simulator" Algoritması
  - Görüşü Zorlaştıran Yansıma ve Kirlilik Modellemeleri
- **Konuşma Metni:** "En çok gurur duyduğumuz verisetsel yeniliğimiz 'Windshield Simulator'. Net veri setlerindeki görüntülerin üzerine algoritmik olarak ağaç gölgeleri, güneş parlamaları ve cam yansımaları ekledik. Modelimiz steril ortama göre değil, yollardaki yansımalı gerçek kameralara göre eğitildi."

### Slayt 6: FTR Uyumluluğu ve Temporal Smoothing
- **Görsel Fikri:** Huniden geçen saniyelik dataların düzenli bir `results.json`'a dönüşmesi. 
- **Slayt Metni:** 
  - FTR Doğrulama: Sıfır Şema Hatası (Exact Match)
  - 3 Saniyelik Temporal Smoothing (Zamana Bağlı Düzleştirme)
  - Titreme (Jitter) Önleyici Algoritma
- **Konuşma Metni:** "Görüntü işlemenin en büyük sorunu kareler arası tutarsızlıklardır (jitter). Buna 'Temporal Smoothing' adını verdiğimiz 3 saniyelik bir hafıza tamponu ile çözüm bulduk. Sistem anlık hataları filtreliyor, düzeltiyor ve tam istenen formatta, regex uyumlu, deterministik bir results.json üretiyor."

### Slayt 7: Saha Entegrasyonu: QoDe Native Kotlin App & 5G
- **Görsel Fikri:** Kotlin logosu ve uygulamanın şık bir mockup ekran görüntüsü.
- **Slayt Metni:** 
  - Yapay Zekayı Sahaya İndiren Native Kotlin Uygulaması
  - 5G Open Gateway Entegrasyonu (Number Verification)
  - Quality on Demand (QoD): Acil durumda ağ ivmelendirme (1080p Boosted)
- **Konuşma Metni:** "Yapay zekamızı sahadaki devriyeler ve hakemler için baştan sona Jetpack Compose ile Native bir Kotlin Android uygulamasına dönüştürdük. Bu uygulama Turkcell 5G API'lerine entegre çalışarak yoğun trafikte 'Quality on Demand' ile ağ önceliği alıyor ve AI motorumuza kesintisiz 1080p görüntü beslemeye devam ediyor."

### Slayt 8: Başarılarımız ve Performans Metrikleri
- **Görsel Fikri:** Hız (FPS) ibresi. Geometrik Zone-Logic çizimi (koltuk planı).
- **Slayt Metni:** 
  - **Docker İzolasyonu:** NVIDIA T4 CUDA destekli imaj çalışmaya hazır.
  - **Yolcu Tespiti:** Başarılı Zone-Logic uyarlaması (Arka_koltuk_1/2, ön_koltuk)
  - **Süreç Başarısı:** 10 Dakika kısıtı içinde eksiksiz Video -> JSON boru hattı (Pipeline)
- **Konuşma Metni:** "Tüm mimariyi NVIDIA T4 sunuculara uygun bir Docker konteynerine izole ettik. 10 dakikalık işlem bütçemizin çok altında çalışıyoruz. Ayrıca Geometrik Zone-Logic sayesinde, YOLO'nun sınıflandıramadığı 'hangi yolcu hangi koltukta' problemini aracın içi planı üzerinden matematiksel olarak çözmeyi başardık."

### Slayt 9: Gelecek Vizyonu ve Sonuç
- **Görsel Fikri:** Projenin sahadaki halini temsil eden bir konsept illüstrasyon (Akıllı Şehir).
- **Slayt Metni:** 
  - Özel Donanım Optimizasyonu ve Hibrit Mimari
  - Otonom araçlara (TOGG) veri akışı.
  - QoDe: Güvenli yolların yeni kodu.
- **Konuşma Metni:** "Özetlemek gerekirse QoDe; her problemi en iyi algoritmayla çözen hibrit teknoloji matrisi, 17.5 milyon satırı aşan veri havuzu ve sahadaki 5G entegreli mobil uygulaması ile gerçek akıllı şehirlerin altyapısıdır. Bizi dinlediğiniz için teşekkür ederiz."

---

## 📌 Jürinin Sorabileceği Olası Sorular (ve Hazırlık)

1. **"Neden tek büyük bir model (örneğin devasa bir YOLO) kullanmak yerine modelleri böldünüz (EfficientNet, K-Means vb.)?"**
   - **Cevap:** Donanım verimliliği ve spesifik doğruluk için. Araç rengi bulmak için milyon parametreli derin öğrenmeye gerek yoktur, K-Means bunu çok daha az işlem gücüyle milisaniyeler içinde mükemmel yapar. Sürücü detay eylemleri (sigara mı içiyor?) için ise EfficientNet, YOLO'dan çok daha yüksek hassasiyete (accuracy) sahiptir ve sistemi yavaşlatmaz.

2. **"Windshield Simulator algoritmanız tam olarak nasıl çalışıyor?"**
   - **Cevap:** Görüntü işleme teknikleri kullanarak net fotoğrafların üzerine yarı saydam maskeler, perlin noise ile kirlilik ve ışık kırılma efektleri uyguluyoruz. Model böylece kontrastı düşük, yansımalı gerçek dış kamera görüntülerine karşı bağışıklık kazanıyor.

3. **"Mobil uygulamaya odaklanmak yerine neden veri toplamaya bu kadar mesai harcadınız?"**
   - **Cevap:** Mobil uygulama ürünümüzün vitrinidir, ancak yapay zekada kural basittir: Çöp girerse, çöp çıkar (Garbage in, garbage out). Biz 17.5M telemetri verisi ve sentetik yansıma filtreleriyle kusursuz bir AI omurgası kurduğumuz için mobil uygulamamız sahada bu kadar verimli çalışabilmektedir.
