# certguard

Certificate metadata store with REST API. Manage SSL/TLS certificate records — track hostnames, expiry dates, issuers, SANs, and fingerprints. Provides full CRUD operations behind JWT authentication.

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
| POST | `/auth/register` | Register a new user |
| POST | `/auth/login` | Authenticate and get JWT token |
| POST | `/certificates/` | Add a certificate record (auth required) |
| GET | `/certificates/` | List all certificate records (auth required) |
| GET | `/certificates/{id}` | Get a single certificate (auth required) |
| PUT | `/certificates/{id}` | Update a certificate record (auth required) |
| DELETE | `/certificates/{id}` | Delete a certificate record (auth required) |

## Configuration

Environment variables (prefix `CERTGUARD_`):

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://...` | Database connection string |
| `SECRET_KEY` | `change-me` | JWT signing key |
| `DEBUG` | `false` | Enable debug mode |
