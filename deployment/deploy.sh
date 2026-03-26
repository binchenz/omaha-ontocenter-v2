#!/bin/bash
set -e

cd /var/www/omaha_ontocenter

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
