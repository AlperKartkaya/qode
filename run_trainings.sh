#!/bin/bash
# run_trainings.sh — Full QoDe model retraining pipeline
#
# Usage:
#   chmod +x run_trainings.sh
#   caffeinate -i ./run_trainings.sh
#
# Models trained:
#   1. Driver Behaviour Classifier (EfficientNet-B2 + WindshieldTransform augmentation)
#   2. Vehicle Type Classifier     (EfficientNet-B0)
#
# Estimated time on M4 Pro: ~2-4 hours total

set -euo pipefail

# Log klasörünü oluştur
mkdir -p logs

# Python ortamını aktif et (varsa)
if [ -d ".venv" ]; then
    echo "[Setup] Sanal ortam aktif ediliyor (.venv)..."
    source .venv/bin/activate
fi

echo "========================================="
echo "   QoDe Yapay Zeka Eğitim Süreci"
echo "   Donanım: Apple Silicon (M4 Pro / MPS)"
echo "========================================="
echo ""
echo "Yenilikler:"
echo "  • WindshieldTransform augmentasyonu (dış kamera simülasyonu)"
echo "  • EfficientNet-B2 sürücü modeli"
echo "  • EfficientNet-B0 araç tipi modeli"
echo ""
echo "Eğitim başladı. Terminali KAPATMAYIN!"
echo "Loglari: logs/ klasöründe bulabilirsiniz."
echo ""

# ── Adım 1: Veri setlerini hazırla ───────────────────────────────────────────
echo "================================================================"
echo " [0/2] Veri setleri hazırlanıyor..."
echo "================================================================"
echo "Adım 0 Başlangıç: $(date)" | tee logs/training_summary.txt

PYTHONPATH=src python3 -m smart_road_safety.training.build_datasets 2>&1 | tee logs/build_datasets.log

echo "Adım 0 Bitiş: $(date)" | tee -a logs/training_summary.txt
echo ""

# ── Adım 2: Sürücü Davranışları Modeli ───────────────────────────────────────
echo "================================================================"
echo " [1/2] Sürücü Davranışları Modeli Eğitiliyor..."
echo "        Model: EfficientNet-B2"
echo "        Augmentation: WindshieldTransform (%50 olasılık)"
echo "        Epochs: 25 (5 frozen + 20 fine-tune)"
echo "================================================================"
echo "Driver Model Başlangıç: $(date)" | tee -a logs/training_summary.txt
echo "Driver Model Start: $(date)" > logs/driver_training.log

PYTHONPATH=src python3 -m smart_road_safety.training.train_classifier \
    --epochs 25 \
    --batch-size 32 \
    --lr 0.0003 \
    --freeze-epochs 5 \
    2>&1 | tee -a logs/driver_training.log

echo "Driver Model Bitiş: $(date)" | tee -a logs/training_summary.txt
echo "[1/2] Sürücü Modeli Eğitimi TAMAMLANDI." | tee -a logs/training_summary.txt
echo ""

# ── Adım 3: Araç Tipleri Modeli ──────────────────────────────────────────────
echo "================================================================"
echo " [2/2] Araç Tipleri Modeli Eğitiliyor..."
echo "        Model: EfficientNet-B0"
echo "        Epochs: 20 (5 frozen + 15 fine-tune)"
echo "================================================================"
echo "Vehicle Model Başlangıç: $(date)" | tee -a logs/training_summary.txt
echo "Vehicle Model Start: $(date)" > logs/vehicle_training.log

PYTHONPATH=src python3 -m smart_road_safety.training.train_vehicle_type_classifier \
    --epochs 20 \
    --batch-size 32 \
    --lr 0.0003 \
    --freeze-epochs 5 \
    2>&1 | tee -a logs/vehicle_training.log

echo "Vehicle Model Bitiş: $(date)" | tee -a logs/training_summary.txt
echo "[2/2] Araç Modeli Eğitimi TAMAMLANDI." | tee -a logs/training_summary.txt
echo ""

# ── Özet ─────────────────────────────────────────────────────────────────────
echo "========================================="
echo "  TÜM EĞİTİMLER BAŞARIYLA BİTTİ! 🎉"
echo ""
echo "  Ağırlıklar:"
echo "    data/weights/driver_classifier.pt"
echo "    data/weights/vehicle_type_classifier.pt"
echo ""
echo "  Detaylı loglar: logs/ klasöründe"
echo ""
echo "  Test etmek için:"
echo "    python analyze_videos.py"
echo "========================================="
