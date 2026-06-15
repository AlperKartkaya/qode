#!/bin/bash

# Log klasörünü oluştur
mkdir -p logs

echo "========================================="
echo "   QoDe-5G Yapay Zeka Eğitim Süreci      "
echo "========================================="
echo "Eğitim başladı. Bilgisayar uyumayacak şekilde ayarlandı (caffeinate)."
echo "Bu işlem saatler sürebilir. Lütfen terminali KAPATMAYIN."

# Sürücü Davranışları Modeli
echo ""
echo "[1/2] Sürücü Davranışları (Driver Behavior) Modeli Eğitiliyor..."
echo "Başlangıç: $(date)" | tee logs/training_summary.txt
echo "Driver Model Start: $(date)" >> logs/driver_training.log

# Caffeinate ile komutu çalıştır ve çıktıları log dosyasına da yaz
caffeinate -i .venv/bin/python src/smart_road_safety/training/train_classifier.py 2>&1 | tee -a logs/driver_training.log

echo "Bitiş: $(date)" | tee -a logs/training_summary.txt
echo "[1/2] Sürücü Modeli Eğitimi TAMAMLANDI." | tee -a logs/training_summary.txt

# Araç Tipleri Modeli
echo ""
echo "[2/2] Araç Tipleri (Vehicle Type) Modeli Eğitiliyor..."
echo "Başlangıç: $(date)" | tee -a logs/training_summary.txt
echo "Vehicle Model Start: $(date)" >> logs/vehicle_training.log

caffeinate -i .venv/bin/python src/smart_road_safety/training/train_vehicle_type_classifier.py 2>&1 | tee -a logs/vehicle_training.log

echo "Bitiş: $(date)" | tee -a logs/training_summary.txt
echo "[2/2] Araç Modeli Eğitimi TAMAMLANDI." | tee -a logs/training_summary.txt

echo ""
echo "========================================="
echo "TÜM EĞİTİMLER BAŞARIYLA BİTTİ!"
echo "Detaylı logları 'logs/' klasöründe bulabilirsiniz."
echo "========================================="
