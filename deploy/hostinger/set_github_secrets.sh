#!/usr/bin/env bash
set -euo pipefail

if ! command -v gh >/dev/null 2>&1; then
  echo "Please install GitHub CLI (gh) and authenticate before running this script." >&2
  exit 1
fi

read -rp "GitHub repo (owner/repo): " REPO
read -rp "VPS host (IP or hostname): " VPS_HOST
read -rp "VPS ssh user: " VPS_USER
read -rp "SSH port (default 22): " VPS_SSH_PORT
if [ -z "$VPS_SSH_PORT" ]; then VPS_SSH_PORT=22; fi

echo "Enter SSH private key (PEM) followed by EOF on an empty line:" >&2
SSH_KEY=""
while IFS= read -r line; do
  [ "$line" = "EOF" ] && break
  SSH_KEY+="$line\n"
done

gh secret set --repo "$REPO" VPS_HOST --body "$VPS_HOST"
gh secret set --repo "$REPO" VPS_USER --body "$VPS_USER"
gh secret set --repo "$REPO" VPS_SSH_PORT --body "$VPS_SSH_PORT"
gh secret set --repo "$REPO" VPS_SSH_KEY --body "$SSH_KEY"

echo "Secrets set for $REPO"
