#!/bin/bash
set -euo pipefail

PROJECT_DIR="/home/ubuntu/JobFinderAgent"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"

echo "=== Pulling latest code ==="
cd "$PROJECT_DIR"
git pull origin main

echo "=== Backend setup ==="
cd "$BACKEND_DIR"
python3 -m venv venv 2>/dev/null || true
source venv/bin/activate
pip install -r requirements.txt

echo "=== Frontend build ==="
cd "$FRONTEND_DIR"
npm ci
npm run build

echo "=== Install systemd service ==="
sudo cp "$PROJECT_DIR/jobfinder.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable jobfinder
sudo systemctl restart jobfinder

echo "=== Done ==="
sudo systemctl status jobfinder --no-pager
