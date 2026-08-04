#!/bin/bash

# Tüm modelleri sırayla eğiten bash betiği
echo "🚀 Tüm modellerin eğitimi başlıyor..."
ERROR_LOG="data/weights/failed_trainings.log"
mkdir -p data/weights
echo "" > $ERROR_LOG

# 1. Smoker Classifier (Yüz Sigara Tespiti)
echo "=================================================="
echo "1. Sürücü Sigara Tespiti (Smoker Classifier) Eğitiliyor..."
echo "=================================================="
python3 scripts/train_smoker_classifier.py
if [ $? -ne 0 ]; then
    echo "❌ Smoker modeli eğitiminde hata oluştu. Sonraki modele geçiliyor..."
    echo "[HATA] Smoker Classifier (scripts/train_smoker_classifier.py)" >> $ERROR_LOG
else
    echo "✅ Smoker modeli başarıyla eğitildi!"
fi

# 2. Driver Behaviors (Ana Sürücü Davranışları - Sigara hariç)
echo "=================================================="
echo "2. Sürücü Davranışları (Driver Behaviors) Eğitiliyor..."
echo "=================================================="
python3 src/smart_road_safety/training/train_driver_model.py
if [ $? -ne 0 ]; then
    echo "❌ Sürücü davranışları eğitiminde hata oluştu. Sonraki modele geçiliyor..."
    echo "[HATA] Driver Behaviors (src/smart_road_safety/training/train_driver_model.py)" >> $ERROR_LOG
else
    echo "✅ Driver Behaviors başarıyla eğitildi!"
fi

# Not: YOLO modelleri (Araç, Teknocan) vs. çok daha uzun sürer ve genelde dışarıda 
# (Google Colab vb.) eğitilip ağırlıkları buraya atılır. Bu yüzden onları bu script'e 
# dahil etmedik, ancak mevcut kodlar src/smart_road_safety/training içinde mevcuttur.

echo "=================================================="
if [ -s "$ERROR_LOG" ] && [ "$(cat $ERROR_LOG | wc -w)" -gt 0 ]; then
    echo "⚠️ Eğitim süreci tamamlandı ancak bazı modeller BAŞARISIZ oldu:"
    cat $ERROR_LOG
    echo "=================================================="
    exit 1
else
    echo "✅ Bütün eğitimler kusursuz bir şekilde başarıyla tamamlandı!"
    echo "Model ağırlıkları data/weights/ klasörüne kaydedildi."
    echo "=================================================="
    rm -f $ERROR_LOG
    exit 0
fi
