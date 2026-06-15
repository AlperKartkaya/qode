#!/usr/bin/env bash
# download_weights.sh — Model ağırlıklarını yerel geliştirme için indir
#
# Kullanım:
#   chmod +x download_weights.sh
#   ./download_weights.sh
#
# Gereksinim: pip install huggingface_hub
# HF token (private repo için):  export HF_TOKEN="hf_xxxx"
#   veya:  huggingface-cli login

set -euo pipefail

HF_REPO="QoDe-5G/qode-models"
WEIGHTS_DIR="data/weights"
mkdir -p "$WEIGHTS_DIR"

echo "============================================="
echo " QoDe — Model Ağırlıkları İndirici"
echo " HF Repo: https://huggingface.co/$HF_REPO"
echo "============================================="

# ── 1. YOLO11x ────────────────────────────────────────────────────────────────
if [ -f "yolo11x.pt" ]; then
    echo "[✓] yolo11x.pt zaten mevcut, atlanıyor."
else
    echo "[↓] yolo11x.pt indiriliyor (Ultralytics, ~113 MB)..."
    python3 -c "
import ssl; ssl._create_default_https_context = ssl._create_unverified_context
from ultralytics import YOLO
import shutil, pathlib
YOLO('yolo11x.pt')
src = pathlib.Path.home() / '.config' / 'Ultralytics' / 'yolo11x.pt'
dst = pathlib.Path('yolo11x.pt')
if src.exists() and not dst.exists():
    shutil.copy(src, dst)
print('yolo11x.pt hazır:', dst.resolve())
"
fi

# ── 2. driver_classifier.pt ───────────────────────────────────────────────────
if [ -f "$WEIGHTS_DIR/driver_classifier.pt" ]; then
    echo "[✓] driver_classifier.pt zaten mevcut, atlanıyor."
else
    echo "[↓] driver_classifier.pt indiriliyor (HF Hub: $HF_REPO)..."
    python3 -c "
from huggingface_hub import hf_hub_download
import os
token = os.environ.get('HF_TOKEN')
path = hf_hub_download(
    repo_id='$HF_REPO',
    filename='driver_classifier.pt',
    local_dir='$WEIGHTS_DIR/',
    token=token,
)
print('driver_classifier.pt hazır:', path)
" && echo "[✓] driver_classifier.pt indirildi." || echo "[!] İndirme başarısız — önce modeli eğitin veya HF_TOKEN ayarlayın."
fi

# ── 3. vehicle_type_classifier.pt (opsiyonel) ─────────────────────────────────
if [ -f "$WEIGHTS_DIR/vehicle_type_classifier.pt" ]; then
    echo "[✓] vehicle_type_classifier.pt zaten mevcut, atlanıyor."
else
    echo "[↓] vehicle_type_classifier.pt indiriliyor (HF Hub: $HF_REPO)..."
    python3 -c "
from huggingface_hub import hf_hub_download
import os
token = os.environ.get('HF_TOKEN')
path = hf_hub_download(
    repo_id='$HF_REPO',
    filename='vehicle_type_classifier.pt',
    local_dir='$WEIGHTS_DIR/',
    token=token,
)
print('vehicle_type_classifier.pt hazır:', path)
" && echo "[✓] vehicle_type_classifier.pt indirildi." || echo "[i] vehicle_type_classifier.pt henüz yok — araç tipi eğitimi yapılmamış, COCO fallback kullanılacak."
fi

echo ""
echo "=== Durum ==="
for f in yolo11x.pt "$WEIGHTS_DIR/driver_classifier.pt" "$WEIGHTS_DIR/vehicle_type_classifier.pt"; do
    if [ -f "$f" ]; then
        size=$(du -sh "$f" | cut -f1)
        echo "  [✓] $f  ($size)"
    else
        echo "  [✗] $f  (eksik)"
    fi
done
echo ""
echo "Hazır! 'python main.py' ile pipeline'ı test edebilirsiniz."
