"""API performance benchmarks for certguard.

Starts a uvicorn server, runs load tests against key endpoints,
and reports requests/sec with p50/p95/p99 latency.
"""

import asyncio
import json
import os
import signal
import socket
import statistics
import subprocess
import sys
import time

import httpx


def find_free_port() -> int:
    """Find a free TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def percentile(data: list[float], p: float) -> float:
    """Calculate the p-th percentile of a sorted list."""
    if not data:
        return 0.0
    k = (len(data) - 1) * (p / 100)
    f = int(k)
    c = f + 1
    if c >= len(data):
        return data[-1]
    return data[f] + (k - f) * (data[c] - data[f])


async def benchmark_endpoint(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    num_requests: int = 1000,
    concurrency: int = 10,
    payload: dict | None = None,
    description: str = "",
) -> dict:
    """Run a benchmark against a single endpoint."""
    latencies: list[float] = []
    errors = 0
    semaphore = asyncio.Semaphore(concurrency)

    async def make_request():
        nonlocal errors
        async with semaphore:
            start = time.perf_counter()
            try:
                if method == "GET":
                    resp = await client.get(url)
                elif method == "POST":
                    resp = await client.post(url, json=payload)
                else:
                    resp = await client.request(method, url)
                elapsed = (time.perf_counter() - start) * 1000  # ms
                latencies.append(elapsed)
                if resp.status_code >= 400:
                    errors += 1
            except Exception:
                errors += 1

    # Warmup: 50 requests
    warmup_tasks = [make_request() for _ in range(50)]
    await asyncio.gather(*warmup_tasks)
    latencies.clear()
    errors = 0

    # Actual benchmark
    wall_start = time.perf_counter()
    tasks = [make_request() for _ in range(num_requests)]
    await asyncio.gather(*tasks)
    wall_elapsed = time.perf_counter() - wall_start

    latencies.sort()
    rps = num_requests / wall_elapsed if wall_elapsed > 0 else 0

    return {
        "description": description,
        "method": method,
        "url": url,
        "num_requests": num_requests,
        "concurrency": concurrency,
        "errors": errors,
        "wall_time_sec": round(wall_elapsed, 3),
        "requests_per_sec": round(rps, 1),
        "latency_ms": {
            "min": round(min(latencies), 2) if latencies else 0,
            "p50": round(percentile(latencies, 50), 2),
            "p95": round(percentile(latencies, 95), 2),
            "p99": round(percentile(latencies, 99), 2),
            "max": round(max(latencies), 2) if latencies else 0,
            "mean": round(statistics.mean(latencies), 2) if latencies else 0,
            "stdev": round(statistics.stdev(latencies), 2) if len(latencies) > 1 else 0,
        },
    }


async def run_all_benchmarks(base_url: str) -> list[dict]:
    """Run all benchmark scenarios."""
    results = []

    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        # Scenario 1: Health check endpoint — lightweight JSON response
        print("  [1/5] GET /health — health check endpoint...")
        result = await benchmark_endpoint(
            client,
            "GET",
            "/health",
            num_requests=2000,
            concurrency=20,
            description="Health check endpoint — returns JSON with status, version, timestamp",
        )
        results.append(result)

        # Scenario 2: Readiness probe — minimal JSON response
        print("  [2/5] GET /ready — readiness probe...")
        result = await benchmark_endpoint(
            client,
            "GET",
            "/ready",
            num_requests=2000,
            concurrency=20,
            description="Readiness probe — minimal JSON response for orchestrators",
        )
        results.append(result)

        # Scenario 3: 404 Not Found — error handling path
        print("  [3/5] GET /nonexistent — 404 error handling...")
        result = await benchmark_endpoint(
            client,
            "GET",
            "/nonexistent",
            num_requests=2000,
            concurrency=20,
            description="404 Not Found — measures error response generation overhead",
        )
        results.append(result)

        # Scenario 4: High concurrency health check
        print("  [4/5] GET /health — high concurrency (50 concurrent)...")
        result = await benchmark_endpoint(
            client,
            "GET",
            "/health",
            num_requests=5000,
            concurrency=50,
            description="Health check under high concurrency — 50 concurrent connections",
        )
        results.append(result)

        # Scenario 5: Sustained load on readiness
        print("  [5/5] GET /ready — sustained load (5000 requests)...")
        result = await benchmark_endpoint(
            client,
            "GET",
            "/ready",
            num_requests=5000,
            concurrency=30,
            description="Sustained load on readiness probe — 5000 requests, 30 concurrent",
        )
        results.append(result)

    return results


def format_markdown(results: list[dict]) -> str:
    """Format benchmark results as Markdown."""
    lines = [
        "# Performance Benchmarks",
        "",
        "API endpoint performance benchmarks for certguard.",
        "",
        "## Test Environment",
        "",
    ]

    # Collect system info
    import platform

    lines.extend([
        f"- **OS**: {platform.system()} {platform.release()}",
        f"- **Python**: {platform.python_version()}",
        f"- **CPU**: {os.cpu_count()} cores",
        "- **Server**: uvicorn (single worker, async)",
        "- **Client**: httpx async with connection pooling",
        f"- **Date**: {time.strftime('%Y-%m-%d')}",
        "",
        "## Methodology",
        "",
        "Each scenario runs a warmup phase (50 requests) followed by the measured requests.",
        "Latency is measured client-side per request using `time.perf_counter()`.",
        "Requests are issued concurrently using `asyncio.gather()` with a semaphore to",
        "control concurrency level. All times are in milliseconds.",
        "",
        "## Results Summary",
        "",
        "| # | Scenario | Requests | Concurrency | Req/sec | p50 (ms) | p95 (ms) | p99 (ms) |",
        "|---|----------|----------|-------------|---------|----------|----------|----------|",
    ])

    for i, r in enumerate(results, 1):
        lat = r["latency_ms"]
        url = r["url"]
        lines.append(
            f"| {i} | `{r['method']} {url}` | {r['num_requests']} "
            f"| {r['concurrency']} | {r['requests_per_sec']} "
            f"| {lat['p50']} | {lat['p95']} | {lat['p99']} |"
        )

    lines.extend(["", "## Detailed Results", ""])

    for i, r in enumerate(results, 1):
        lat = r["latency_ms"]
        lines.extend([
            f"### Scenario {i}: `{r['method']} {r['url']}`",
            "",
            f"**{r['description']}**",
            "",
            f"- **Requests**: {r['num_requests']}",
            f"- **Concurrency**: {r['concurrency']}",
            f"- **Errors**: {r['errors']}",
            f"- **Wall time**: {r['wall_time_sec']}s",
            f"- **Throughput**: {r['requests_per_sec']} req/sec",
            "",
            "| Metric | Value (ms) |",
            "|--------|-----------|",
            f"| Min | {lat['min']} |",
            f"| Mean | {lat['mean']} |",
            f"| p50 (median) | {lat['p50']} |",
            f"| p95 | {lat['p95']} |",
            f"| p99 | {lat['p99']} |",
            f"| Max | {lat['max']} |",
            f"| Std Dev | {lat['stdev']} |",
            "",
        ])

    lines.extend([
        "## Analysis",
        "",
        "### Key Observations",
        "",
    ])

    # Generate observations from data
    health = results[0]
    ready = results[1]
    error = results[2]
    high_conc = results[3]

    lines.extend([
        f"1. **Health endpoint throughput**: {health['requests_per_sec']} req/sec at "
        f"{health['concurrency']} concurrency with p99 latency of "
        f"{health['latency_ms']['p99']}ms.",
        "",
        f"2. **Readiness probe performance**: {ready['requests_per_sec']} req/sec — "
        f"the minimal response keeps latency low (p50: {ready['latency_ms']['p50']}ms).",
        "",
        f"3. **Error handling overhead**: 404 responses at {error['requests_per_sec']} req/sec "
        f"with p99 of {error['latency_ms']['p99']}ms, showing FastAPI's error handling "
        "adds minimal overhead.",
        "",
        f"4. **High concurrency behavior**: At {high_conc['concurrency']} concurrent connections, "
        f"throughput reaches {high_conc['requests_per_sec']} req/sec with p99 of "
        f"{high_conc['latency_ms']['p99']}ms.",
        "",
        "### Performance Targets",
        "",
        "| Metric | Target | Status |",
        "|--------|--------|--------|",
    ])

    health_p99 = health["latency_ms"]["p99"]
    health_rps = health["requests_per_sec"]
    error_rate = sum(r["errors"] for r in results) / sum(r["num_requests"] for r in results) * 100

    lines.extend([
        f"| Health check p99 < 50ms | {health_p99}ms | "
        f"{'PASS' if health_p99 < 50 else 'REVIEW'} |",
        f"| Throughput > 500 req/sec | {health_rps} req/sec | "
        f"{'PASS' if health_rps > 500 else 'REVIEW'} |",
        f"| Error rate < 1% | {error_rate:.2f}% | "
        f"{'PASS' if error_rate < 1 else 'REVIEW'} |",
        "",
    ])

    return "\n".join(lines)


def main():
    port = find_free_port()
    base_url = f"http://127.0.0.1:{port}"

    print(f"Starting uvicorn on port {port}...")

    # Start server
    server_proc = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn",
            "certguard.app:app",
            "--host", "127.0.0.1",
            "--port", str(port),
            "--log-level", "warning",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait for server to be ready
    for _ in range(50):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                break
        except OSError:
            time.sleep(0.1)
    else:
        print("ERROR: Server failed to start")
        server_proc.kill()
        sys.exit(1)

    print(f"Server ready at {base_url}")
    print("Running benchmarks...\n")

    try:
        results = asyncio.run(run_all_benchmarks(base_url))

        # Write JSON results
        json_path = os.path.join(os.path.dirname(__file__), "results.json")
        with open(json_path, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nJSON results written to {json_path}")

        # Write Markdown report
        md_content = format_markdown(results)
        md_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "BENCHMARKS.md")
        with open(md_path, "w") as f:
            f.write(md_content)
        print(f"Markdown report written to {md_path}")

        # Print summary
        print("\n" + "=" * 70)
        print("BENCHMARK SUMMARY")
        print("=" * 70)
        for i, r in enumerate(results, 1):
            lat = r["latency_ms"]
            print(
                f"  {i}. {r['method']} {r['url']:20s} | "
                f"{r['requests_per_sec']:>8.1f} req/s | "
                f"p50={lat['p50']:>6.2f}ms | "
                f"p95={lat['p95']:>6.2f}ms | "
                f"p99={lat['p99']:>6.2f}ms"
            )
        print("=" * 70)

    finally:
        server_proc.send_signal(signal.SIGTERM)
        server_proc.wait(timeout=5)


if __name__ == "__main__":
    main()
