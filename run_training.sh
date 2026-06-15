#!/usr/bin/env bash
# run_training.sh — Tam 22k görsel ile sürücü modeli eğitimi başlatıcı
#
# Kullanım:
#   chmod +x run_training.sh
#   ./run_training.sh

set -euo pipefail

# Python ortamını aktif et (varsa)
if [ -d ".venv" ]; then
    echo "[Setup] Sanal ortam aktif ediliyor (.venv)..."
    source .venv/bin/activate
fi

echo "=================================================================="
echo " QoDe Sürücü Davranışı Eğitimi Başlıyor"
echo " Donanım: Apple Silicon (M4 Pro / MPS) veya CUDA"
echo " Model:   EfficientNet-B2"
echo " Tahmini Süre: ~2-3 Saat"
echo "=================================================================="
echo ""

echo "Adım 1: Veri seti hazırlanıyor (State Farm ~22k görsel)"
echo "Bu işlem cam yansıma (windshield) augmentasyonlarını uygulayacaktır."
echo "------------------------------------------------------------------"
PYTHONPATH=src python3 -m smart_road_safety.training.preprocess_state_farm --max-samples 0
echo ""

echo "Adım 2: Model eğitimi başlıyor"
echo "İlerleme çubuğu (progress bar) her epoch için aktif edildi."
echo "------------------------------------------------------------------"
# M4 Pro için iyi bir batch size (32 veya 64, bellek durumuna göre)
PYTHONPATH=src python3 -m smart_road_safety.training.train_classifier \
    --epochs 20 \
    --batch-size 32 \
    --lr 0.0003 \
    --freeze-epochs 5

echo ""
echo "=================================================================="
echo " Eğitim Tamamlandı! 🎉"
echo " Ağırlıklar kaydedildi: data/weights/driver_classifier.pt"
echo " "
echo " Hugging Face Hub'a yüklemek için şu komutu çalıştırın:"
echo "   python upload_weights.py"
echo "=================================================================="
