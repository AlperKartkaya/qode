#!/bin/bash

# Tüm modelleri sırayla eğiten bash betiği
echo "🚀 Tüm modellerin eğitimi başlıyor..."

# 1. Smoker Classifier (Yüz Sigara Tespiti)
echo "=================================================="
echo "1. Sürücü Sigara Tespiti (Smoker Classifier) Eğitiliyor..."
echo "=================================================="
python3 scripts/train_smoker_classifier.py
if [ $? -ne 0 ]; then
    echo "❌ Smoker modeli eğitiminde hata oluştu. Çıkılıyor."
    exit 1
fi

# 2. Driver Behaviors (Ana Sürücü Davranışları - Sigara hariç)
echo "=================================================="
echo "2. Sürücü Davranışları (Driver Behaviors) Eğitiliyor..."
echo "=================================================="
python3 src/smart_road_safety/training/train_driver_model.py
if [ $? -ne 0 ]; then
    echo "❌ Sürücü davranışları eğitiminde hata oluştu. Çıkılıyor."
    exit 1
fi

# Not: YOLO modelleri (Araç, Teknocan) vs. çok daha uzun sürer ve genelde dışarıda 
# (Google Colab vb.) eğitilip ağırlıkları buraya atılır. Bu yüzden onları bu script'e 
# dahil etmedik, ancak mevcut kodlar src/smart_road_safety/training içinde mevcuttur.

echo "=================================================="
echo "✅ Bütün eğitimler başarıyla tamamlandı!"
echo "Model ağırlıkları data/weights/ klasörüne kaydedildi."
echo "=================================================="
