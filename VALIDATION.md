# Real-World Validation Report

Full Docker Compose stack validation of the certguard API.

## Test Environment

- **Date**: 2026-03-02
- **Host**: Linux 6.17.0-14-generic (x86_64)
- **Docker**: Docker Compose v2, containers running in bridge network
- **App image**: `certguard-app:latest` (140 MB, Python 3.12-alpine, multi-stage build)
- **Database**: `postgres:16-alpine` (276 MB)
- **Stack ports**: app on 8000, postgres on 5432

## Stack Startup

Docker Compose brought up both services. Postgres health check passed (`pg_isready`),
app started uvicorn on port 8000. Tables auto-created via SQLAlchemy `create_all` in
the FastAPI lifespan handler.

```
$ docker compose up -d
 Container certguard-postgres-1  Created
 Container certguard-app-1  Created
 Container certguard-postgres-1  Started
 Container certguard-postgres-1  Healthy
 Container certguard-app-1  Started
```

Container status after startup:

```
NAME                   IMAGE                SERVICE    STATUS                    PORTS
certguard-app-1        certguard-app        app        Up About a minute         0.0.0.0:8000->8000/tcp
certguard-postgres-1   postgres:16-alpine   postgres   Up About a minute (healthy)   0.0.0.0:5432->5432/tcp
```

## Test Results Summary

| # | Test | Method | Endpoint | Expected | Actual | Status |
|---|------|--------|----------|----------|--------|--------|
| 1 | Health check | GET | /health | 200 | 200 | PASS |
| 2 | Readiness | GET | /ready | 200 | 200 | PASS |
| 3 | Register user | POST | /auth/register | 201 | 201 | PASS |
| 4 | Login | POST | /auth/login | 200 + JWT | 200 + JWT | PASS |
| 5 | Create cert | POST | /certificates/ | 201 | 201 | PASS |
| 6 | Create cert (2nd) | POST | /certificates/ | 201 | 201 | PASS |
| 7 | List certs | GET | /certificates/ | 200 + 2 items | 200 + 2 items | PASS |
| 8 | Get single cert | GET | /certificates/1 | 200 | 200 | PASS |
| 9 | Update cert | PUT | /certificates/1 | 200 + updated fields | 200 + updated | PASS |
| 10 | Delete cert | DELETE | /certificates/2 | 204 | 204 | PASS |
| 11 | List after delete | GET | /certificates/ | 200 + 1 item | 200 + 1 item | PASS |
| 12 | Unauth access | GET | /certificates/ | 401 | 401 | PASS |
| 13 | Not found | GET | /certificates/999 | 404 | 404 | PASS |
| 14 | Duplicate register | POST | /auth/register | 400 | 400 | PASS |
| 15 | Bad credentials | POST | /auth/login | 401 | 401 | PASS |
| 16 | Invalid token | GET | /certificates/ | 401 | 401 | PASS |
| 17 | Validation error | POST | /certificates/ | 422 | 422 | PASS |
| 18 | OpenAPI docs | GET | /docs | 200 | 200 | PASS |

**Result: 18/18 tests passed.**

## Detailed Test Output

### Test 1: GET /health

```
Timestamp: 2026-03-02T02:14:48Z

$ curl -s http://localhost:8000/health
{
  "status": "healthy",
  "version": "0.1.0",
  "timestamp": "2026-03-02T02:14:48.181460Z"
}

HTTP Status: 200
```

### Test 2: GET /ready

```
Timestamp: 2026-03-02T02:14:50Z

$ curl -s http://localhost:8000/ready
{
  "status": "ready"
}

HTTP Status: 200
```

### Test 3: POST /auth/register

```
Timestamp: 2026-03-02T02:14:58Z

$ curl -s -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"securepass123"}'

{
  "id": 1,
  "username": "testuser",
  "is_active": true,
  "created_at": "2026-03-02T02:14:58.443226"
}

HTTP Status: 201
```

### Test 4: POST /auth/login

```
Timestamp: 2026-03-02T02:15:03Z

$ curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"securepass123"}'

{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0dXNlciIsImV4cCI6MTc3MjQxOTUwM30.ydCTgFvxu6McXx2uMlUF2X5FtGvwK8Z9SkW2h98YYNQ",
  "token_type": "bearer"
}

HTTP Status: 200
```

### Test 5: POST /certificates/ (Create first)

```
Timestamp: 2026-03-02T02:15:14Z

$ curl -s -X POST http://localhost:8000/certificates/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"hostname":"google.com","port":443,"issuer":"CN=GTS CA 1C3, O=Google Trust Services LLC","subject":"CN=*.google.com","sans":"*.google.com, google.com","not_before":"2026-02-10T00:00:00","not_after":"2026-05-05T00:00:00","serial_number":"ABCDEF1234567890","fingerprint":"AA:BB:CC:DD:EE:FF:00:11:22:33","status":"active"}'

{
  "id": 1,
  "hostname": "google.com",
  "port": 443,
  "issuer": "CN=GTS CA 1C3, O=Google Trust Services LLC",
  "subject": "CN=*.google.com",
  "sans": "*.google.com, google.com",
  "not_before": "2026-02-10T00:00:00",
  "not_after": "2026-05-05T00:00:00",
  "serial_number": "ABCDEF1234567890",
  "fingerprint": "AA:BB:CC:DD:EE:FF:00:11:22:33",
  "status": "active",
  "created_at": "2026-03-02T02:15:14.768751",
  "updated_at": "2026-03-02T02:15:14.768751"
}

HTTP Status: 201
```

### Test 6: POST /certificates/ (Create second)

```
Timestamp: 2026-03-02T02:15:28Z

$ curl -s -X POST http://localhost:8000/certificates/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"hostname":"github.com","port":443,"issuer":"CN=DigiCert SHA2 High Assurance Server CA","subject":"CN=github.com","sans":"github.com, www.github.com","not_before":"2026-01-15T00:00:00","not_after":"2026-07-15T00:00:00","serial_number":"FEDCBA0987654321","fingerprint":"11:22:33:44:55:66:77:88:99:AA","status":"active"}'

{
  "id": 2,
  "hostname": "github.com",
  "port": 443,
  "issuer": "CN=DigiCert SHA2 High Assurance Server CA",
  "subject": "CN=github.com",
  "sans": "github.com, www.github.com",
  "not_before": "2026-01-15T00:00:00",
  "not_after": "2026-07-15T00:00:00",
  "serial_number": "FEDCBA0987654321",
  "fingerprint": "11:22:33:44:55:66:77:88:99:AA",
  "status": "active",
  "created_at": "2026-03-02T02:15:28.336499",
  "updated_at": "2026-03-02T02:15:28.336499"
}

HTTP Status: 201
```

### Test 7: GET /certificates/ (List all)

```
Timestamp: 2026-03-02T02:15:32Z

$ curl -s http://localhost:8000/certificates/ -H "Authorization: Bearer $TOKEN"

[
  {"id":1, "hostname":"google.com", "port":443, "status":"active", ...},
  {"id":2, "hostname":"github.com", "port":443, "status":"active", ...}
]

HTTP Status: 200
(2 certificates returned)
```

### Test 8: GET /certificates/1 (Get single)

```
Timestamp: 2026-03-02T02:15:36Z

$ curl -s http://localhost:8000/certificates/1 -H "Authorization: Bearer $TOKEN"

{
  "id": 1,
  "hostname": "google.com",
  "port": 443,
  "issuer": "CN=GTS CA 1C3, O=Google Trust Services LLC",
  "subject": "CN=*.google.com",
  "status": "active",
  ...
}

HTTP Status: 200
```

### Test 9: PUT /certificates/1 (Update)

```
Timestamp: 2026-03-02T02:15:41Z

$ curl -s -X PUT http://localhost:8000/certificates/1 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status":"expiring_soon","not_after":"2026-03-15T00:00:00"}'

{
  "id": 1,
  "hostname": "google.com",
  "port": 443,
  "not_after": "2026-03-15T00:00:00",
  "status": "expiring_soon",
  "updated_at": "2026-03-02T02:15:41.488206",
  ...
}

HTTP Status: 200
(status changed from "active" to "expiring_soon", not_after updated, updated_at changed)
```

### Test 10: DELETE /certificates/2

```
Timestamp: 2026-03-02T02:15:45Z

$ curl -s -X DELETE http://localhost:8000/certificates/2 -H "Authorization: Bearer $TOKEN"

HTTP Status: 204 (No Content)
```

### Test 11: GET /certificates/ (Verify deletion)

```
Timestamp: 2026-03-02T02:15:51Z

$ curl -s http://localhost:8000/certificates/ -H "Authorization: Bearer $TOKEN"

[
  {"id":1, "hostname":"google.com", "status":"expiring_soon", ...}
]

HTTP Status: 200
(1 certificate returned — github.com was deleted)
```

### Test 12: GET /certificates/ without auth (401)

```
Timestamp: 2026-03-02T02:15:59Z

$ curl -s http://localhost:8000/certificates/

{"detail": "Not authenticated"}

HTTP Status: 401
```

### Test 13: GET /certificates/999 (404)

```
Timestamp: 2026-03-02T02:16:01Z

$ curl -s http://localhost:8000/certificates/999 -H "Authorization: Bearer $TOKEN"

{"detail": "Certificate not found"}

HTTP Status: 404
```

### Test 14: POST /auth/register — duplicate username (400)

```
Timestamp: 2026-03-02T02:16:03Z

$ curl -s -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"anotherpass123"}'

{"detail": "Username already taken"}

HTTP Status: 400
```

### Test 15: POST /auth/login — wrong password (401)

```
Timestamp: 2026-03-02T02:16:04Z

$ curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"wrongpassword"}'

{"detail": "Invalid credentials"}

HTTP Status: 401
```

### Test 16: GET /certificates/ with invalid JWT (401)

```
Timestamp: 2026-03-02T02:16:05Z

$ curl -s http://localhost:8000/certificates/ -H "Authorization: Bearer invalidtoken123"

{"detail": "Invalid or expired token"}

HTTP Status: 401
```

### Test 17: POST /certificates/ — validation error (422)

```
Timestamp: 2026-03-02T02:16:08Z

$ curl -s -X POST http://localhost:8000/certificates/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"hostname":"test.com","port":99999}'

{
  "detail": [{
    "type": "less_than_equal",
    "loc": ["body", "port"],
    "msg": "Input should be less than or equal to 65535",
    "input": 99999,
    "ctx": {"le": 65535}
  }]
}

HTTP Status: 422
```

### Test 18: GET /docs (OpenAPI)

```
Timestamp: 2026-03-02T02:16:19Z

$ curl -s -o /dev/null -w "HTTP Status: %{http_code}\nSize: %{size_download} bytes\n" \
  http://localhost:8000/docs

HTTP Status: 200
Size: 1008 bytes
```

## Application Logs

Full uvicorn access log from the validation run:

```
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     172.27.0.1:57836 - "GET /health HTTP/1.1" 200 OK
INFO:     172.27.0.1:57850 - "GET /ready HTTP/1.1" 200 OK
INFO:     172.27.0.1:54108 - "POST /auth/register HTTP/1.1" 201 Created
INFO:     172.27.0.1:34860 - "POST /auth/login HTTP/1.1" 200 OK
INFO:     172.27.0.1:34868 - "POST /certificates/ HTTP/1.1" 201 Created
INFO:     172.27.0.1:51190 - "POST /certificates/ HTTP/1.1" 201 Created
INFO:     172.27.0.1:43730 - "GET /certificates/ HTTP/1.1" 200 OK
INFO:     172.27.0.1:43760 - "GET /certificates/1 HTTP/1.1" 200 OK
INFO:     172.27.0.1:43792 - "PUT /certificates/1 HTTP/1.1" 200 OK
INFO:     172.27.0.1:57074 - "DELETE /certificates/2 HTTP/1.1" 204 No Content
INFO:     172.27.0.1:57090 - "GET /certificates/ HTTP/1.1" 200 OK
INFO:     172.27.0.1:58026 - "GET /certificates/ HTTP/1.1" 401 Unauthorized
INFO:     172.27.0.1:53256 - "GET /certificates/999 HTTP/1.1" 404 Not Found
INFO:     172.27.0.1:53268 - "POST /auth/register HTTP/1.1" 400 Bad Request
INFO:     172.27.0.1:53280 - "POST /auth/login HTTP/1.1" 401 Unauthorized
INFO:     172.27.0.1:53290 - "GET /certificates/ HTTP/1.1" 401 Unauthorized
INFO:     172.27.0.1:53304 - "POST /certificates/ HTTP/1.1" 422 Unprocessable Entity
INFO:     172.27.0.1:50786 - "GET /docs HTTP/1.1" 200 OK
```

## Limitations and Notes

1. **No live certificate scanning in this test**: The API stores certificate metadata
   as CRUD records. The validation exercises the inventory/tracking API, not live TLS
   scanning of remote hosts.
2. **Single-worker uvicorn**: The Docker CMD runs a single uvicorn worker. Production
   deployments should use `--workers N` or a process manager like gunicorn.
3. **No pagination**: The `GET /certificates/` endpoint returns all records without
   pagination. This is fine for small inventories but would need pagination for large
   deployments.
4. **No per-user isolation**: All authenticated users can see and modify all
   certificates. Role-based access control is not implemented.
5. **Token expiry**: JWT tokens expire after 30 minutes (configurable via
   `CERTGUARD_ACCESS_TOKEN_EXPIRE_MINUTES`). No refresh token mechanism exists.
6. **Auto-table creation**: The app creates database tables via SQLAlchemy
   `create_all` on startup. For production schema migrations, Alembic is configured
   but no migration scripts have been generated yet.
