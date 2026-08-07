FROM --platform=linux/amd64 nvidia/cuda@sha256:c348da4a5ab1edae77c22efa89d6915eab7f4cf26ee2c3ca60d94e21c32d4062

ARG QODE_VERSION=2026.08-p4
ARG VCS_REF=unknown
ARG BUILD_DATE=unknown
LABEL org.opencontainers.image.title="QoDe Final Inference" \
      org.opencontainers.image.version="${QODE_VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      qode.ftr.schema-version="1" \
      qode.runtime.asset-manifest="config/runtime_assets.json"

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONPATH=/app/src \
    QODE_RUNTIME_MODE=final \
    QODE_SAMPLE_FPS=4 \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    YOLO_OFFLINE=1 \
    EASYOCR_MODULE_PATH=/app/easyocr_weights

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip ffmpeg libsm6 libxext6 libgl1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
RUN mkdir -p /app/data/input /app/data/output /app/weights /app/easyocr_weights

COPY requirements-runtime.txt /app/requirements-runtime.txt
RUN pip3 install --no-cache-dir -r /app/requirements-runtime.txt

# Pre-download EasyOCR weights to the image so they work in offline final mode
RUN python3 -c "import easyocr; import os; easyocr.Reader(['tr', 'en'])"


COPY src/ /app/src/
COPY config/runtime_assets.json /app/config/runtime_assets.json
COPY config/runtime_environment.json /app/config/runtime_environment.json
COPY data/weights/ /app/weights/
COPY main.py /app/main.py

# Missing, unfrozen, checksum-invalid, or class-incompatible production assets
# deliberately make the final image build fail.
RUN python3 -m smart_road_safety.cli check-runtime-assets \
    --manifest /app/config/runtime_assets.json --asset-root /app/weights \
    --mode final --inspect-classes

HEALTHCHECK --interval=30s --timeout=20s --retries=1 \
  CMD python3 -m smart_road_safety.cli check-runtime-readiness \
      --manifest /app/config/runtime_assets.json --asset-root /app/weights \
      --output-dir /app/data/output || exit 1

CMD ["python3", "/app/main.py", "--mode", "final", "--input-dir", "/app/data/input", "--output-dir", "/app/data/output", "--asset-root", "/app/weights", "--asset-manifest", "/app/config/runtime_assets.json"]
