#!/bin/bash
set -e

# Deploy backend to a remote VPS via SSH and Docker
# Usage: ./deploy-backend.sh vps2

TARGET_HOST="${1:-vps2}"
TARGET_PATH="/home/hitesh/mic-check-lookup"

if [ -z "$TARGET_HOST" ]; then
    echo "Usage: $0 <hostname>"
    echo "Example: $0 vps2"
    exit 1
fi

echo "🚀 Deploying backend to $TARGET_HOST:$TARGET_PATH"

# 1. Sync server/ to vps
echo "📦 Syncing server/ directory..."
rsync -avz --delete \
    server/ \
    "$TARGET_HOST:$TARGET_PATH/server/" \
    --exclude='.env.local' \
    --exclude='__pycache__' \
    --exclude='.pytest_cache' \
    --exclude='.venv'

# Also sync Dockerfile and pyproject.toml
rsync -avz \
    server/Dockerfile \
    server/pyproject.toml \
    "$TARGET_HOST:$TARGET_PATH/"

# 2. Rebuild and restart
echo "🔨 Building Docker image..."
ssh "$TARGET_HOST" "cd $TARGET_PATH && docker build -t mic-check-lookup ."

echo "♻️  Stopping old container..."
ssh "$TARGET_HOST" "docker stop mic-check-lookup || true"

echo "♻️  Removing old container..."
ssh "$TARGET_HOST" "docker rm mic-check-lookup || true"

echo "🚀 Starting new container..."
ssh "$TARGET_HOST" "docker run -d --name mic-check-lookup -p 127.0.0.1:7777:8080 --restart unless-stopped mic-check-lookup"

echo "✅ Deployment complete!"
echo "Check logs: ssh $TARGET_HOST 'docker logs -f mic-check-lookup'"
