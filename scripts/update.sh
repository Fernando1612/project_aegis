#!/bin/bash

# Project AEGIS - Update Script
# Pulls latest code, rebuilds, and restarts containers.

set -e

echo ">>> Updating Project AEGIS..."

# 1. Pull latest code
echo ">>> Pulling latest changes from git..."
git pull

# 2. Rebuild and Restart
echo ">>> Rebuilding and restarting containers..."
docker compose down
docker compose up -d --build

# 3. Prune unused images
echo ">>> Cleaning up old images..."
docker image prune -f

echo ">>> Update Complete! Check logs with: docker compose logs -f"
