FROM nvidia/cuda:12.1.0-base-ubuntu22.04

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

# The FTR PDF states inputs will be at /app/data/input and outputs at /app/data/output
RUN mkdir -p /app/data/input /app/data/output

# Set the Python path so src modules can be imported naturally
ENV PYTHONPATH=/app/src

# Run main.py which conforms to the FTR processing structure
CMD ["python3", "main.py"]
