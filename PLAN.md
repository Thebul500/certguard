# CertGuard — Project Plan

## Architecture

### System Overview

CertGuard is a REST API service that maintains an inventory of SSL/TLS certificates across network infrastructure. It actively scans hosts, stores certificate metadata, and sends alerts before certificates expire.

```
┌─────────────┐     ┌──────────────────┐     ┌────────────┐
│  HTTP Client│────▶│  FastAPI (async)  │────▶│ PostgreSQL │
└─────────────┘     │                  │     └────────────┘
                    │  ┌────────────┐  │
                    │  │ TLS Scanner│  │     ┌────────────┐
                    │  └────────────┘  │────▶│ Signal API │
                    │  ┌────────────┐  │     └────────────┘
                    │  │ Scheduler  │  │
                    │  └────────────┘  │
                    └──────────────────┘
```

**Components:**

- **API layer** — FastAPI routers handling CRUD for certificates, hosts, and scan jobs. All endpoints return JSON with Pydantic-validated schemas.
- **TLS scanner** — Async module that opens TCP connections with `ssl` + `asyncio`, extracts certificate chains, parses x509 fields (subject, issuer, SANs, serial, expiry dates, fingerprint).
- **Alert engine** — Background task that queries certificates approaching expiry (configurable threshold, default 30 days) and sends notifications via Signal REST API.
- **Scheduler** — Optional periodic scan loop using FastAPI lifespan background tasks. Re-scans all registered hosts on a configurable interval.

### API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/auth/register` | No | Create user account |
| `POST` | `/auth/login` | No | Get JWT access token |
| `GET` | `/certificates` | Yes | List all certificates (paginated, filterable) |
| `GET` | `/certificates/{id}` | Yes | Get single certificate detail |
| `DELETE` | `/certificates/{id}` | Yes | Remove certificate from inventory |
| `POST` | `/hosts` | Yes | Register a host:port to monitor |
| `GET` | `/hosts` | Yes | List monitored hosts |
| `DELETE` | `/hosts/{id}` | Yes | Remove host from monitoring |
| `POST` | `/scan` | Yes | Trigger immediate scan of one or more hosts |
| `POST` | `/scan/import` | Yes | Import certificates from PEM file upload |
| `GET` | `/scan/{id}` | Yes | Get scan job status and results |
| `GET` | `/alerts` | Yes | List alert history |
| `POST` | `/alerts/test` | Yes | Send a test alert via Signal |
| `GET` | `/health` | No | Health check |
| `GET` | `/ready` | No | Readiness probe |

### Data Model

```
User
├── id: int (PK)
├── username: str (unique)
├── password_hash: str
├── created_at: datetime
└── updated_at: datetime

Host
├── id: int (PK)
├── hostname: str
├── port: int (default 443)
├── label: str (optional, human-readable name)
├── is_active: bool (default true)
├── last_scanned_at: datetime (nullable)
├── created_at: datetime
└── updated_at: datetime

Certificate
├── id: int (PK)
├── host_id: int (FK → Host, nullable for imported certs)
├── serial_number: str
├── fingerprint_sha256: str (unique)
├── subject: str
├── issuer: str
├── sans: JSON (list of subject alternative names)
├── not_before: datetime
├── not_after: datetime
├── chain_depth: int
├── pem: text (full PEM-encoded cert)
├── status: enum (valid, expiring, expired, revoked, unknown)
├── last_seen_at: datetime
├── created_at: datetime
└── updated_at: datetime

ScanJob
├── id: int (PK)
├── status: enum (pending, running, completed, failed)
├── hosts_scanned: int
├── certs_found: int
├── errors: JSON (list of error messages)
├── started_at: datetime
├── completed_at: datetime (nullable)
├── created_at: datetime
└── updated_at: datetime

AlertLog
├── id: int (PK)
├── certificate_id: int (FK → Certificate)
├── alert_type: str (expiry_warning, expired, new_cert)
├── message: str
├── delivered: bool
├── delivered_at: datetime (nullable)
├── created_at: datetime
└── updated_at: datetime
```

### Auth Flow

1. User registers via `POST /auth/register` with username + password.
2. Password is hashed with bcrypt via `passlib`.
3. User logs in via `POST /auth/login`, receives a JWT access token.
4. JWT is signed with `CERTGUARD_SECRET_KEY`, expires after `ACCESS_TOKEN_EXPIRE_MINUTES`.
5. Protected endpoints require `Authorization: Bearer <token>` header.
6. A FastAPI dependency (`get_current_user`) decodes the JWT and loads the user from the database, returning 401 on invalid/expired tokens.

### Deployment Architecture

**Docker Compose (default):**

- `app` — CertGuard FastAPI container, port 8000
- `postgres` — PostgreSQL 16, persistent volume
- Alembic migrations run on startup via lifespan hook
- Health checks on both containers for orchestrator compatibility

**Production additions:**

- Reverse proxy (nginx/caddy) for TLS termination in front of the API
- Environment-based config: `CERTGUARD_SECRET_KEY`, `CERTGUARD_DATABASE_URL`, `CERTGUARD_SIGNAL_API_URL`
- Container image published to GHCR via CI pipeline

---

## Technology

| Technology | Role | Why |
|---|---|---|
| **Python 3.11+** | Language | Excellent async support, rich `ssl`/`cryptography` ecosystem for x509 parsing. |
| **FastAPI** | Web framework | Native async, automatic OpenAPI docs, Pydantic validation, dependency injection. The standard for modern Python APIs. |
| **SQLAlchemy 2.0 (async)** | ORM | Mature, type-safe ORM with first-class async session support via `asyncpg`. Declarative models map cleanly to the data model. |
| **PostgreSQL 16** | Database | Reliable, supports JSON columns for SANs/errors, strong indexing for expiry date queries. |
| **asyncpg** | DB driver | Fastest async PostgreSQL driver for Python, pairs with SQLAlchemy async engine. |
| **Alembic** | Migrations | De facto migration tool for SQLAlchemy. Already scaffolded. |
| **python-jose** | JWT | Lightweight JWT encode/decode with cryptography backend. Already a dependency. |
| **passlib + bcrypt** | Password hashing | Industry-standard password hashing. Already a dependency. |
| **httpx** | HTTP client | Async HTTP client for calling Signal REST API and potential webhook integrations. |
| **Pydantic Settings** | Config | Typed environment variable parsing with `CERTGUARD_` prefix. Already configured. |
| **ssl + cryptography** | TLS scanning | Python stdlib `ssl` for connections, `cryptography` library for x509 certificate parsing. |
| **Ruff** | Linter/formatter | Fast, replaces flake8+isort+black in a single tool. Already configured. |
| **pytest + pytest-asyncio** | Testing | Async test support with fixtures for database sessions and HTTPX test client. |
| **Docker** | Deployment | Reproducible builds, compose for local dev, single-image production deployment. |

---

## Milestones

### Milestone 1 — Core CRUD & Auth
**Goal:** Working API with user authentication, host management, and certificate storage.

- [ ] User model + auth routes (register, login, JWT issuance)
- [ ] `get_current_user` dependency for protected routes
- [ ] Host model + CRUD routes (create, list, delete)
- [ ] Certificate model + read/list/delete routes
- [ ] Alembic initial migration for all models
- [ ] Request/response Pydantic schemas for all endpoints
- [ ] Unit tests for auth flow and CRUD operations

### Milestone 2 — TLS Scanner
**Goal:** Scan hosts and extract certificate data into the inventory.

- [ ] Async TLS scanner module (`certguard/scanner.py`)
- [ ] Connect to host:port, retrieve full certificate chain
- [ ] Parse x509: subject, issuer, SANs, serial, fingerprint, validity dates
- [ ] ScanJob model for tracking scan progress
- [ ] `POST /scan` endpoint to trigger scans (single host or all active hosts)
- [ ] `POST /scan/import` endpoint for PEM file upload
- [ ] Upsert logic: update existing certs by fingerprint, insert new ones
- [ ] Certificate status computation (valid / expiring / expired)
- [ ] Tests with mocked TLS connections

### Milestone 3 — Alerts & Notifications
**Goal:** Proactive alerting when certificates approach expiry.

- [ ] AlertLog model for delivery tracking
- [ ] Alert engine: query certs where `not_after` is within threshold
- [ ] Signal REST API integration via httpx
- [ ] `GET /alerts` endpoint for alert history
- [ ] `POST /alerts/test` for manual test notification
- [ ] Configurable alert thresholds (30d, 14d, 7d, 1d)
- [ ] Deduplication: don't re-alert for the same cert within a cooldown window
- [ ] Tests for alert logic and Signal API integration

### Milestone 4 — Scheduling & Background Tasks
**Goal:** Automated periodic scanning without manual triggers.

- [ ] Background scan scheduler in FastAPI lifespan
- [ ] Configurable scan interval via `CERTGUARD_SCAN_INTERVAL_HOURS`
- [ ] Auto-renewal hook support: configurable webhook URL called when a cert is renewed (fingerprint changes)
- [ ] Scan history and last-scanned tracking on hosts
- [ ] Dashboard summary endpoint: total certs, expiring soon, expired count

### Milestone 5 — Production Hardening
**Goal:** CI/CD, security, documentation, and deployment readiness.

- [ ] Integration tests against real database (docker-compose test profile)
- [ ] 80%+ test coverage
- [ ] Ruff lint clean
- [ ] Security audit (bandit, dependency scanning)
- [ ] Rate limiting on auth endpoints
- [ ] CORS configuration for production
- [ ] API documentation in `docs/`
- [ ] SECURITY.md, CONTRIBUTING.md
- [ ] Container image scanning and SBOM generation
- [ ] CI pipeline: lint, test, coverage, build, publish
