FROM nvidia/cuda:12.1.0-base-ubuntu22.04

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install required system packages (ffmpeg + OpenCV deps required)
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    ffmpeg \
    libsm6 \
    libxext6 \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create required directory structure per FTR spec
RUN mkdir -p /app/data/input /app/data/output /app/weights

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install all Python dependencies at BUILD time (no internet at runtime)
RUN pip3 install --no-cache-dir -r requirements.txt

# ── Download model weights at BUILD time ──────────────────────────────────────
# NOTE: Docker build time is NOT counted toward the 10-minute inference timeout.
# The evaluation server runs the container offline — all weights must be
# baked into the image during this build step.

# 1. YOLO11x — official Ultralytics model (public, downloaded from GitHub releases)
RUN python3 -c "\
import ssl; ssl._create_default_https_context = ssl._create_unverified_context; \
from ultralytics import YOLO; \
import shutil, pathlib; \
m = YOLO('yolo11x.pt'); \
# Move from Ultralytics cache to our weights directory \
cache = pathlib.Path.home() / '.config' / 'Ultralytics' / 'yolo11x.pt'; \
dst = pathlib.Path('/app/weights/yolo11x.pt'); \
if cache.exists() and not dst.exists(): shutil.copy(cache, dst); \
print('YOLO11x ready.')"

# 2. EasyOCR language models (tr + en) — pre-download during build
RUN python3 -c "import easyocr; easyocr.Reader(['tr', 'en'], gpu=False); print('EasyOCR models ready.')" || true

# 3. Driver classifier — copy from local data/weights/ if present.
#    IMPORTANT: Run training locally first, then place driver_classifier.pt
#    at data/weights/driver_classifier.pt before running docker build.
#    See README.md → "Model Training" section for instructions.
COPY data/weights/driver_classifier.pt /app/weights/driver_classifier.pt

# Copy source code and entry point
COPY src/ /app/src/
COPY main.py .
COPY README.md .

# Set Python path so src modules are importable
ENV PYTHONPATH=/app/src

# When the container starts, run the inference pipeline automatically
CMD ["python3", "main.py"]
