"""Tests for the TLS certificate scanner — the core feature of certguard.

Tests real TLS connections to public hosts, error handling for unreachable
hosts, and the expiry-checking logic.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from unittest.mock import patch

from certguard.scanner import (
    CertInfo,
    ScanError,
    _extract_sans,
    _format_dn,
    _get_fingerprint,
    _parse_cert_date,
    check_expiry,
    scan_host,
    scan_host_async,
    scan_hosts,
)

# ── Unit tests for helper functions ─────────────────────────────────


class TestFormatDN:
    """Tests for _format_dn()."""

    def test_simple_dn(self):
        dn = ((("commonName", "example.com"),),)
        assert _format_dn(dn) == "commonName=example.com"

    def test_multi_rdn(self):
        dn = (
            (("countryName", "US"),),
            (("organizationName", "Example Inc"),),
            (("commonName", "example.com"),),
        )
        result = _format_dn(dn)
        assert "countryName=US" in result
        assert "organizationName=Example Inc" in result
        assert "commonName=example.com" in result

    def test_empty_dn(self):
        assert _format_dn(()) == ""


class TestExtractSANs:
    """Tests for _extract_sans()."""

    def test_with_sans(self):
        cert = {"subjectAltName": (("DNS", "example.com"), ("DNS", "www.example.com"))}
        assert _extract_sans(cert) == ["example.com", "www.example.com"]

    def test_no_sans(self):
        assert _extract_sans({}) == []

    def test_empty_sans(self):
        cert = {"subjectAltName": ()}
        assert _extract_sans(cert) == []


class TestParseCertDate:
    """Tests for _parse_cert_date()."""

    def test_parse_date(self):
        dt = _parse_cert_date("Jan  5 09:00:00 2025 GMT")
        assert dt.year == 2025
        assert dt.month == 1
        assert dt.day == 5
        assert dt.tzinfo == UTC

    def test_parse_date_with_single_digit_day(self):
        dt = _parse_cert_date("Mar  3 12:30:00 2026 GMT")
        assert dt.day == 3
        assert dt.month == 3


class TestGetFingerprint:
    """Tests for _get_fingerprint()."""

    def test_fingerprint_format(self):
        # Known SHA256 of empty bytes
        fp = _get_fingerprint(b"")
        # SHA256 of empty = e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
        assert fp.startswith("E3:B0:C4:42")
        assert len(fp) == 95  # 64 hex chars + 31 colons

    def test_fingerprint_deterministic(self):
        data = b"test certificate data"
        assert _get_fingerprint(data) == _get_fingerprint(data)


# ── CertInfo properties ─────────────────────────────────────────────


class TestCertInfoProperties:
    """Tests for CertInfo dataclass properties."""

    def _make_cert(self, days_from_now: int) -> CertInfo:
        """Create a CertInfo expiring N days from now."""
        from datetime import timedelta

        return CertInfo(
            host="test.example.com",
            port=443,
            subject="CN=test.example.com",
            issuer="CN=Test CA",
            serial_number="ABC123",
            sans=["test.example.com"],
            not_before=datetime(2020, 1, 1, tzinfo=UTC),
            not_after=datetime.now(UTC) + timedelta(days=days_from_now),
            fingerprint_sha256="AA:BB:CC",
        )

    def test_days_until_expiry_positive(self):
        cert = self._make_cert(90)
        assert 89 <= cert.days_until_expiry <= 91

    def test_days_until_expiry_negative(self):
        cert = self._make_cert(-10)
        assert cert.days_until_expiry < 0

    def test_is_expired_false(self):
        cert = self._make_cert(90)
        assert cert.is_expired is False

    def test_is_expired_true(self):
        cert = self._make_cert(-1)
        assert cert.is_expired is True


# ── Real TLS scanning tests ─────────────────────────────────────────


class TestScanHost:
    """Tests that scan real TLS hosts over the network."""

    def test_scan_google(self):
        """Scan google.com — should always have a valid cert."""
        result = scan_host("google.com", 443, timeout=15.0)
        assert isinstance(result, CertInfo)
        assert result.host == "google.com"
        assert result.port == 443
        assert "google" in result.subject.lower() or any(
            "google" in san.lower() for san in result.sans
        )
        assert result.issuer  # non-empty
        assert result.serial_number  # non-empty
        assert len(result.sans) > 0
        assert result.not_before < datetime.now(UTC)
        assert result.not_after > datetime.now(UTC)
        assert ":" in result.fingerprint_sha256  # colon-separated hex
        assert result.days_until_expiry > 0
        assert result.is_expired is False
        assert result.error is None

    def test_scan_github(self):
        """Scan github.com — another reliable public host."""
        result = scan_host("github.com", 443, timeout=15.0)
        assert isinstance(result, CertInfo)
        assert result.host == "github.com"
        assert len(result.sans) > 0
        assert result.not_after > datetime.now(UTC)

    def test_scan_connection_refused(self):
        """Scanning a port that's not listening should return ScanError."""
        # Port 1 is almost never listening
        result = scan_host("127.0.0.1", 1, timeout=3.0)
        assert isinstance(result, ScanError)
        assert result.host == "127.0.0.1"
        assert result.port == 1
        assert result.error  # non-empty error message

    def test_scan_invalid_host(self):
        """Scanning a non-existent host should return ScanError or CertInfo with error.

        Some DNS providers (e.g., Pi-hole, ISP) may resolve non-existent domains
        to a landing page, so the TLS handshake may succeed with a mismatched cert.
        We accept either a ScanError or a CertInfo with an error field set.
        """
        result = scan_host("this-host-does-not-exist-12345.example.invalid", 443, timeout=3.0)
        if isinstance(result, ScanError):
            assert result.error  # non-empty error message
        else:
            # Host resolved to something, but cert won't match — error should be set
            assert isinstance(result, CertInfo)
            assert result.error is not None

    def test_scan_timeout(self):
        """Scanning with a very short timeout on a slow/non-responsive port."""
        # Use a non-routable IP to trigger a timeout
        result = scan_host("192.0.2.1", 443, timeout=1.0)
        assert isinstance(result, ScanError)
        assert result.error  # should contain timeout or connection info

    def test_scan_custom_port(self):
        """Scanning with a non-standard port that isn't TLS should fail gracefully."""
        result = scan_host("google.com", 80, timeout=5.0)
        assert isinstance(result, ScanError)


class TestScanHostAsync:
    """Tests for the async wrapper."""

    def test_async_scan_google(self):
        """Async scan of google.com should return CertInfo."""
        result = asyncio.run(scan_host_async("google.com", 443, timeout=15.0))
        assert isinstance(result, CertInfo)
        assert result.host == "google.com"


class TestScanHosts:
    """Tests for concurrent multi-host scanning."""

    def test_scan_multiple_hosts(self):
        """Scan several hosts concurrently."""
        hosts = [
            ("google.com", 443),
            ("github.com", 443),
        ]
        results = asyncio.run(scan_hosts(hosts, timeout=15.0))
        assert len(results) == 2

        # Both should succeed
        for result in results:
            assert isinstance(result, CertInfo)

    def test_scan_mix_of_good_and_bad(self):
        """Scan a mix of valid and invalid targets."""
        hosts = [
            ("google.com", 443),
            ("127.0.0.1", 1),  # connection refused
        ]
        results = asyncio.run(scan_hosts(hosts, timeout=10.0))
        assert len(results) == 2

        # At least one success and one failure
        types = {type(r) for r in results}
        assert CertInfo in types
        assert ScanError in types

    def test_scan_empty_list(self):
        """Scanning an empty list should return an empty list."""
        results = asyncio.run(scan_hosts([]))
        assert results == []


# ── Expiry checking tests ───────────────────────────────────────────


class TestCheckExpiry:
    """Tests for the check_expiry() function."""

    def test_check_google_ok(self):
        """Google's cert should be OK (not expiring within 1 day)."""
        result, status = check_expiry("google.com", 443, warn_days=1)
        assert isinstance(result, CertInfo)
        assert status == "OK"

    def test_check_unreachable_host(self):
        """Unreachable host should return ERROR status."""
        result, status = check_expiry("127.0.0.1", 1, warn_days=30)
        assert isinstance(result, ScanError)
        assert status == "ERROR"

    def test_check_expiry_warning_with_mock(self):
        """Mock a cert expiring within the warning window."""
        from datetime import timedelta

        mock_cert = CertInfo(
            host="expiring.example.com",
            port=443,
            subject="CN=expiring.example.com",
            issuer="CN=Test CA",
            serial_number="123",
            sans=["expiring.example.com"],
            not_before=datetime(2020, 1, 1, tzinfo=UTC),
            not_after=datetime.now(UTC) + timedelta(days=10),
            fingerprint_sha256="AA:BB",
        )

        with patch("certguard.scanner.scan_host", return_value=mock_cert):
            result, status = check_expiry("expiring.example.com", 443, warn_days=30)
            assert status == "WARNING"
            assert isinstance(result, CertInfo)
            assert result.days_until_expiry <= 30

    def test_check_expiry_expired_with_mock(self):
        """Mock an already-expired cert."""
        from datetime import timedelta

        mock_cert = CertInfo(
            host="expired.example.com",
            port=443,
            subject="CN=expired.example.com",
            issuer="CN=Test CA",
            serial_number="456",
            sans=["expired.example.com"],
            not_before=datetime(2020, 1, 1, tzinfo=UTC),
            not_after=datetime.now(UTC) - timedelta(days=5),
            fingerprint_sha256="DD:EE",
        )

        with patch("certguard.scanner.scan_host", return_value=mock_cert):
            result, status = check_expiry("expired.example.com", 443, warn_days=30)
            assert status == "EXPIRED"
            assert isinstance(result, CertInfo)
            assert result.is_expired is True
