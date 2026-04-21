# Deployment Guide

## Scripts

| File | Purpose |
|------|---------|
| `setup_server.sh` | Full server init: installs deps, sets up DB, starts service |
| `setup_nginx.sh` | Configures Nginx reverse proxy and SSL (Let's Encrypt) |
| `setup_cron.sh` | Sets up cron jobs for data sync and DB backup |
| `deploy.sh` | Incremental code deploy (pull + restart) |
| `backup.sh` | Manual database backup |
| `sync_wrapper.sh` | Wrapper for Tushare data sync |
| `nginx.conf` | Nginx site configuration |
| `omaha-cloud.service` | systemd service unit |
| `crontab.txt` | Cron schedule reference |

## Initial Setup

```bash
# Upload code to server
scp -r /path/to/omaha_ontocenter root@<server-ip>:/tmp/

# SSH in and run setup
ssh root@<server-ip>
cd /tmp/omaha_ontocenter/deployment
bash setup_server.sh
bash setup_nginx.sh
bash setup_cron.sh
```

## Common Operations

```bash
# Deploy a code update
cd /opt/omaha-cloud && bash deployment/deploy.sh

# Service management
systemctl status omaha-cloud
systemctl restart omaha-cloud
journalctl -u omaha-cloud -f

# Health check
curl http://localhost:8000/health
```

## Environment

Production config at `/opt/omaha-cloud/backend/.env`:
- `DATABASE_URL` — PostgreSQL connection string
- `SECRET_KEY` — JWT signing key
- `TUSHARE_TOKEN` — Tushare Pro API token
