#!/usr/bin/env bash
# download_weights.sh — Download all required model weights locally
#
# Usage (before docker build or local dev):
#   chmod +x download_weights.sh
#   ./download_weights.sh
#
# What this downloads:
#   • yolo11x.pt    — Ultralytics YOLO11x (public, 113 MB)
#   • driver_classifier.pt — QoDe trained driver behaviour model
#     (Upload your trained weights to Hugging Face Hub and update the URL below)

set -euo pipefail

WEIGHTS_DIR="data/weights"
mkdir -p "$WEIGHTS_DIR"

echo "[weights] Downloading YOLO11x..."
python3 -c "
import ssl; ssl._create_default_https_context = ssl._create_unverified_context
from ultralytics import YOLO
m = YOLO('yolo11x.pt')
import shutil, pathlib
# Ultralytics caches to ~/.config/Ultralytics/
src = pathlib.Path.home() / '.config' / 'Ultralytics' / 'yolo11x.pt'
dst = pathlib.Path('yolo11x.pt')
if src.exists() and not dst.exists():
    shutil.copy(src, dst)
print('yolo11x.pt ready at:', dst.resolve())
"

echo "[weights] YOLO11x download complete."

# ── driver_classifier.pt ───────────────────────────────────────────────────────
# Option A: If you have uploaded to Hugging Face Hub, set HF_REPO and uncomment:
# HF_REPO="your-username/qode-driver-classifier"
# python3 -c "
# from huggingface_hub import hf_hub_download
# path = hf_hub_download(repo_id='$HF_REPO', filename='driver_classifier.pt', local_dir='data/weights/')
# print('driver_classifier.pt ready at:', path)
# "

# Option B: If running locally, train with:
#   python -m smart_road_safety.training.preprocess_state_farm --max-samples 0
#   python -m smart_road_safety.training.train_classifier --epochs 20

echo ""
echo "[weights] All weights ready."
echo "  yolo11x.pt             → $(du -sh yolo11x.pt 2>/dev/null | cut -f1 || echo 'missing')"
echo "  data/weights/driver_classifier.pt → $(du -sh data/weights/driver_classifier.pt 2>/dev/null | cut -f1 || echo 'missing — train first')"
