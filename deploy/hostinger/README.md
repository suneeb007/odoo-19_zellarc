# Deploying Odoo on Hostinger KVM (no impact to other apps)

Summary
- This directory contains a ready `docker-compose.hostinger.yml`, a `.env.hostinger` with DB credentials and host port choices, and a `start.sh` helper.
- Compose uses separate container names, its own Docker network and non-default host ports (by default `18069` for Odoo and `15432` for Postgres) so it won't interfere with existing services.

Prepare on your local machine
1. Optionally review and edit `.env.hostinger` to change `HOST_ODOO_PORT` and `HOST_PG_PORT` if those host ports conflict with existing services.

Copy to the VPS (example):
```bash
# from your local repo root
scp -r deploy/hostinger/ user@your-vps-ip:~/odoo-deploy
ssh user@your-vps-ip
```

On the VPS (Debian/Ubuntu example)
```bash
# update and install docker + compose plugin
sudo apt update
sudo apt install -y docker.io docker-compose-plugin
sudo systemctl enable --now docker

# go to deployment dir created via scp
cd ~/odoo-deploy

# (optional) login to Docker Hub so private images can be pulled
docker login

# start the stack
chmod +x start.sh
./start.sh

# check status
docker compose -f docker-compose.hostinger.yml ps
docker compose -f docker-compose.hostinger.yml logs -f odoo
```

Firewall
- If the VPS uses `ufw` open the chosen Odoo port (example):
```bash
sudo ufw allow 18069/tcp
```

Notes & troubleshooting
- If you already run Postgres on the host and prefer to reuse it, remove the `db` service from the compose file and set `DB_HOST` to the host IP (and ensure port/credentials match).
- The `.env.hostinger` file contains credentials; keep it private on the VPS.
