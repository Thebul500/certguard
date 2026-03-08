"""TLS certificate scanner — the core of certguard.

Connects to hosts over TLS, retrieves peer certificates, and extracts
subject, issuer, SANs, validity dates, serial number, and SHA-256 fingerprint.
"""

from __future__ import annotations

import asyncio
import hashlib
import pathlib
import socket
import ssl
import tempfile
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class CertInfo:
    """Parsed TLS certificate information."""

    host: str
    port: int
    subject: str
    issuer: str
    serial_number: str
    sans: list[str]
    not_before: datetime
    not_after: datetime
    fingerprint_sha256: str
    error: str | None = None

    @property
    def days_until_expiry(self) -> int:
        """Days remaining until the certificate expires."""
        delta = self.not_after - datetime.now(UTC)
        return delta.days

    @property
    def is_expired(self) -> bool:
        """Whether the certificate has already expired."""
        return self.days_until_expiry < 0


@dataclass
class ScanError:
    """Returned when a scan fails (connection refused, timeout, etc.)."""

    host: str
    port: int
    error: str
    sans: list[str] = field(default_factory=list)


ScanResult = CertInfo | ScanError


def _format_dn(dn_tuples: tuple[tuple[tuple[str, str], ...], ...]) -> str:
    """Format an X.509 distinguished name into a readable string.

    The ssl module returns DNs as nested tuples like:
        ((('commonName', 'example.com'),), (('organizationName', 'Org'),))
    """
    parts: list[str] = []
    for rdn in dn_tuples:
        for attr_type, attr_value in rdn:
            parts.append(f"{attr_type}={attr_value}")
    return ", ".join(parts)


def _extract_sans(cert_dict: dict) -> list[str]:
    """Extract Subject Alternative Names from a certificate dict."""
    san_entries = cert_dict.get("subjectAltName", ())
    return [value for _type, value in san_entries]


def _parse_cert_date(date_str: str) -> datetime:
    """Parse a date string from ssl.SSLSocket.getpeercert().

    The ssl module returns dates like 'Jan  5 09:00:00 2025 GMT'.
    """
    return datetime.strptime(date_str, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=UTC)


def _get_fingerprint(der_cert: bytes) -> str:
    """Compute SHA-256 fingerprint of a DER-encoded certificate."""
    digest = hashlib.sha256(der_cert).hexdigest().upper()
    return ":".join(digest[i : i + 2] for i in range(0, len(digest), 2))


def _extract_cert_fields(cert_dict: dict, der_cert: bytes, host: str, port: int) -> CertInfo:
    """Extract all certificate fields from the parsed dict and DER bytes."""
    return CertInfo(
        host=host,
        port=port,
        subject=_format_dn(cert_dict.get("subject", ())),
        issuer=_format_dn(cert_dict.get("issuer", ())),
        serial_number=str(cert_dict.get("serialNumber", "")),
        sans=_extract_sans(cert_dict),
        not_before=_parse_cert_date(cert_dict["notBefore"]),
        not_after=_parse_cert_date(cert_dict["notAfter"]),
        fingerprint_sha256=_get_fingerprint(der_cert),
    )


def scan_host(host: str, port: int = 443, timeout: float = 10.0) -> ScanResult:
    """Scan a single host and return certificate info.

    Opens a TLS connection, retrieves the peer certificate, and extracts
    all relevant fields. Handles errors gracefully — returns a ScanError
    on failure instead of raising.

    Args:
        host: Hostname or IP to connect to.
        port: TCP port (default 443).
        timeout: Connection timeout in seconds.

    Returns:
        CertInfo on success, ScanError on failure.
    """
    ctx = ssl.create_default_context()

    try:
        with (
            socket.create_connection((host, port), timeout=timeout) as sock,
            ctx.wrap_socket(sock, server_hostname=host) as ssock,
        ):
            cert_dict = ssock.getpeercert()
            if cert_dict is None:
                return ScanError(host=host, port=port, error="No certificate presented")

            der_cert = ssock.getpeercert(binary_form=True)
            if der_cert is None:
                return ScanError(host=host, port=port, error="No DER certificate available")

            return _extract_cert_fields(cert_dict, der_cert, host, port)

    except ssl.SSLCertVerificationError:
        return _scan_host_no_verify(host, port, timeout)
    except TimeoutError:
        return ScanError(host=host, port=port, error=f"Connection timed out after {timeout}s")
    except ConnectionRefusedError:
        return ScanError(host=host, port=port, error="Connection refused")
    except OSError as exc:
        return ScanError(host=host, port=port, error=str(exc))


def _scan_host_no_verify(host: str, port: int, timeout: float) -> ScanResult:
    """Scan a host with certificate verification disabled (for self-signed certs).

    When the initial verified scan fails (e.g., hostname mismatch, self-signed),
    we retry without verification to still extract certificate details.
    """
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        with (
            socket.create_connection((host, port), timeout=timeout) as sock,
            ctx.wrap_socket(sock, server_hostname=host) as ssock,
        ):
            # With CERT_NONE, getpeercert() returns empty dict
            # but getpeercert(binary_form=True) still works
            der_cert = ssock.getpeercert(binary_form=True)
            if der_cert is None:
                return ScanError(
                    host=host, port=port, error="No certificate presented (unverified)"
                )

            fingerprint = _get_fingerprint(der_cert)

            # Write DER cert to a temp file and decode it via CPython internal API
            try:
                tmp = pathlib.Path(tempfile.mktemp(suffix=".der"))  # noqa: S306
                tmp.write_bytes(der_cert)
                cert_dict = ssl._ssl._test_decode_cert(str(tmp))  # type: ignore[attr-defined]
                tmp.unlink(missing_ok=True)

                result = _extract_cert_fields(cert_dict, der_cert, host, port)
                result.error = "Certificate verification failed (self-signed or untrusted CA)"
                return result
            except Exception:
                # If we can't decode, return what we have (just fingerprint)
                return CertInfo(
                    host=host,
                    port=port,
                    subject="(unverified)",
                    issuer="(unknown)",
                    serial_number="(unknown)",
                    sans=[],
                    not_before=datetime.now(UTC),
                    not_after=datetime.now(UTC),
                    fingerprint_sha256=fingerprint,
                    error="Certificate verification failed; limited info available",
                )

    except OSError as exc:
        return ScanError(host=host, port=port, error=f"Unverified scan failed: {exc}")


async def scan_host_async(host: str, port: int = 443, timeout: float = 10.0) -> ScanResult:
    """Async wrapper around scan_host — runs the blocking TLS scan in a thread."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, scan_host, host, port, timeout)


async def scan_hosts(
    hosts_ports: list[tuple[str, int]],
    timeout: float = 10.0,
    max_concurrent: int = 20,
) -> list[ScanResult]:
    """Scan multiple hosts concurrently.

    Args:
        hosts_ports: List of (host, port) tuples to scan.
        timeout: Per-host connection timeout.
        max_concurrent: Maximum number of concurrent scans.

    Returns:
        List of ScanResult (CertInfo or ScanError) for each host.
    """
    semaphore = asyncio.Semaphore(max_concurrent)

    async def _bounded_scan(host: str, port: int) -> ScanResult:
        async with semaphore:
            return await scan_host_async(host, port, timeout)

    tasks = [_bounded_scan(host, port) for host, port in hosts_ports]
    return list(await asyncio.gather(*tasks))


def check_expiry(host: str, port: int = 443, warn_days: int = 30) -> tuple[ScanResult, str]:
    """Scan a host and check certificate expiry.

    Args:
        host: Hostname to check.
        port: TCP port.
        warn_days: Number of days before expiry to warn.

    Returns:
        Tuple of (scan_result, status_string) where status is one of:
        "OK", "WARNING", "EXPIRED", or "ERROR".
    """
    result = scan_host(host, port)

    if isinstance(result, ScanError):
        return result, "ERROR"

    if result.is_expired:
        return result, "EXPIRED"

    if result.days_until_expiry <= warn_days:
        return result, "WARNING"

    return result, "OK"
