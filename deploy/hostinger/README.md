# Hostinger VPS deploy (git + docker-compose)

Copy `deploy/hostinger` to your VPS (or git clone this repo on the VPS) and then run `./start.sh`.

Quick steps on the VPS:

1. Install Docker Engine and Docker Compose plugin.
2. Copy this folder to `~/odoo-deploy` (or clone repository and keep files under that path).
3. Edit `.env.hostinger` with production credentials (do NOT commit secrets).
4. Run:

```bash
cd ~/odoo-deploy/deploy/hostinger
./start.sh
```

Recommended nginx reverse-proxy (on the VPS) pointing to `127.0.0.1:${HOST_ODOO_PORT}` and obtain TLS with Certbot.

GitHub Actions:

- Use `deploy/.github/workflows/deploy-odoo.yml` (created) which SSHes into the VPS and runs the compose update.
- Set repository secrets `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`, and `VPS_SSH_PORT` (use `deploy/hostinger/set_github_secrets.sh` to set them via `gh`).
