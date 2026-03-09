# Hostinger VPS deployment

This deployment pulls `suneeb/odoo:latest` from Docker Hub and persists PostgreSQL and Odoo data on the VPS filesystem.

## Files

- `docker-compose.hostinger.yml`: VPS compose stack
- `.env.hostinger.example`: environment template
- `start.sh`: pull and start helper

## VPS setup

1. Install Docker Engine and the Docker Compose plugin on the VPS.
2. Clone this repository on the VPS or copy only the `deploy/hostinger` folder.
3. Create the runtime env file:

```bash
cd deploy/hostinger
cp .env.hostinger.example .env.hostinger
```

4. Edit `.env.hostinger` and set a real database password.
5. Start the stack:

```bash
chmod +x start.sh
./start.sh
```

## Ports

- Odoo HTTP: `127.0.0.1:${HOST_ODOO_PORT}`
- Odoo longpolling: `127.0.0.1:${HOST_LONGPOLLING_PORT}`
- PostgreSQL: `127.0.0.1:${HOST_PG_PORT}`

These are bound to localhost so you should place Nginx in front of Odoo.

## Data directories

- PostgreSQL data: `./data/postgres`
- Odoo filestore and data-dir: `./data/odoo`

## Useful commands

```bash
docker compose -f docker-compose.hostinger.yml --env-file .env.hostinger logs -f odoo
docker compose -f docker-compose.hostinger.yml --env-file .env.hostinger logs -f db
docker compose -f docker-compose.hostinger.yml --env-file .env.hostinger pull
docker compose -f docker-compose.hostinger.yml --env-file .env.hostinger up -d
```

## First login

Open Odoo through your VPS domain or reverse proxy and use the database name from `POSTGRES_DB`.
If you are restoring an existing database, also restore the filestore into `./data/odoo/filestore/<database_name>`.