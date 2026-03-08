"""Tests for the certguard CLI."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from click.testing import CliRunner

from certguard.cli import cli
from certguard.scanner import CertInfo, ScanError


def _mock_cert(host: str = "example.com", port: int = 443, days: int = 90) -> CertInfo:
    """Create a mock CertInfo for testing."""
    return CertInfo(
        host=host,
        port=port,
        subject=f"commonName={host}",
        issuer="commonName=Test CA, organizationName=Test",
        serial_number="ABCDEF1234567890",
        sans=[host, f"www.{host}"],
        not_before=datetime(2024, 1, 1, tzinfo=UTC),
        not_after=datetime.now(UTC) + timedelta(days=days),
        fingerprint_sha256="AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99:AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99",
    )


def _mock_error(host: str = "bad.example.com", port: int = 443) -> ScanError:
    """Create a mock ScanError for testing."""
    return ScanError(host=host, port=port, error="Connection refused")


class TestScanCommand:
    """Tests for `certguard scan`."""

    def test_scan_success(self):
        runner = CliRunner()
        with patch("certguard.cli.scan_host", return_value=_mock_cert()):
            result = runner.invoke(cli, ["scan", "example.com"])
            assert result.exit_code == 0
            assert "example.com" in result.output
            assert "commonName=example.com" in result.output
            assert "Test CA" in result.output
            assert "AA:BB:CC" in result.output

    def test_scan_with_port(self):
        runner = CliRunner()
        with patch("certguard.cli.scan_host", return_value=_mock_cert(port=8443)):
            result = runner.invoke(cli, ["scan", "example.com", "--port", "8443"])
            assert result.exit_code == 0

    def test_scan_failure(self):
        runner = CliRunner()
        with patch("certguard.cli.scan_host", return_value=_mock_error()):
            result = runner.invoke(cli, ["scan", "bad.example.com"])
            assert result.exit_code == 1
            assert "Failed" in result.output or "Error" in result.output
            assert "Connection refused" in result.output

    def test_scan_no_args(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["scan"])
        assert result.exit_code != 0  # missing required argument


class TestScanRangeCommand:
    """Tests for `certguard scan-range`."""

    def test_scan_range_all_success(self):
        runner = CliRunner()
        mock_results = [_mock_cert("a.com"), _mock_cert("b.com")]
        with patch("certguard.cli.scan_hosts", return_value=mock_results):
            result = runner.invoke(cli, ["scan-range", "a.com", "b.com"])
            assert result.exit_code == 0
            assert "a.com" in result.output
            assert "b.com" in result.output
            assert "2 succeeded, 0 failed" in result.output

    def test_scan_range_mixed(self):
        runner = CliRunner()
        mock_results = [_mock_cert("good.com"), _mock_error("bad.com")]
        with patch("certguard.cli.scan_hosts", return_value=mock_results):
            result = runner.invoke(cli, ["scan-range", "good.com", "bad.com"])
            assert result.exit_code == 1  # failures present
            assert "1 succeeded, 1 failed" in result.output

    def test_scan_range_no_args(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["scan-range"])
        assert result.exit_code != 0


class TestCheckCommand:
    """Tests for `certguard check`."""

    def test_check_ok(self):
        runner = CliRunner()
        with patch("certguard.cli.check_expiry", return_value=(_mock_cert(days=90), "OK")):
            result = runner.invoke(cli, ["check", "example.com"])
            assert result.exit_code == 0
            assert "OK" in result.output

    def test_check_warning(self):
        runner = CliRunner()
        cert = _mock_cert(days=15)
        with patch("certguard.cli.check_expiry", return_value=(cert, "WARNING")):
            result = runner.invoke(cli, ["check", "example.com", "--warn-days", "30"])
            assert result.exit_code == 1
            assert "WARNING" in result.output

    def test_check_expired(self):
        runner = CliRunner()
        cert = _mock_cert(days=-5)
        with patch("certguard.cli.check_expiry", return_value=(cert, "EXPIRED")):
            result = runner.invoke(cli, ["check", "example.com"])
            assert result.exit_code == 2
            assert "EXPIRED" in result.output

    def test_check_error(self):
        runner = CliRunner()
        with patch("certguard.cli.check_expiry", return_value=(_mock_error(), "ERROR")):
            result = runner.invoke(cli, ["check", "bad.example.com"])
            assert result.exit_code == 2
            assert "ERROR" in result.output


class TestVersion:
    """Tests for --version flag."""

    def test_version(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "certguard" in result.output
        assert "0.2.0" in result.output
