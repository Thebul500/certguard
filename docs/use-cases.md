# CertGuard Use Cases

## 1. Multi-Host Certificate Inventory

Track SSL/TLS certificates across your entire infrastructure. Register every
host/port combination that serves a certificate, and CertGuard stores the
issuer, subject, SANs, serial number, fingerprint, and validity window.

```bash
# Register a certificate
curl -X POST http://localhost:8000/certificates/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "hostname": "api.example.com",
    "port": 443,
    "issuer": "CN=Let'\''s Encrypt Authority X3",
    "subject": "CN=api.example.com",
    "sans": "api.example.com,www.example.com",
    "not_before": "2026-01-01T00:00:00Z",
    "not_after": "2026-04-01T00:00:00Z",
    "serial_number": "03:a1:b2:c3:d4:e5",
    "fingerprint": "SHA256:abc123...",
    "status": "active"
  }'
```

## 2. Expiry Monitoring Dashboard

Query the full certificate inventory to identify upcoming expirations. Build
dashboards or scripts that poll the `/certificates/` endpoint and flag
certificates approaching their `not_after` date.

```bash
# List all certificates
curl http://localhost:8000/certificates/ \
  -H "Authorization: Bearer $TOKEN"
```

Filter results client-side or in your monitoring tool to find certificates
expiring within 30, 14, or 7 days.

## 3. Signal Alerting for Expiring Certificates

Pair CertGuard with a Signal REST API to send alerts when certificates are
nearing expiry. A cron job or external scheduler queries the API, checks
`not_after` dates, and sends a message:

```bash
#!/bin/bash
# Example cron script: check-certs.sh
CERTS=$(curl -s http://localhost:8000/certificates/ \
  -H "Authorization: Bearer $TOKEN")

# Parse and alert on certs expiring within 14 days
echo "$CERTS" | python3 -c "
import json, sys
from datetime import datetime, timezone, timedelta
certs = json.load(sys.stdin)
threshold = datetime.now(timezone.utc) + timedelta(days=14)
for c in certs:
    if c['not_after'] and datetime.fromisoformat(c['not_after']) < threshold:
        print(f\"EXPIRING: {c['hostname']}:{c['port']} — {c['not_after']}\")
"
```

## 4. CI/CD Certificate Validation

Integrate CertGuard into deployment pipelines to verify that newly deployed
services have valid, non-expired certificates before traffic is routed to them.

```yaml
# Example GitHub Actions step
- name: Verify certificate
  run: |
    CERT=$(curl -s http://certguard.internal:8000/certificates/ \
      -H "Authorization: Bearer ${{ secrets.CERTGUARD_TOKEN }}" \
      | jq '.[] | select(.hostname == "app.example.com")')
    NOT_AFTER=$(echo "$CERT" | jq -r '.not_after')
    if [ "$(date -d "$NOT_AFTER" +%s)" -lt "$(date +%s)" ]; then
      echo "Certificate expired!" && exit 1
    fi
```

## 5. Multi-Team Certificate Ownership

Use JWT-authenticated access to give different teams visibility into the
certificates they manage. Each team authenticates with their own credentials
and can create, update, or remove certificate records for their services.

```bash
# Register a team user
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "platform-team", "password": "secure-password-here"}'

# Obtain a token
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "platform-team", "password": "secure-password-here"}'
```

## 6. Certificate Lifecycle Tracking

Update certificate records after renewals to maintain an accurate inventory.
When a certificate is renewed via ACME, a post-renewal hook can push the new
metadata to CertGuard:

```bash
# Post-renewal hook (e.g., certbot deploy hook)
curl -X PUT http://localhost:8000/certificates/42 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "not_before": "2026-03-01T00:00:00Z",
    "not_after": "2026-06-01T00:00:00Z",
    "serial_number": "04:f1:a2:b3:c4:d5",
    "fingerprint": "SHA256:def456...",
    "status": "active"
  }'
```
