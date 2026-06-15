FROM nvidia/cuda:12.1.0-base-ubuntu22.04

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install required system packages
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

# Install all Python dependencies at build time (no internet at runtime)
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy model weights (tracked in git — required for offline evaluation)
# driver_classifier.pt is the MobileNetV3/EfficientNet driver behavior model
COPY data/weights/ /app/weights/
# Copy the YOLO11x base model if present
COPY yolo11x.pt /app/weights/yolo11x.pt

# Copy source code
COPY src/ /app/src/
COPY main.py .
COPY README.md .

# Set Python path so src modules are importable
ENV PYTHONPATH=/app/src

# When the container starts, run the inference pipeline automatically
CMD ["python3", "main.py"]
