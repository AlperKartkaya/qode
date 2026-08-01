#!/usr/bin/env bash
set -e

echo "Deploying QoDe to VM..."

# 1. Ensure directories exist
mkdir -p /app/data/input /app/data/output /app/weights

# 2. Build Docker Image
echo "Building Docker image: teknofest-2026/qode:latest"
docker build -t teknofest-2026/qode:latest .

# 3. Print SHA256 (Required for Teknofest Final submission)
FINGERPRINT=$(docker inspect --format='{{.Id}}' teknofest-2026/qode:latest)
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
