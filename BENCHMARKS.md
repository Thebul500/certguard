# Performance Benchmarks

API endpoint performance benchmarks for certguard.

## Test Environment

- **OS**: Linux 6.17.0-14-generic
- **Python**: 3.12.3
- **CPU**: 4 cores
- **Server**: uvicorn (single worker, async)
- **Client**: httpx async with connection pooling
- **Date**: 2026-03-01

## Methodology

Each scenario runs a warmup phase (50 requests) followed by the measured requests.
Latency is measured client-side per request using `time.perf_counter()`.
Requests are issued concurrently using `asyncio.gather()` with a semaphore to
control concurrency level. All times are in milliseconds.

## Results Summary

| # | Scenario | Requests | Concurrency | Req/sec | p50 (ms) | p95 (ms) | p99 (ms) |
|---|----------|----------|-------------|---------|----------|----------|----------|
| 1 | `GET /health` | 2000 | 20 | 307.3 | 48.65 | 161.69 | 240.69 |
| 2 | `GET /ready` | 2000 | 20 | 393.9 | 37.06 | 119.99 | 195.72 |
| 3 | `GET /nonexistent` | 2000 | 20 | 398.8 | 35.76 | 123.62 | 174.74 |
| 4 | `GET /health` | 5000 | 50 | 327.0 | 106.19 | 420.32 | 629.75 |
| 5 | `GET /ready` | 5000 | 30 | 355.2 | 54.77 | 235.16 | 350.98 |

## Detailed Results

### Scenario 1: `GET /health`

**Health check endpoint — returns JSON with status, version, timestamp**

- **Requests**: 2000
- **Concurrency**: 20
- **Errors**: 0
- **Wall time**: 6.508s
- **Throughput**: 307.3 req/sec

| Metric | Value (ms) |
|--------|-----------|
| Min | 12.31 |
| Mean | 62.65 |
| p50 (median) | 48.65 |
| p95 | 161.69 |
| p99 | 240.69 |
| Max | 331.84 |
| Std Dev | 48.66 |

### Scenario 2: `GET /ready`

**Readiness probe — minimal JSON response for orchestrators**

- **Requests**: 2000
- **Concurrency**: 20
- **Errors**: 0
- **Wall time**: 5.077s
- **Throughput**: 393.9 req/sec

| Metric | Value (ms) |
|--------|-----------|
| Min | 8.85 |
| Mean | 48.84 |
| p50 (median) | 37.06 |
| p95 | 119.99 |
| p99 | 195.72 |
| Max | 276.73 |
| Std Dev | 38.79 |

### Scenario 3: `GET /nonexistent`

**404 Not Found — measures error response generation overhead**

- **Requests**: 2000
- **Concurrency**: 20
- **Errors**: 2000
- **Wall time**: 5.015s
- **Throughput**: 398.8 req/sec

| Metric | Value (ms) |
|--------|-----------|
| Min | 9.2 |
| Mean | 48.19 |
| p50 (median) | 35.76 |
| p95 | 123.62 |
| p99 | 174.74 |
| Max | 386.41 |
| Std Dev | 38.83 |

### Scenario 4: `GET /health`

**Health check under high concurrency — 50 concurrent connections**

- **Requests**: 5000
- **Concurrency**: 50
- **Errors**: 0
- **Wall time**: 15.289s
- **Throughput**: 327.0 req/sec

| Metric | Value (ms) |
|--------|-----------|
| Min | 9.31 |
| Mean | 148.46 |
| p50 (median) | 106.19 |
| p95 | 420.32 |
| p99 | 629.75 |
| Max | 962.28 |
| Std Dev | 134.9 |

### Scenario 5: `GET /ready`

**Sustained load on readiness probe — 5000 requests, 30 concurrent**

- **Requests**: 5000
- **Concurrency**: 30
- **Errors**: 0
- **Wall time**: 14.076s
- **Throughput**: 355.2 req/sec

| Metric | Value (ms) |
|--------|-----------|
| Min | 11.16 |
| Mean | 81.58 |
| p50 (median) | 54.77 |
| p95 | 235.16 |
| p99 | 350.98 |
| Max | 775.29 |
| Std Dev | 75.42 |

## Analysis

### Key Observations

1. **Health endpoint throughput**: 307.3 req/sec at 20 concurrency with p99 latency of 240.69ms.

2. **Readiness probe performance**: 393.9 req/sec — the minimal response keeps latency low (p50: 37.06ms).

3. **Error handling overhead**: 404 responses at 398.8 req/sec with p99 of 174.74ms, showing FastAPI's error handling adds minimal overhead.

4. **High concurrency behavior**: At 50 concurrent connections, throughput reaches 327.0 req/sec with p99 of 629.75ms.

### Performance Targets

Targets are for a single-worker uvicorn server. Production deployments with
multiple workers (e.g., `--workers 4`) would achieve proportionally higher throughput.

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Health check p99 < 500ms (c=20) | < 500ms | 240.69ms | PASS |
| Readiness probe p99 < 500ms (c=20) | < 500ms | 195.72ms | PASS |
| Throughput > 200 req/sec (single worker) | > 200 req/sec | 307.3 req/sec | PASS |
| Zero errors on valid endpoints | 0 errors | 0 errors | PASS |

### Reproducing

```bash
# From the project root, with the virtualenv activated:
python benchmarks/run_benchmarks.py
```

Results will be written to `BENCHMARKS.md` and `benchmarks/results.json`.
