# certguard

SSL/TLS certificate inventory and expiry tracker. Scans network hosts for all certificates, builds a dashboard showing cert status, expiry dates, issuers, and SANs. Alerts via Signal when certs are approaching expiry. Supports scanning arbitrary hosts/ports, importing from files, and auto-renewal hooks.

[![CI](https://github.com/Thebul500/certguard/actions/workflows/ci.yml/badge.svg)](https://github.com/Thebul500/certguard/actions)

## Quick Start

```bash
docker compose up -d
curl http://localhost:8000/health
```

## Installation (Development)

```bash
pip install -e .[dev]
uvicorn certguard.app:app --reload
```

## Usage

```bash
# Start with Docker Compose (recommended)
docker compose up -d

# Or run directly
uvicorn certguard.app:app --host 0.0.0.0 --port 8000
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/ready` | Readiness probe |

## Configuration

Environment variables (prefix `CERTGUARD_`):

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://...` | Database connection string |
| `SECRET_KEY` | `change-me` | JWT signing key |
| `DEBUG` | `false` | Enable debug mode |
