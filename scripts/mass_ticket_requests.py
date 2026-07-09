"""
Mass Ticket Reserve Load Test — Football Virtual Waiting Room

Sends approximately 1,000,000 ticket reserve (queue join) requests to the
deployed API Gateway endpoint using concurrent async HTTP calls.

Usage:
    python scripts/mass_ticket_requests.py                    # defaults: 1M requests, event 1001
    python scripts/mass_ticket_requests.py --total 500000     # custom total
    python scripts/mass_ticket_requests.py --concurrency 200  # custom concurrency
    python scripts/mass_ticket_requests.py --event 1002       # target different event

Prerequisites:
    pip install aiohttp

Architecture:
    - Uses asyncio + aiohttp for high-throughput async HTTP
    - Configurable concurrency via semaphore (default 150 concurrent)
    - Generates unique user IDs using counter + random suffix
    - Tracks success/failure/latency stats in real time
    - Prints periodic progress updates every 10,000 requests
    - Final summary with throughput, error rate, and percentile latencies
"""

from __future__ import annotations

import argparse
import asyncio
import random
import string
import sys
import time
from dataclasses import dataclass, field

# Try importing aiohttp — provide install instructions if missing
try:
    import aiohttp
except ImportError:
    print("=" * 60)
    print("ERROR: 'aiohttp' is required for the load test.")
    print("Install it with:  pip install aiohttp")
    print("=" * 60)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
API_BASE = "https://n20mxucrj4.execute-api.us-east-1.amazonaws.com/Prod"
JOIN_ENDPOINT = "/queue/join"

DEFAULT_TOTAL_REQUESTS = 1_000_000
DEFAULT_CONCURRENCY = 150
DEFAULT_EVENT_ID = "1001"
PROGRESS_INTERVAL = 10_000  # Print progress every N requests


# ---------------------------------------------------------------------------
# Stats Tracker
# ---------------------------------------------------------------------------
@dataclass
class Stats:
    """Thread-safe (asyncio-safe) statistics collector."""
    total_sent: int = 0
    success_count: int = 0
    error_count: int = 0
    duplicate_count: int = 0
    latencies: list[float] = field(default_factory=list)
    errors: dict[str, int] = field(default_factory=dict)
    start_time: float = 0.0

    def record_success(self, latency: float) -> None:
        self.total_sent += 1
        self.success_count += 1
        self.latencies.append(latency)

    def record_duplicate(self, latency: float) -> None:
        self.total_sent += 1
        self.duplicate_count += 1
        self.latencies.append(latency)

    def record_error(self, error_msg: str, latency: float) -> None:
        self.total_sent += 1
        self.error_count += 1
        self.latencies.append(latency)
        self.errors[error_msg] = self.errors.get(error_msg, 0) + 1

    def elapsed(self) -> float:
        return time.monotonic() - self.start_time

    def throughput(self) -> float:
        e = self.elapsed()
        return self.total_sent / e if e > 0 else 0

    def percentile(self, p: float) -> float:
        if not self.latencies:
            return 0.0
        sorted_lats = sorted(self.latencies)
        idx = int(len(sorted_lats) * p / 100)
        idx = min(idx, len(sorted_lats) - 1)
        return sorted_lats[idx]


# ---------------------------------------------------------------------------
# User ID Generator
# ---------------------------------------------------------------------------
def generate_user_id(index: int) -> str:
    """Generate a unique user ID with index + random suffix."""
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"LOAD-{index:08d}-{suffix}"


# ---------------------------------------------------------------------------
# Single Request
# ---------------------------------------------------------------------------
async def send_join_request(
    session: aiohttp.ClientSession,
    semaphore: asyncio.Semaphore,
    event_id: str,
    user_id: str,
    stats: Stats,
) -> None:
    """Send a single POST /queue/join request."""
    url = f"{API_BASE}{JOIN_ENDPOINT}"
    payload = {"eventId": event_id, "userId": user_id}

    async with semaphore:
        start = time.monotonic()
        try:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                latency = time.monotonic() - start
                body = await resp.json()

                # Parse API Gateway proxy response if needed
                if "body" in body and isinstance(body["body"], str):
                    import json
                    body = json.loads(body["body"])

                if resp.status == 201:
                    stats.record_success(latency)
                elif resp.status == 409 or "Already registered" in str(body.get("message", "")):
                    stats.record_duplicate(latency)
                else:
                    msg = body.get("message", f"HTTP {resp.status}")
                    stats.record_error(msg, latency)

        except asyncio.TimeoutError:
            latency = time.monotonic() - start
            stats.record_error("Timeout", latency)
        except aiohttp.ClientError as e:
            latency = time.monotonic() - start
            stats.record_error(f"ClientError: {type(e).__name__}", latency)
        except Exception as e:
            latency = time.monotonic() - start
            stats.record_error(f"Unexpected: {type(e).__name__}: {e}", latency)


# ---------------------------------------------------------------------------
# Progress Reporter
# ---------------------------------------------------------------------------
async def progress_reporter(stats: Stats, total: int) -> None:
    """Periodically report progress while the load test runs."""
    last_reported = 0
    while stats.total_sent < total:
        await asyncio.sleep(1)
        current = stats.total_sent
        if current - last_reported >= PROGRESS_INTERVAL:
            elapsed = stats.elapsed()
            pct = (current / total) * 100
            rps = stats.throughput()
            print(
                f"  📊 Progress: {current:>10,} / {total:,} ({pct:5.1f}%) "
                f"| ✅ {stats.success_count:,} ok | ❌ {stats.error_count:,} err "
                f"| 🔁 {stats.duplicate_count:,} dup | ⚡ {rps:,.0f} req/s "
                f"| ⏱️ {elapsed:.1f}s"
            )
            last_reported = current


# ---------------------------------------------------------------------------
# Main Load Test
# ---------------------------------------------------------------------------
async def run_load_test(total: int, concurrency: int, event_id: str) -> None:
    """Execute the full load test."""
    print("=" * 70)
    print("⚽ FOOTBALL VIRTUAL WAITING ROOM — MASS TICKET RESERVE LOAD TEST")
    print("=" * 70)
    print(f"  Target Endpoint : {API_BASE}{JOIN_ENDPOINT}")
    print(f"  Event ID        : {event_id}")
    print(f"  Total Requests  : {total:,}")
    print(f"  Concurrency     : {concurrency}")
    print(f"  Progress Interval: every {PROGRESS_INTERVAL:,} requests")
    print("-" * 70)
    print()

    stats = Stats()
    semaphore = asyncio.Semaphore(concurrency)

    # Use connection pooling for efficiency
    connector = aiohttp.TCPConnector(
        limit=concurrency,
        limit_per_host=concurrency,
        ttl_dns_cache=300,
        force_close=False,
        enable_cleanup_closed=True,
    )

    print(f"🚀 Starting load test at {time.strftime('%Y-%m-%d %H:%M:%S')}...")
    print()

    stats.start_time = time.monotonic()

    async with aiohttp.ClientSession(
        connector=connector,
        headers={"Content-Type": "application/json"},
    ) as session:

        # Start progress reporter
        reporter_task = asyncio.create_task(progress_reporter(stats, total))

        # Create all tasks in batches to avoid memory explosion
        BATCH_SIZE = 10_000  # Submit tasks in batches of 10K

        for batch_start in range(0, total, BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE, total)
            tasks = []
            for i in range(batch_start, batch_end):
                user_id = generate_user_id(i)
                task = asyncio.create_task(
                    send_join_request(session, semaphore, event_id, user_id, stats)
                )
                tasks.append(task)

            # Wait for this batch to complete before submitting next
            await asyncio.gather(*tasks, return_exceptions=True)

        # Cancel progress reporter
        reporter_task.cancel()
        try:
            await reporter_task
        except asyncio.CancelledError:
            pass

    # ---------------------------------------------------------------------------
    # Final Report
    # ---------------------------------------------------------------------------
    elapsed = stats.elapsed()
    print()
    print("=" * 70)
    print("📋 LOAD TEST COMPLETE — FINAL REPORT")
    print("=" * 70)
    print(f"  Duration         : {elapsed:,.1f} seconds ({elapsed/60:.1f} minutes)")
    print(f"  Total Sent       : {stats.total_sent:,}")
    print(f"  ✅ Successful    : {stats.success_count:,}")
    print(f"  🔁 Duplicates    : {stats.duplicate_count:,}")
    print(f"  ❌ Errors        : {stats.error_count:,}")
    print(f"  Error Rate       : {(stats.error_count / max(stats.total_sent, 1)) * 100:.2f}%")
    print(f"  Throughput       : {stats.throughput():,.0f} requests/second")
    print()

    if stats.latencies:
        print("  ⏱️ Latency Distribution:")
        print(f"     p50  : {stats.percentile(50)*1000:>8.1f} ms")
        print(f"     p90  : {stats.percentile(90)*1000:>8.1f} ms")
        print(f"     p95  : {stats.percentile(95)*1000:>8.1f} ms")
        print(f"     p99  : {stats.percentile(99)*1000:>8.1f} ms")
        print(f"     max  : {max(stats.latencies)*1000:>8.1f} ms")
        print(f"     min  : {min(stats.latencies)*1000:>8.1f} ms")
        avg_lat = sum(stats.latencies) / len(stats.latencies)
        print(f"     avg  : {avg_lat*1000:>8.1f} ms")
    print()

    if stats.errors:
        print("  🔍 Error Breakdown:")
        for err_msg, count in sorted(stats.errors.items(), key=lambda x: -x[1])[:10]:
            print(f"     {count:>8,}x  {err_msg}")
        print()

    print("=" * 70)
    print("✅ Load test finished.")
    print("=" * 70)


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Send ~1 million ticket reserve requests to the Football Virtual Waiting Room API.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/mass_ticket_requests.py                         # 1M requests, default settings
    python scripts/mass_ticket_requests.py --total 100000          # 100K requests
    python scripts/mass_ticket_requests.py --concurrency 300       # 300 concurrent connections
    python scripts/mass_ticket_requests.py --event 1002            # target event 1002
    python scripts/mass_ticket_requests.py --total 50000 --concurrency 50   # lighter test
        """,
    )
    parser.add_argument(
        "--total", type=int, default=DEFAULT_TOTAL_REQUESTS,
        help=f"Total number of requests to send (default: {DEFAULT_TOTAL_REQUESTS:,})"
    )
    parser.add_argument(
        "--concurrency", type=int, default=DEFAULT_CONCURRENCY,
        help=f"Max concurrent requests (default: {DEFAULT_CONCURRENCY})"
    )
    parser.add_argument(
        "--event", type=str, default=DEFAULT_EVENT_ID,
        help=f"Target event ID (default: {DEFAULT_EVENT_ID})"
    )

    args = parser.parse_args()

    print(f"\n{'⚽' * 35}\n")
    print(f"  Configuration:")
    print(f"    Total Requests  = {args.total:,}")
    print(f"    Concurrency     = {args.concurrency}")
    print(f"    Target Event    = {args.event}")
    print(f"\n{'⚽' * 35}\n")

    confirm = input("🟡 This will send a MASSIVE number of requests. Continue? (y/N): ").strip().lower()
    if confirm != "y":
        print("Cancelled.")
        sys.exit(0)

    # Run the async load test
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(run_load_test(args.total, args.concurrency, args.event))


if __name__ == "__main__":
    main()
