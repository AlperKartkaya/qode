FROM nvidia/cuda:12.1.0-base-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive

# System packages — OpenCV ve ffmpeg için gerekli
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    ffmpeg \
    libsm6 \
    libxext6 \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
RUN mkdir -p /app/data/input /app/data/output /app/weights

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# ── Model ağırlıkları BUILD aşamasında indirilir ──────────────────────────────
# Docker build süresi 10 dakika timeout'una dahil DEĞİLDİR.
# Tüm ağırlıklar burada hazırlanır → konteyner tamamen offline çalışır.

# 1. YOLO11x — Ultralytics public model
RUN python3 -c "\
import ssl; ssl._create_default_https_context = ssl._create_unverified_context; \
from ultralytics import YOLO; \
import shutil, pathlib; \
YOLO('yolo11x.pt'); \
cache = pathlib.Path.home() / '.config' / 'Ultralytics' / 'yolo11x.pt'; \
dst = pathlib.Path('/app/weights/yolo11x.pt'); \
if cache.exists(): shutil.copy(cache, dst); \
print('[OK] yolo11x.pt ready at', dst)"

# 2. EasyOCR dil modelleri (tr + en) — build aşamasında önbellek
RUN python3 -c "import easyocr; easyocr.Reader(['tr', 'en'], gpu=False); print('[OK] EasyOCR models ready.')" || true

# 3. Eğitilmiş ağırlıklar — Hugging Face Hub: QoDe-5G/qode-models
#    Build argümanı: docker build --build-arg HF_TOKEN=hf_xxxx .
ARG HF_TOKEN=""

RUN python3 -c "\
import os; \
from huggingface_hub import hf_hub_download; \
token = os.environ.get('HF_TOKEN', '$HF_TOKEN') or None; \
repo = 'QoDe-5G/qode-models'; \
for fname in ['driver_classifier.pt', 'vehicle_type_classifier.pt']: \
    try: \
        p = hf_hub_download(repo_id=repo, filename=fname, local_dir='/app/weights/', token=token); \
        print(f'[OK] {fname} ready at {p}'); \
    except Exception as e: \
        print(f'[WARN] {fname} could not be downloaded: {e}'); \
" || true

# Kaynak kod
COPY src/ /app/src/
COPY main.py .
COPY README.md .

ENV PYTHONPATH=/app/src

CMD ["python3", "main.py"]
