#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

if [ ! -f ".env.hostinger" ]; then
  echo ".env.hostinger not found. Copy .env.hostinger.example to .env.hostinger and set real values." >&2
  exit 1
fi

mkdir -p ./data/postgres ./data/odoo

docker compose -f docker-compose.hostinger.yml --env-file .env.hostinger pull
docker compose -f docker-compose.hostinger.yml --env-file .env.hostinger up -d --remove-orphans
docker compose -f docker-compose.hostinger.yml --env-file .env.hostinger ps