#!/usr/bin/env bash
set -euo pipefail

# Start the Odoo stack for Hostinger (run on the VPS inside the deployment dir)
docker compose -f docker-compose.hostinger.yml up -d

echo "Started containers. Run 'docker compose ps' to check status."
