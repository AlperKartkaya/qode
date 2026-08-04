# P2 gerçek FTR evaluator kanıtı

Tarih: **2026-08-04**

## Uygulanan sözleşme

- Prediction ve GT, metric hesaplanmadan önce aynı `competition/ftr.py`
  validator'ından geçirilir.
- Vehicle type/color/normalize plate exact-match, plate regex ve confidence range
  alanları ayrı raporlanır.
- Event'ler category+label içinde maksimum cardinality, minimum mutlak timestamp
  hatalı bire-bir eşlemeyle değerlendirilir. Bir prediction iki GT event'ini
  kapatamaz; repeated object/passenger timestamp'leri set'e indirgenmez.
- Per-label/per-family TP/FP/FN, precision/recall/F1, micro/macro ve timestamp MAE
  üretilir.
- 0.5, 1.0, 2.0 ve 3.0 saniye sensitivity raporu her koşuda üretilir.
- Tolerance, resmi yarışma kuralı değil development calibration parametresi olarak
  hem JSON hem Markdown çıktıda işaretlenir.

## Manuel smoke

```text
prediction = data/final_stage/faz2/ground_truth.json
ground_truth = data/final_stage/faz2/ground_truth.json
timestamp_tolerance = 1.0
vehicle exact-match rate = 1.0
TP=34, FP=0, FN=0
micro precision=1.0, recall=1.0, F1=1.0
macro F1=1.0
timestamp MAE=0.0
sensitivity F1 (0.5/1.0/2.0/3.0)=1.0/1.0/1.0/1.0
```

Bu sonuç model başarısı değildir; evaluator'ın identity/self-consistency smoke'udur.
Gerçek düşük/yüksek/kayıt-video prediction dosyaları P3/P4 tarafından üretildikten
sonra aynı CLI ile ayrı, kalıcı metric JSON'ları oluşturulacaktır.

## Test kapsamı

Güncel repo doğrulaması: **71/71 Python testi**, **13/13 backend testi** ve
`compileall` başarılıdır. Backend suite'inde mevcut Starlette/httpx deprecation
uyarısı devam etmektedir.

- GT vs kendisi
- one-to-one repeated passenger event eşleme
- cardinality-first/minimum-error assignment
- tolerance sınırı
- yanlış label için FP+FN
- schema fail'de çıktı üretilmemesi
- boş event/category sıfıra bölme güvenliği
- event sırası değişmezliği
- Markdown vehicle/event/sensitivity/FP/FN tabloları

## Komut

```bash
PYTHONPATH=src python3 -m smart_road_safety.cli evaluate-ftr \
  --prediction out/faz2/results.json \
  --ground-truth data/final_stage/faz2/ground_truth.json \
  --timestamp-tolerance 1.0 \
  --output out/final_stage/faz2_metrics.json \
  --markdown-output out/final_stage/faz2_metrics.md
```
