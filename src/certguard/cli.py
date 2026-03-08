"""certguard CLI — scan TLS certificates from the command line.

Usage:
    certguard scan google.com
    certguard scan google.com --port 443
    certguard scan-range google.com github.com cloudflare.com
    certguard check google.com --warn-days 30
"""

from __future__ import annotations

import asyncio
import sys

import click

from . import __version__
from .scanner import CertInfo, ScanError, check_expiry, scan_host, scan_hosts


def _format_cert(info: CertInfo) -> str:
    """Format a CertInfo into a readable block."""
    lines = [
        f"  Host:        {info.host}:{info.port}",
        f"  Subject:     {info.subject}",
        f"  Issuer:      {info.issuer}",
        f"  Serial:      {info.serial_number}",
        f"  SANs:        {', '.join(info.sans) if info.sans else '(none)'}",
        f"  Valid from:  {info.not_before.strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"  Valid until: {info.not_after.strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"  Expires in:  {info.days_until_expiry} days",
        f"  Fingerprint: {info.fingerprint_sha256}",
    ]
    if info.error:
        lines.append(f"  Warning:     {info.error}")
    return "\n".join(lines)


def _format_error(err: ScanError) -> str:
    """Format a ScanError into a readable block."""
    return f"  Host:  {err.host}:{err.port}\n  Error: {err.error}"


@click.group()
@click.version_option(version=__version__, prog_name="certguard")
def cli():
    """certguard -- TLS certificate scanner and expiry checker."""


@cli.command()
@click.argument("host")
@click.option("--port", "-p", default=443, type=int, help="TCP port to connect to.")
@click.option("--timeout", "-t", default=10.0, type=float, help="Connection timeout in seconds.")
def scan(host: str, port: int, timeout: float):
    """Scan a single host and display certificate details."""
    click.echo(f"Scanning {host}:{port} ...")
    result = scan_host(host, port, timeout)

    if isinstance(result, ScanError):
        click.secho(f"\nFailed to scan {host}:{port}", fg="red", bold=True)
        click.echo(_format_error(result))
        sys.exit(1)

    click.secho(f"\nCertificate for {host}:{port}", fg="green", bold=True)
    click.echo(_format_cert(result))


@cli.command("scan-range")
@click.argument("hosts", nargs=-1, required=True)
@click.option("--port", "-p", default=443, type=int, help="TCP port for all hosts.")
@click.option("--timeout", "-t", default=10.0, type=float, help="Connection timeout in seconds.")
def scan_range(hosts: tuple[str, ...], port: int, timeout: float):
    """Scan multiple hosts and display certificate details."""
    hosts_ports = [(h, port) for h in hosts]
    click.echo(f"Scanning {len(hosts_ports)} host(s) ...")

    results = asyncio.run(scan_hosts(hosts_ports, timeout=timeout))

    successes = 0
    failures = 0

    for result in results:
        click.echo("")
        if isinstance(result, ScanError):
            click.secho(f"FAILED: {result.host}:{result.port}", fg="red", bold=True)
            click.echo(_format_error(result))
            failures += 1
        else:
            click.secho(f"OK: {result.host}:{result.port}", fg="green", bold=True)
            click.echo(_format_cert(result))
            successes += 1

    click.echo(f"\n--- Summary: {successes} succeeded, {failures} failed ---")

    if failures > 0:
        sys.exit(1)


@cli.command()
@click.argument("host")
@click.option("--port", "-p", default=443, type=int, help="TCP port to connect to.")
@click.option("--warn-days", "-w", default=30, type=int, help="Warn if cert expires within N days.")
def check(host: str, port: int, warn_days: int):
    """Check if a host's certificate is expiring soon."""
    click.echo(f"Checking {host}:{port} (warn if < {warn_days} days) ...")
    result, status = check_expiry(host, port, warn_days)

    click.echo("")

    if status == "ERROR":
        click.secho(f"ERROR: Could not scan {host}:{port}", fg="red", bold=True)
        if isinstance(result, ScanError):
            click.echo(_format_error(result))
        sys.exit(2)

    if not isinstance(result, CertInfo):
        click.secho("Unexpected result type", fg="red")
        sys.exit(2)

    if status == "EXPIRED":
        click.secho(f"EXPIRED: Certificate for {host}:{port} has expired!", fg="red", bold=True)
        click.echo(_format_cert(result))
        sys.exit(2)

    if status == "WARNING":
        click.secho(
            f"WARNING: Certificate for {host}:{port} expires in {result.days_until_expiry} days",
            fg="yellow",
            bold=True,
        )
        click.echo(_format_cert(result))
        sys.exit(1)

    click.secho(
        f"OK: Certificate for {host}:{port} expires in {result.days_until_expiry} days",
        fg="green",
        bold=True,
    )
    click.echo(_format_cert(result))
