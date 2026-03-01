# Deployment Guide

## Docker Compose (Recommended)

The simplest way to run CertGuard in production.

### Prerequisites

- Docker Engine 20.10+
- Docker Compose v2

### Steps

1. Clone the repository and set a secret key:

```bash
git clone https://github.com/Thebul500/certguard.git
cd certguard
export SECRET_KEY=$(openssl rand -hex 32)
```

2. Start the stack:

```bash
docker compose up -d
```

This launches:
- **app** — CertGuard API on port 8000
- **postgres** — PostgreSQL 16 database with a health check

3. Verify the deployment:

```bash
curl http://localhost:8000/health
# {"status":"healthy","version":"0.1.0","timestamp":"..."}

curl http://localhost:8000/ready
# {"status":"ready"}
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CERTGUARD_DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@postgres:5432/certguard` | Async database connection string |
| `CERTGUARD_SECRET_KEY` | `change-me-in-production` | JWT signing key — **must override in production** |
| `CERTGUARD_ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | JWT token lifetime |
| `CERTGUARD_DEBUG` | `false` | Enable debug mode |

### Database Migrations

CertGuard uses Alembic for schema migrations. After the database is running:

```bash
docker compose exec app alembic upgrade head
```

## Standalone Deployment

Run CertGuard directly without Docker.

### Prerequisites

- Python 3.11+
- PostgreSQL 14+

### Steps

1. Install the package:

```bash
pip install .
```

2. Set environment variables:

```bash
export CERTGUARD_DATABASE_URL="postgresql+asyncpg://user:pass@dbhost:5432/certguard"
export CERTGUARD_SECRET_KEY="$(openssl rand -hex 32)"
```

3. Run database migrations:

```bash
alembic upgrade head
```

4. Start the server:

```bash
uvicorn certguard.app:app --host 0.0.0.0 --port 8000
```

## Kubernetes

Deploy CertGuard behind an ingress controller with a managed PostgreSQL instance.

### Example Pod Spec

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: certguard
spec:
  replicas: 2
  selector:
    matchLabels:
      app: certguard
  template:
    metadata:
      labels:
        app: certguard
    spec:
      containers:
        - name: certguard
          image: certguard:latest
          ports:
            - containerPort: 8000
          env:
            - name: CERTGUARD_DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: certguard-secrets
                  key: database-url
            - name: CERTGUARD_SECRET_KEY
              valueFrom:
                secretKeyRef:
                  name: certguard-secrets
                  key: secret-key
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /ready
              port: 8000
            initialDelaySeconds: 3
            periodSeconds: 5
```

## Reverse Proxy

Place CertGuard behind nginx or Caddy for TLS termination:

```nginx
server {
    listen 443 ssl;
    server_name certguard.example.com;

    ssl_certificate     /etc/ssl/certs/certguard.pem;
    ssl_certificate_key /etc/ssl/private/certguard.key;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```
