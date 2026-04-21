#!/bin/bash
set -e

cd /opt/omaha-cloud

# Pull latest code
git pull origin main

# Install backend dependencies
cd backend
source ../venv/bin/activate
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Restart service
sudo systemctl restart omaha-cloud

echo "Deployment completed successfully"
