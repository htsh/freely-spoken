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

# 1. Sync app code directly to where the Dockerfile expects it
echo "📦 Syncing app/ directory..."
rsync -avz --delete \
    server/app/ \
    "$TARGET_HOST:$TARGET_PATH/app/" \
    --exclude='__pycache__' \
    --exclude='*.pyc'

# Sync Dockerfile and pyproject.toml
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
ssh "$TARGET_HOST" "docker run -d --name mic-check-lookup -p 127.0.0.1:7777:8080 --restart unless-stopped --env-file $TARGET_PATH/.env mic-check-lookup"

echo "✅ Deployment complete!"
echo "Check logs: ssh $TARGET_HOST 'docker logs -f mic-check-lookup'"
