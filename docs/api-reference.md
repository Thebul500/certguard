# API Reference

Base URL: `http://localhost:8000`

All certificate endpoints require a valid JWT token in the `Authorization: Bearer <token>` header.

## Health

### `GET /health`

Returns application health status.

**Response** `200 OK`
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "timestamp": "2026-03-01T12:00:00Z"
}
```

### `GET /ready`

Readiness probe for load balancers and orchestrators.

**Response** `200 OK`
```json
{"status": "ready"}
```

## Authentication

### `POST /auth/register`

Register a new user account.

**Request Body**
```json
{
  "username": "admin",
  "password": "securepassword"
}
```

| Field | Type | Constraints |
|-------|------|-------------|
| `username` | string | 3–255 characters |
| `password` | string | 8–128 characters |

**Response** `201 Created`
```json
{
  "id": 1,
  "username": "admin",
  "is_active": true,
  "created_at": "2026-03-01T12:00:00Z"
}
```

**Errors**
- `400 Bad Request` — Username already taken

### `POST /auth/login`

Authenticate and receive a JWT access token.

**Request Body**
```json
{
  "username": "admin",
  "password": "securepassword"
}
```

**Response** `200 OK`
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

**Errors**
- `401 Unauthorized` — Invalid credentials

## Certificates

All endpoints require authentication.

### `POST /certificates/`

Add a new certificate record.

**Request Body**
```json
{
  "hostname": "example.com",
  "port": 443,
  "issuer": "CN=Let's Encrypt Authority X3",
  "subject": "CN=example.com",
  "sans": "example.com,www.example.com",
  "not_before": "2026-01-01T00:00:00Z",
  "not_after": "2026-04-01T00:00:00Z",
  "serial_number": "03:a1:b2:c3:d4:e5",
  "fingerprint": "SHA256:abc123...",
  "status": "active"
}
```

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `hostname` | string | yes | — |
| `port` | integer (1–65535) | no | `443` |
| `issuer` | string | no | `null` |
| `subject` | string | no | `null` |
| `sans` | string | no | `null` |
| `not_before` | datetime | no | `null` |
| `not_after` | datetime | no | `null` |
| `serial_number` | string | no | `null` |
| `fingerprint` | string | no | `null` |
| `status` | string | no | `"active"` |

**Response** `201 Created` — Returns the full certificate record.

### `GET /certificates/`

List all certificate records, ordered by ID.

**Response** `200 OK` — Array of certificate objects.

### `GET /certificates/{cert_id}`

Get a single certificate by its ID.

**Response** `200 OK` — Certificate object.

**Errors**
- `404 Not Found` — Certificate not found

### `PUT /certificates/{cert_id}`

Update an existing certificate. Only provided fields are changed.

**Request Body** — Same fields as `POST`, all optional.

**Response** `200 OK` — Updated certificate object.

**Errors**
- `404 Not Found` — Certificate not found

### `DELETE /certificates/{cert_id}`

Delete a certificate record.

**Response** `204 No Content`

**Errors**
- `404 Not Found` — Certificate not found
