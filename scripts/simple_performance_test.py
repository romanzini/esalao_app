"""
Simple performance testing script for Phase 3 endpoints.

This script performs basic performance testing without external dependencies.
"""

import json
import time
import statistics
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Dict, List, Any
import requests
from dataclasses import dataclass


@dataclass
class PerformanceResult:
    """Result of a performance test."""
    endpoint: str
    response_time_ms: float
    status_code: int
    success: bool
    cached: bool = False
    error: str = ""


class SimplePerformanceTester:
    """Simple performance tester using requests."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results: List[PerformanceResult] = []
        self.admin_token = "test_admin_token"  # Replace with actual token

    def test_endpoint(self, endpoint: str, params: Dict = None, method: str = "GET") -> PerformanceResult:
        """Test a single endpoint and return performance result."""
        url = f"{self.base_url}{endpoint}"
        headers = {"Authorization": f"Bearer {self.admin_token}"}

        start_time = time.time()

        try:
            if method == "GET":
                response = requests.get(url, params=params, headers=headers, timeout=10)
            elif method == "POST":
                response = requests.post(url, json=params, headers=headers, timeout=10)
            else:
                raise ValueError(f"Unsupported method: {method}")

            response_time = (time.time() - start_time) * 1000

            return PerformanceResult(
                endpoint=endpoint,
                response_time_ms=response_time,
                status_code=response.status_code,
                success=response.status_code < 400
            )

        except Exception as e:
            response_time = (time.time() - start_time) * 1000

            return PerformanceResult(
                endpoint=endpoint,
                response_time_ms=response_time,
                status_code=0,
                success=False,
                error=str(e)
            )

    def test_cache_performance(self, endpoint: str, params: Dict = None) -> List[PerformanceResult]:
        """Test cache performance by making multiple requests."""
        results = []

        # First request (potential cache miss)
        result1 = self.test_endpoint(endpoint, params)
        results.append(result1)

        # Small delay
        time.sleep(0.1)

        # Second request (potential cache hit)
        result2 = self.test_endpoint(endpoint, params)
        result2.cached = result2.response_time_ms < result1.response_time_ms * 0.7  # 30% faster = cached
        results.append(result2)

        return results

    def run_concurrent_test(self, endpoint: str, params: Dict = None,
                          concurrent_users: int = 10, requests_per_user: int = 5) -> List[PerformanceResult]:
        """Run concurrent test on an endpoint."""
        results = []

        def worker():
            worker_results = []
            for _ in range(requests_per_user):
                result = self.test_endpoint(endpoint, params)
                worker_results.append(result)
                time.sleep(0.1)  # Small delay between requests
            return worker_results

        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(worker) for _ in range(concurrent_users)]

            for future in as_completed(futures):
                try:
                    worker_results = future.result()
                    results.extend(worker_results)
                except Exception as e:
                    print(f"Worker failed: {e}")

        return results

    def run_full_performance_suite(self) -> Dict[str, Any]:
        """Run full performance test suite."""
        print("Starting Phase 3 Performance Testing...")

        test_results = {}

        # Test 1: Basic endpoint response times
        print("\n1. Testing basic endpoint response times...")
        basic_endpoints = [
            ("/api/v1/reports/dashboard", {"salon_id": 1}),
            ("/api/v1/reports/professionals", {"salon_id": 1}),
            ("/api/v1/platform-reports/overview", {}),
            ("/api/v1/audit/events", {"limit": 20}),
            ("/api/v1/cancellation-policies", {"salon_id": 1}),
        ]

        basic_results = []
        for endpoint, params in basic_endpoints:
            result = self.test_endpoint(endpoint, params)
            basic_results.append(result)
            print(f"  {endpoint}: {result.response_time_ms:.1f}ms - {'✅' if result.success else '❌'}")

        test_results["basic_endpoints"] = basic_results

        # Test 2: Cache performance
        print("\n2. Testing cache performance...")
        cache_endpoints = [
            ("/api/v1/optimized-reports/dashboard", {"salon_id": 1}),
            ("/api/v1/optimized-reports/booking-metrics", {"salon_id": 1}),
        ]

        cache_results = []
        for endpoint, params in cache_endpoints:
            results = self.test_cache_performance(endpoint, params)
            cache_results.extend(results)

            if len(results) >= 2:
                first_time = results[0].response_time_ms
                second_time = results[1].response_time_ms
                improvement = ((first_time - second_time) / first_time) * 100
                cached = results[1].cached

                print(f"  {endpoint}:")
                print(f"    First request: {first_time:.1f}ms")
                print(f"    Second request: {second_time:.1f}ms ({improvement:+.1f}% {'[CACHED]' if cached else '[NOT CACHED]'})")

        test_results["cache_performance"] = cache_results

        # Test 3: Concurrent load
        print("\n3. Testing concurrent load...")
        concurrent_endpoints = [
            ("/api/v1/reports/dashboard", {"salon_id": 1}),
            ("/api/v1/optimized-reports/dashboard", {"salon_id": 1}),
        ]

        concurrent_results = {}
        for endpoint, params in concurrent_endpoints:
            print(f"  Testing {endpoint} with 10 concurrent users...")
            results = self.run_concurrent_test(endpoint, params, concurrent_users=10, requests_per_user=3)
            concurrent_results[endpoint] = results

            if results:
                response_times = [r.response_time_ms for r in results if r.success]
                success_rate = sum(1 for r in results if r.success) / len(results) * 100

                if response_times:
                    avg_time = statistics.mean(response_times)
                    max_time = max(response_times)
                    print(f"    {len(results)} requests, {success_rate:.1f}% success")
                    print(f"    Avg: {avg_time:.1f}ms, Max: {max_time:.1f}ms")

        test_results["concurrent_load"] = concurrent_results

        # Test 4: Database-heavy operations
        print("\n4. Testing database-heavy operations...")
        db_heavy_endpoints = [
            ("/api/v1/audit/events/stats", {}),
            ("/api/v1/reports/revenue/trend", {"salon_id": 1, "aggregation": "daily"}),
        ]

        db_results = []
        for endpoint, params in db_heavy_endpoints:
            result = self.test_endpoint(endpoint, params)
            db_results.append(result)
            print(f"  {endpoint}: {result.response_time_ms:.1f}ms - {'✅' if result.success else '❌'}")

        test_results["database_heavy"] = db_results

        return test_results

    def generate_performance_report(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        all_results = []

        # Collect all results
        for category, results in test_results.items():
            if isinstance(results, list):
                all_results.extend(results)
            elif isinstance(results, dict):
                for endpoint_results in results.values():
                    all_results.extend(endpoint_results)

        if not all_results:
            return {"error": "No test results to analyze"}

        # Calculate statistics
        successful_results = [r for r in all_results if r.success]
        response_times = [r.response_time_ms for r in successful_results]

        # Performance benchmarks
        performance_targets = {
            "avg_response_time_ms": 500,
            "p95_response_time_ms": 1000,
            "success_rate_percent": 99.0,
            "cache_improvement_percent": 50.0
        }

        # Calculate cache performance
        cached_results = [r for r in all_results if r.cached]
        cache_hit_rate = len(cached_results) / len(all_results) * 100 if all_results else 0

        # Generate report
        report = {
            "test_summary": {
                "total_requests": len(all_results),
                "successful_requests": len(successful_results),
                "success_rate_percent": len(successful_results) / len(all_results) * 100 if all_results else 0,
                "test_timestamp": datetime.now().isoformat()
            },
            "performance_metrics": {
                "avg_response_time_ms": statistics.mean(response_times) if response_times else 0,
                "min_response_time_ms": min(response_times) if response_times else 0,
                "max_response_time_ms": max(response_times) if response_times else 0,
                "p95_response_time_ms": statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 20 else 0,
                "p99_response_time_ms": statistics.quantiles(response_times, n=100)[98] if len(response_times) >= 100 else 0
            },
            "cache_performance": {
                "cache_hit_rate_percent": cache_hit_rate,
                "cached_requests": len(cached_results),
                "avg_cached_response_time_ms": statistics.mean([r.response_time_ms for r in cached_results]) if cached_results else 0
            },
            "performance_targets": performance_targets,
            "target_compliance": {
                "avg_response_time_ok": (statistics.mean(response_times) if response_times else float('inf')) <= performance_targets["avg_response_time_ms"],
                "success_rate_ok": (len(successful_results) / len(all_results) * 100 if all_results else 0) >= performance_targets["success_rate_percent"],
                "cache_performance_ok": cache_hit_rate >= 20.0  # At least some caching
            },
            "detailed_results": test_results
        }

        return report


def main():
    """Main function to run performance tests."""
    tester = SimplePerformanceTester()

    try:
        # Run tests
        test_results = tester.run_full_performance_suite()

        # Generate report
        report = tester.generate_performance_report(test_results)

        # Save report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"performance_test_report_{timestamp}.json"

        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        # Print summary
        print("\n" + "="*60)
        print("PHASE 3 PERFORMANCE TEST SUMMARY")
        print("="*60)

        summary = report["test_summary"]
        metrics = report["performance_metrics"]
        cache = report["cache_performance"]
        compliance = report["target_compliance"]

        print(f"Total Requests: {summary['total_requests']}")
        print(f"Success Rate: {summary['success_rate_percent']:.1f}%")
        print(f"Avg Response Time: {metrics['avg_response_time_ms']:.1f}ms")
        print(f"95th Percentile: {metrics['p95_response_time_ms']:.1f}ms")
        print(f"Cache Hit Rate: {cache['cache_hit_rate_percent']:.1f}%")

        print("\nTarget Compliance:")
        print(f"  Response Time: {'✅' if compliance['avg_response_time_ok'] else '❌'}")
        print(f"  Success Rate: {'✅' if compliance['success_rate_ok'] else '❌'}")
        print(f"  Cache Performance: {'✅' if compliance['cache_performance_ok'] else '❌'}")

        print(f"\nDetailed report saved to: {report_file}")

        return report

    except Exception as e:
        print(f"Performance test failed: {e}")
        return None


if __name__ == "__main__":
    main()
