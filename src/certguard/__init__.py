"""certguard — SSL/TLS certificate inventory and expiry tracker. Scans network hosts for all certificates, builds a dashboard showing cert status, expiry dates, issuers, and SANs. Alerts via Signal when certs are approaching expiry. Supports scanning arbitrary hosts/ports, importing from files, and auto-renewal hooks."""

__version__ = "0.1.0"
