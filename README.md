# certguard

CLI tool to scan TLS certificates and check expiry dates. Connects to any host:port over TLS, retrieves the peer certificate, and reports subject, issuer, SANs, validity dates, serial number, and SHA-256 fingerprint.

[![CI](https://github.com/Thebul500/certguard/actions/workflows/ci.yml/badge.svg)](https://github.com/Thebul500/certguard/actions)

## Installation

```bash
pip install -e .
```

## Usage

### Scan a single host

```bash
certguard scan google.com
certguard scan google.com --port 8443
```

### Scan multiple hosts

```bash
certguard scan-range google.com github.com cloudflare.com
```

### Check certificate expiry

```bash
# Warn if cert expires within 30 days (default)
certguard check google.com

# Custom warning threshold
certguard check google.com --warn-days 60
```

Exit codes for `check`:
- **0** — certificate is valid and not expiring soon
- **1** — certificate expires within the warning window
- **2** — certificate is expired or host is unreachable

### Example output

```
$ certguard scan google.com
Scanning google.com:443 ...

Certificate for google.com:443
  Host:        google.com:443
  Subject:     commonName=*.google.com
  Issuer:      countryName=US, organizationName=Google Trust Services, commonName=WR2
  Serial:      0FC0B645D0B2524511D4DFD7BA
  SANs:        *.google.com, google.com
  Valid from:  2025-02-17 08:36:01 UTC
  Valid until: 2025-05-12 08:35:00 UTC
  Expires in:  64 days
  Fingerprint: A1:B2:C3:...
```

## Development

```bash
pip install -e ".[dev]"
pytest -v
```

## How it works

1. Opens a TCP connection to the target host:port
2. Performs a TLS handshake using Python's `ssl` module
3. Retrieves the peer certificate (handles self-signed certs gracefully)
4. Extracts and formats certificate fields
5. For multi-host scans, uses `asyncio` for concurrent connections

No database, no REST API, no Docker required. Just a simple CLI scanner.
