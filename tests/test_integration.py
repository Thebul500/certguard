"""API integration tests — real HTTP calls via FastAPI TestClient.

Tests CRUD operations on certificates, auth flows (register/login),
and error cases (400, 401, 404). No mocks for HTTP calls.
"""

import secrets
import string

# Test-only constants — generated at import time so no credentials are hardcoded.
TEST_USERNAME = "testuser"
_ALPHABET = string.ascii_letters + string.digits + string.punctuation
TEST_PASSWORD = (
    "T"
    + secrets.choice(string.ascii_lowercase)
    + secrets.choice(string.digits)
    + "".join(secrets.choice(_ALPHABET) for _ in range(9))
)


# ── Helpers ──────────────────────────────────────────────────────────


def register_user(client, username=TEST_USERNAME, password=TEST_PASSWORD):
    """Register a user and return the response."""
    return client.post("/auth/register", json={"username": username, "password": password})


def login_user(client, username=TEST_USERNAME, password=TEST_PASSWORD):
    """Login and return the response."""
    return client.post("/auth/login", json={"username": username, "password": password})


def auth_header(client, username=TEST_USERNAME, password=TEST_PASSWORD):
    """Register, login, and return an Authorization header dict."""
    register_user(client, username, password)
    resp = login_user(client, username, password)
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


SAMPLE_CERT = {
    "hostname": "example.com",
    "port": 443,
    "issuer": "Let's Encrypt Authority X3",
    "subject": "CN=example.com",
    "sans": "example.com,www.example.com",
    "serial_number": "ABC123",
    "fingerprint": "AA:BB:CC:DD",
    "status": "active",
}


# ── Auth: Registration ──────────────────────────────────────────────


class TestAuthRegister:
    """POST /auth/register"""

    def test_register_success(self, client):
        resp = register_user(client)
        assert resp.status_code == 201
        data = resp.json()
        assert data["username"] == "testuser"
        assert data["is_active"] is True
        assert "id" in data
        assert "hashed_password" not in data  # never leak password hash

    def test_register_duplicate_username(self, client):
        register_user(client)
        resp = register_user(client)  # same username again
        assert resp.status_code == 400
        assert "already taken" in resp.json()["detail"].lower()

    def test_register_short_username(self, client):
        resp = register_user(client, username="ab")
        assert resp.status_code == 422  # validation error

    def test_register_short_password(self, client):
        resp = register_user(client, password="short")
        assert resp.status_code == 422

    def test_register_missing_fields(self, client):
        resp = client.post("/auth/register", json={})
        assert resp.status_code == 422


# ── Auth: Login ─────────────────────────────────────────────────────


class TestAuthLogin:
    """POST /auth/login"""

    def test_login_success(self, client):
        register_user(client)
        resp = login_user(client)
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client):
        register_user(client)
        resp = login_user(client, password="wrong!1")
        assert resp.status_code == 401
        assert "invalid" in resp.json()["detail"].lower()

    def test_login_nonexistent_user(self, client):
        resp = login_user(client, username="ghost")
        assert resp.status_code == 401

    def test_login_missing_fields(self, client):
        resp = client.post("/auth/login", json={})
        assert resp.status_code == 422


# ── Auth: Protected endpoint access ────────────────────────────────


class TestAuthProtection:
    """Verify endpoints require valid JWT."""

    def test_no_token_returns_401(self, client):
        resp = client.get("/certificates/")
        assert resp.status_code == 401

    def test_invalid_token_returns_401(self, client):
        resp = client.get("/certificates/", headers={"Authorization": "Bearer bad.token.here"})
        assert resp.status_code == 401

    def test_valid_token_grants_access(self, client):
        headers = auth_header(client)
        resp = client.get("/certificates/", headers=headers)
        assert resp.status_code == 200


# ── Certificates: POST (Create) ────────────────────────────────────


class TestCertificateCreate:
    """POST /certificates/"""

    def test_create_certificate(self, client):
        headers = auth_header(client)
        resp = client.post("/certificates/", json=SAMPLE_CERT, headers=headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["hostname"] == "example.com"
        assert data["port"] == 443
        assert data["issuer"] == "Let's Encrypt Authority X3"
        assert data["status"] == "active"
        assert "id" in data

    def test_create_minimal_certificate(self, client):
        headers = auth_header(client)
        resp = client.post("/certificates/", json={"hostname": "min.example.com"}, headers=headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["hostname"] == "min.example.com"
        assert data["port"] == 443  # default

    def test_create_certificate_invalid_port(self, client):
        headers = auth_header(client)
        resp = client.post(
            "/certificates/",
            json={"hostname": "example.com", "port": 99999},
            headers=headers,
        )
        assert resp.status_code == 422

    def test_create_certificate_empty_hostname(self, client):
        headers = auth_header(client)
        resp = client.post(
            "/certificates/",
            json={"hostname": ""},
            headers=headers,
        )
        assert resp.status_code == 422

    def test_create_certificate_no_auth(self, client):
        resp = client.post("/certificates/", json=SAMPLE_CERT)
        assert resp.status_code == 401


# ── Certificates: GET (Read) ───────────────────────────────────────


class TestCertificateRead:
    """GET /certificates/ and GET /certificates/{id}"""

    def test_list_empty(self, client):
        headers = auth_header(client)
        resp = client.get("/certificates/", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_returns_created(self, client):
        headers = auth_header(client)
        client.post("/certificates/", json=SAMPLE_CERT, headers=headers)
        client.post(
            "/certificates/",
            json={**SAMPLE_CERT, "hostname": "other.com"},
            headers=headers,
        )
        resp = client.get("/certificates/", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        hostnames = {c["hostname"] for c in data}
        assert hostnames == {"example.com", "other.com"}

    def test_get_by_id(self, client):
        headers = auth_header(client)
        create_resp = client.post("/certificates/", json=SAMPLE_CERT, headers=headers)
        cert_id = create_resp.json()["id"]

        resp = client.get(f"/certificates/{cert_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == cert_id
        assert resp.json()["hostname"] == "example.com"

    def test_get_nonexistent_returns_404(self, client):
        headers = auth_header(client)
        resp = client.get("/certificates/9999", headers=headers)
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()


# ── Certificates: PUT (Update) ─────────────────────────────────────


class TestCertificateUpdate:
    """PUT /certificates/{id}"""

    def test_update_certificate(self, client):
        headers = auth_header(client)
        create_resp = client.post("/certificates/", json=SAMPLE_CERT, headers=headers)
        cert_id = create_resp.json()["id"]

        resp = client.put(
            f"/certificates/{cert_id}",
            json={"hostname": "updated.com", "status": "expiring"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["hostname"] == "updated.com"
        assert data["status"] == "expiring"
        assert data["issuer"] == "Let's Encrypt Authority X3"  # unchanged field preserved

    def test_partial_update(self, client):
        headers = auth_header(client)
        create_resp = client.post("/certificates/", json=SAMPLE_CERT, headers=headers)
        cert_id = create_resp.json()["id"]

        resp = client.put(
            f"/certificates/{cert_id}",
            json={"status": "expired"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "expired"
        assert resp.json()["hostname"] == "example.com"  # unchanged

    def test_update_nonexistent_returns_404(self, client):
        headers = auth_header(client)
        resp = client.put(
            "/certificates/9999",
            json={"hostname": "ghost.com"},
            headers=headers,
        )
        assert resp.status_code == 404

    def test_update_invalid_port(self, client):
        headers = auth_header(client)
        create_resp = client.post("/certificates/", json=SAMPLE_CERT, headers=headers)
        cert_id = create_resp.json()["id"]

        resp = client.put(
            f"/certificates/{cert_id}",
            json={"port": 0},
            headers=headers,
        )
        assert resp.status_code == 422

    def test_update_no_auth(self, client):
        resp = client.put("/certificates/1", json={"hostname": "evil.com"})
        assert resp.status_code == 401


# ── Certificates: DELETE ────────────────────────────────────────────


class TestCertificateDelete:
    """DELETE /certificates/{id}"""

    def test_delete_certificate(self, client):
        headers = auth_header(client)
        create_resp = client.post("/certificates/", json=SAMPLE_CERT, headers=headers)
        cert_id = create_resp.json()["id"]

        resp = client.delete(f"/certificates/{cert_id}", headers=headers)
        assert resp.status_code == 204

        # Confirm it's gone
        resp = client.get(f"/certificates/{cert_id}", headers=headers)
        assert resp.status_code == 404

    def test_delete_nonexistent_returns_404(self, client):
        headers = auth_header(client)
        resp = client.delete("/certificates/9999", headers=headers)
        assert resp.status_code == 404

    def test_delete_no_auth(self, client):
        resp = client.delete("/certificates/1")
        assert resp.status_code == 401


# ── Full CRUD lifecycle ────────────────────────────────────────────


class TestCRUDLifecycle:
    """End-to-end test: create → read → update → delete."""

    def test_full_lifecycle(self, client):
        headers = auth_header(client)

        # Create
        resp = client.post("/certificates/", json=SAMPLE_CERT, headers=headers)
        assert resp.status_code == 201
        cert_id = resp.json()["id"]

        # Read
        resp = client.get(f"/certificates/{cert_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["hostname"] == "example.com"

        # Update
        resp = client.put(
            f"/certificates/{cert_id}",
            json={"status": "renewed", "hostname": "renewed.example.com"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "renewed"
        assert resp.json()["hostname"] == "renewed.example.com"

        # Delete
        resp = client.delete(f"/certificates/{cert_id}", headers=headers)
        assert resp.status_code == 204

        # Verify gone
        resp = client.get(f"/certificates/{cert_id}", headers=headers)
        assert resp.status_code == 404

        # List should be empty
        resp = client.get("/certificates/", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []
