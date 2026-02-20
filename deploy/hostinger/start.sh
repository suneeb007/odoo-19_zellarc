#!/usr/bin/env bash
set -euo pipefail

# Start Hostinger deployment stack using the host-specific compose file
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

if [ ! -f ".env.hostinger" ]; then
  echo ".env.hostinger not found; copy .env.hostinger.example or create one" >&2
  exit 1
fi

docker compose -f docker-compose.hostinger.yml --env-file .env.hostinger pull
docker compose -f docker-compose.hostinger.yml --env-file .env.hostinger up -d --remove-orphans
