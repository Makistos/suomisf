#!/usr/bin/env python3
"""
SuomiSF API Performance Benchmark Runner

Standalone tool for measuring and tracking API performance.
Run after tests pass and changes are committed to git.

Usage:
    python -m tests.benchmark.benchmark_runner [options]

Options:
    --iterations N      Number of iterations per endpoint (default: 10)
    --warmup N          Warmup iterations before measuring (default: 2)
    --endpoints FILE    JSON file with endpoints to test (default: all)
    --output DIR        Output directory for results
    --compare HASH      Compare against baseline git hash
    --verbose           Show detailed output
"""

import argparse
import json
import os
import subprocess
import sys
import time
import statistics
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    import requests
except ImportError:
    print("Error: requests library required. Install with: pip install requests")
    sys.exit(1)


@dataclass
class EndpointResult:
    """Result for a single endpoint benchmark."""
    endpoint: str
    method: str
    iterations: int
    min_ms: float
    max_ms: float
    avg_ms: float
    median_ms: float
    p95_ms: float
    p99_ms: float
    std_dev_ms: float
    errors: int
    error_messages: List[str]


@dataclass
class BenchmarkResult:
    """Complete benchmark run result."""
    git_hash: str
    git_branch: str
    timestamp: str
    iterations: int
    warmup: int
    base_url: str
    total_duration_seconds: float
    endpoints: Dict[str, Any]


class BenchmarkRunner:
    """Runs performance benchmarks against the API."""

    # Default endpoints to benchmark (GET requests only for now)
    DEFAULT_ENDPOINTS = [
        # High-traffic endpoints
        ("GET", "/api/frontpagedata"),
        ("GET", "/api/genres"),
        ("GET", "/api/countries"),
        ("GET", "/api/roles/"),

        # Latest endpoints
        ("GET", "/api/latest/works/10"),
        ("GET", "/api/latest/editions/10"),
        ("GET", "/api/latest/people/10"),
        ("GET", "/api/latest/shorts/10"),
        ("GET", "/api/latest/covers/10"),

        # Statistics endpoints (typically expensive)
        ("GET", "/api/stats/genrecounts"),
        ("GET", "/api/stats/personcounts"),
        ("GET", "/api/stats/publishercounts"),
        ("GET", "/api/stats/worksbyyear"),
        ("GET", "/api/stats/nationalitycounts"),
        ("GET", "/api/stats/misc"),

        # Filter endpoints
        ("GET", "/api/filter/people/aa"),
        ("GET", "/api/filter/tags/sf"),
        ("GET", "/api/filter/publishers/aa"),

        # List endpoints
        ("GET", "/api/magazines"),
        ("GET", "/api/awards"),
        ("GET", "/api/tags"),
        ("GET", "/api/publishers"),
        ("GET", "/api/bookseries"),
        ("GET", "/api/pubseries"),

        # Type endpoints
        ("GET", "/api/worktypes"),
        ("GET", "/api/shorttypes"),
        ("GET", "/api/magazinetypes"),
        ("GET", "/api/bindings"),
    ]

    def __init__(
        self,
        base_url: str = "http://localhost:5000",
        iterations: int = 10,
        warmup: int = 2,
        verbose: bool = False
    ):
        self.base_url = base_url.rstrip('/')
        self.iterations = iterations
        self.warmup = warmup
        self.verbose = verbose
        self.session = requests.Session()

    def get_git_info(self) -> tuple:
        """Get current git hash and branch."""
        try:
            hash_result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                capture_output=True, text=True, check=True
            )
            git_hash = hash_result.stdout.strip()

            branch_result = subprocess.run(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                capture_output=True, text=True, check=True
            )
            git_branch = branch_result.stdout.strip()

            return git_hash, git_branch
        except Exception:
            return 'unknown', 'unknown'

    def benchmark_endpoint(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None
    ) -> EndpointResult:
        """Benchmark a single endpoint."""
        url = urljoin(self.base_url, endpoint)
        times: List[float] = []
        errors: List[str] = []

        # Warmup
        for _ in range(self.warmup):
            try:
                if method.upper() == 'GET':
                    self.session.get(url, timeout=30)
                elif method.upper() == 'POST':
                    self.session.post(url, json=data, timeout=30)
            except Exception:
                pass  # Ignore warmup errors

        # Actual measurements
        for i in range(self.iterations):
            try:
                start = time.perf_counter()

                if method.upper() == 'GET':
                    response = self.session.get(url, timeout=30)
                elif method.upper() == 'POST':
                    response = self.session.post(url, json=data, timeout=30)
                else:
                    errors.append(f"Unsupported method: {method}")
                    continue

                end = time.perf_counter()

                if response.status_code >= 400:
                    errors.append(f"HTTP {response.status_code}")
                else:
                    times.append((end - start) * 1000)  # Convert to ms

            except requests.Timeout:
                errors.append("Timeout")
            except requests.RequestException as e:
                errors.append(str(e))

            if self.verbose:
                status = "OK" if times and len(times) > i else "ERR"
                print(f"  [{i+1}/{self.iterations}] {status}")

        # Calculate statistics
        if times:
            sorted_times = sorted(times)
            p95_idx = int(len(sorted_times) * 0.95)
            p99_idx = int(len(sorted_times) * 0.99)

            return EndpointResult(
                endpoint=endpoint,
                method=method,
                iterations=len(times),
                min_ms=round(min(times), 2),
                max_ms=round(max(times), 2),
                avg_ms=round(statistics.mean(times), 2),
                median_ms=round(statistics.median(times), 2),
                p95_ms=round(sorted_times[min(p95_idx, len(sorted_times)-1)], 2),
                p99_ms=round(sorted_times[min(p99_idx, len(sorted_times)-1)], 2),
                std_dev_ms=round(statistics.stdev(times), 2) if len(times) > 1 else 0,
                errors=len(errors),
                error_messages=errors[:5]  # Keep first 5 error messages
            )
        else:
            return EndpointResult(
                endpoint=endpoint,
                method=method,
                iterations=0,
                min_ms=0, max_ms=0, avg_ms=0, median_ms=0,
                p95_ms=0, p99_ms=0, std_dev_ms=0,
                errors=len(errors),
                error_messages=errors[:5]
            )

    def run(
        self,
        endpoints: Optional[List[tuple]] = None
    ) -> BenchmarkResult:
        """Run complete benchmark suite."""
        endpoints = endpoints or self.DEFAULT_ENDPOINTS
        git_hash, git_branch = self.get_git_info()

        print("=" * 60)
        print("SuomiSF API Performance Benchmark")
        print("=" * 60)
        print(f"Base URL:   {self.base_url}")
        print(f"Git Hash:   {git_hash[:8]}")
        print(f"Git Branch: {git_branch}")
        print(f"Iterations: {self.iterations}")
        print(f"Warmup:     {self.warmup}")
        print(f"Endpoints:  {len(endpoints)}")
        print("=" * 60)
        print()

        start_time = time.time()
        results = {}

        for i, (method, endpoint) in enumerate(endpoints, 1):
            print(f"[{i}/{len(endpoints)}] {method} {endpoint}...", end=" ", flush=True)

            result = self.benchmark_endpoint(method, endpoint)

            if result.iterations > 0:
                print(f"avg={result.avg_ms:.1f}ms, p95={result.p95_ms:.1f}ms")
            else:
                print(f"FAILED ({result.errors} errors)")

            key = f"{method} {endpoint}"
            results[key] = asdict(result)

        total_duration = time.time() - start_time

        print()
        print("=" * 60)
        print(f"Benchmark complete in {total_duration:.1f}s")
        print("=" * 60)

        return BenchmarkResult(
            git_hash=git_hash,
            git_branch=git_branch,
            timestamp=datetime.now(timezone.utc).isoformat(),
            iterations=self.iterations,
            warmup=self.warmup,
            base_url=self.base_url,
            total_duration_seconds=round(total_duration, 2),
            endpoints=results
        )

    def save_result(
        self,
        result: BenchmarkResult,
        output_dir: Optional[str] = None
    ) -> str:
        """Save benchmark result to file."""
        output_dir = output_dir or os.path.join(
            os.path.dirname(__file__), 'results'
        )
        os.makedirs(output_dir, exist_ok=True)

        # Generate filename
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        short_hash = result.git_hash[:8]
        filename = f"benchmark_{short_hash}_{timestamp}.json"
        filepath = os.path.join(output_dir, filename)

        # Save result
        with open(filepath, 'w') as f:
            json.dump(asdict(result), f, indent=2)

        print(f"Results saved to: {filepath}")

        # Update best results
        self.update_best_results(result, output_dir)

        return filepath

    def update_best_results(
        self,
        result: BenchmarkResult,
        output_dir: str
    ):
        """Update best results tracking file."""
        best_path = os.path.join(output_dir, '..', 'best_results.json')

        # Load existing best results
        if os.path.exists(best_path):
            with open(best_path, 'r') as f:
                best_results = json.load(f)
        else:
            best_results = {}

        # Update with new bests
        improvements = []
        for key, endpoint_result in result.endpoints.items():
            if endpoint_result['iterations'] == 0:
                continue  # Skip failed endpoints

            current_avg = endpoint_result['avg_ms']

            if key not in best_results or current_avg < best_results[key]['best_avg_ms']:
                old_best = best_results.get(key, {}).get('best_avg_ms')
                best_results[key] = {
                    'best_avg_ms': current_avg,
                    'git_hash': result.git_hash,
                    'timestamp': result.timestamp
                }

                if old_best:
                    improvement = ((old_best - current_avg) / old_best) * 100
                    improvements.append((key, improvement, old_best, current_avg))

        # Save updated best results
        with open(best_path, 'w') as f:
            json.dump(best_results, f, indent=2)

        # Report improvements
        if improvements:
            print()
            print("New best times achieved:")
            for key, improvement, old, new in improvements:
                print(f"  {key}: {old:.1f}ms -> {new:.1f}ms ({improvement:+.1f}%)")


def compare_results(
    baseline_path: str,
    current_path: str,
    threshold: float = 10.0
):
    """Compare two benchmark results."""
    with open(baseline_path, 'r') as f:
        baseline = json.load(f)
    with open(current_path, 'r') as f:
        current = json.load(f)

    print("=" * 60)
    print("Benchmark Comparison")
    print("=" * 60)
    print(f"Baseline: {baseline['git_hash'][:8]} ({baseline['timestamp']})")
    print(f"Current:  {current['git_hash'][:8]} ({current['timestamp']})")
    print("=" * 60)
    print()
    print(f"{'Endpoint':<45} {'Baseline':>10} {'Current':>10} {'Change':>10}")
    print("-" * 75)

    regressions = []
    improvements = []

    for key in baseline['endpoints']:
        if key not in current['endpoints']:
            continue

        base_avg = baseline['endpoints'][key]['avg_ms']
        curr_avg = current['endpoints'][key]['avg_ms']

        if base_avg == 0:
            continue

        change_pct = ((curr_avg - base_avg) / base_avg) * 100

        # Determine status
        if change_pct > threshold:
            status = "SLOWER"
            regressions.append((key, base_avg, curr_avg, change_pct))
        elif change_pct < -threshold:
            status = "FASTER"
            improvements.append((key, base_avg, curr_avg, change_pct))
        else:
            status = ""

        print(f"{key:<45} {base_avg:>8.1f}ms {curr_avg:>8.1f}ms {change_pct:>+8.1f}% {status}")

    print()
    print("=" * 60)
    print(f"Regressions (>{threshold}% slower): {len(regressions)}")
    print(f"Improvements (>{threshold}% faster): {len(improvements)}")
    print("=" * 60)

    return len(regressions) == 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='SuomiSF API Performance Benchmark Runner'
    )
    parser.add_argument(
        '--base-url', '-u',
        default=os.environ.get('TEST_API_URL', 'http://localhost:5000'),
        help='API base URL (default: http://localhost:5000)'
    )
    parser.add_argument(
        '--iterations', '-n',
        type=int, default=10,
        help='Number of iterations per endpoint (default: 10)'
    )
    parser.add_argument(
        '--warmup', '-w',
        type=int, default=2,
        help='Warmup iterations before measuring (default: 2)'
    )
    parser.add_argument(
        '--output', '-o',
        help='Output directory for results'
    )
    parser.add_argument(
        '--compare', '-c',
        help='Compare against baseline result file'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show detailed output'
    )

    args = parser.parse_args()

    runner = BenchmarkRunner(
        base_url=args.base_url,
        iterations=args.iterations,
        warmup=args.warmup,
        verbose=args.verbose
    )

    result = runner.run()
    result_path = runner.save_result(result, args.output)

    if args.compare:
        print()
        compare_results(args.compare, result_path)


if __name__ == '__main__':
    main()
