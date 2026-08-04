#!/usr/bin/env bash
set -euo pipefail

QODE_VERSION="${QODE_VERSION:-2026.08-p4}"
IMAGE="teknofest-2026/qode-final:${QODE_VERSION}"

echo "Deploying QoDe to VM..."

# 1. Ensure directories exist (using relative paths for the host, not root /app)
mkdir -p data/input data/output data/weights

# 2. Build Docker Image
echo "Building Docker image: $IMAGE"
docker build --platform linux/amd64 --build-arg "QODE_VERSION=$QODE_VERSION" \
  --build-arg "VCS_REF=$(git rev-parse HEAD)" \
  --build-arg "BUILD_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  -t "$IMAGE" .

# 3. Print SHA256 (Required for Teknofest Final submission)
FINGERPRINT=$(docker inspect --format='{{.Id}}' "$IMAGE")
echo "----------------------------------------"
echo "DOCKER IMAGE SHA256 FINGERPRINT:"
echo "$FINGERPRINT"
echo "----------------------------------------"
echo "Please save this SHA256 fingerprint for submission before Aug 7, 21:00."

# 4. Start Backend API
echo "Starting Backend API on port 8000..."
cd backend
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install -r requirements.txt
# Run via uvicorn in background
nohup uvicorn app:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &

echo "Deployment finished! Backend is running at http://localhost:8000"
