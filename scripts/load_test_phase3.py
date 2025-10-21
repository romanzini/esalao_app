"""
Load testing script for Phase 3 systems.

This script performs comprehensive load testing on all Phase 3 endpoints
including reporting, caching, and concurrent operations validation.
"""

import asyncio
import json
import random
import time
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Any
import statistics

import aiohttp
import asyncpg
from dataclasses import dataclass


@dataclass
class LoadTestConfig:
    """Configuration for load testing."""
    base_url: str = "http://localhost:8000"
    concurrent_users: int = 50
    test_duration_seconds: int = 300  # 5 minutes
    ramp_up_time: int = 30  # 30 seconds to reach max users
    admin_token: str = ""
    salon_owner_token: str = ""
    database_url: str = ""


@dataclass
class TestResult:
    """Result of a test operation."""
    endpoint: str
    method: str
    status_code: int
    response_time_ms: float
    success: bool
    error_message: str = ""
    cached: bool = False


class LoadTester:
    """Main load testing class."""

    def __init__(self, config: LoadTestConfig):
        self.config = config
        self.results: List[TestResult] = []
        self.start_time = None
        self.end_time = None

    async def setup_test_data(self):
        """Setup test data for load testing."""
        print("Setting up test data...")

        # Connect to database to create test data
        conn = await asyncpg.connect(self.config.database_url)

        try:
            # Create test salons if they don't exist
            await self._create_test_salons(conn)

            # Create test bookings for reporting
            await self._create_test_bookings(conn)

            # Create test policies
            await self._create_test_policies(conn)

        finally:
            await conn.close()

        print("Test data setup complete")

    async def _create_test_salons(self, conn):
        """Create test salons for load testing."""
        for i in range(5):
            await conn.execute("""
                INSERT INTO salons (name, email, phone, address, is_active, created_at, updated_at)
                VALUES ($1, $2, $3, $4, true, NOW(), NOW())
                ON CONFLICT (email) DO NOTHING
            """, f"Load Test Salon {i+1}", f"salon{i+1}@loadtest.com",
                f"(11) 9999-{i+1}000", f"Address {i+1}")

    async def _create_test_bookings(self, conn):
        """Create test bookings for reporting load testing."""
        # Create bookings for the last 30 days
        base_date = datetime.now() - timedelta(days=30)

        for day in range(30):
            current_date = base_date + timedelta(days=day)

            # Create 5-15 bookings per day
            for _ in range(random.randint(5, 15)):
                await conn.execute("""
                    INSERT INTO bookings (
                        client_id, professional_id, service_id, salon_id,
                        scheduled_at, status, service_price, created_at, updated_at
                    ) VALUES (1, 1, 1, 1, $1, $2, $3, NOW(), NOW())
                """, current_date,
                    random.choice(['completed', 'confirmed', 'cancelled']),
                    Decimal(str(random.uniform(50.0, 200.0))))

    async def _create_test_policies(self, conn):
        """Create test cancellation policies."""
        await conn.execute("""
            INSERT INTO cancellation_policies (
                salon_id, name, description, status, created_by, created_at, updated_at
            ) VALUES (1, 'Load Test Policy', 'Policy for load testing', 'active', 1, NOW(), NOW())
            ON CONFLICT DO NOTHING
        """)

    async def run_load_test(self):
        """Run the complete load test suite."""
        print(f"Starting load test with {self.config.concurrent_users} concurrent users for {self.config.test_duration_seconds}s")

        self.start_time = time.time()

        # Create test scenarios
        scenarios = [
            self._test_reporting_endpoints,
            self._test_audit_endpoints,
            self._test_policy_endpoints,
            self._test_no_show_endpoints,
            self._test_cache_performance,
        ]

        # Calculate users per scenario
        users_per_scenario = self.config.concurrent_users // len(scenarios)

        # Start concurrent testing
        tasks = []
        for scenario in scenarios:
            for _ in range(users_per_scenario):
                task = asyncio.create_task(self._run_scenario(scenario))
                tasks.append(task)

        # Wait for ramp-up time then let tests run
        await asyncio.sleep(self.config.ramp_up_time)

        # Wait for test duration
        await asyncio.sleep(self.config.test_duration_seconds - self.config.ramp_up_time)

        # Cancel remaining tasks
        for task in tasks:
            if not task.done():
                task.cancel()

        # Wait for cleanup
        await asyncio.gather(*tasks, return_exceptions=True)

        self.end_time = time.time()

        print("Load test completed")

    async def _run_scenario(self, scenario_func):
        """Run a specific test scenario."""
        async with aiohttp.ClientSession() as session:
            end_time = time.time() + self.config.test_duration_seconds

            while time.time() < end_time:
                try:
                    await scenario_func(session)

                    # Random delay between requests (0.1-2 seconds)
                    await asyncio.sleep(random.uniform(0.1, 2.0))

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    print(f"Error in scenario: {e}")

    async def _test_reporting_endpoints(self, session: aiohttp.ClientSession):
        """Test reporting endpoints under load."""
        endpoints = [
            ("/api/v1/reports/dashboard", {"salon_id": 1}),
            ("/api/v1/reports/professionals", {"salon_id": 1}),
            ("/api/v1/reports/services", {"salon_id": 1}),
            ("/api/v1/reports/revenue/trend", {"salon_id": 1, "aggregation": "daily"}),
            ("/api/v1/platform-reports/overview", {}),
            ("/api/v1/optimized-reports/dashboard", {"salon_id": 1}),
        ]

        endpoint, params = random.choice(endpoints)
        await self._make_request(session, "GET", endpoint, params=params, use_admin_token=True)

    async def _test_audit_endpoints(self, session: aiohttp.ClientSession):
        """Test audit endpoints under load."""
        endpoints = [
            ("/api/v1/audit/events", {"limit": 20}),
            ("/api/v1/audit/events/stats", {}),
            ("/api/v1/audit/events", {"event_type": "booking_created", "limit": 10}),
        ]

        endpoint, params = random.choice(endpoints)
        await self._make_request(session, "GET", endpoint, params=params, use_admin_token=True)

    async def _test_policy_endpoints(self, session: aiohttp.ClientSession):
        """Test policy endpoints under load."""
        endpoints = [
            ("/api/v1/cancellation-policies", {"salon_id": 1}),
            ("/api/v1/cancellation-policies/1", {}),
        ]

        endpoint, params = random.choice(endpoints)
        await self._make_request(session, "GET", endpoint, params=params, use_admin_token=True)

    async def _test_no_show_endpoints(self, session: aiohttp.ClientSession):
        """Test no-show endpoints under load."""
        endpoints = [
            ("/api/v1/no-show/config", {}),
            ("/api/v1/no-show/history", {"limit": 10}),
        ]

        endpoint, params = random.choice(endpoints)
        await self._make_request(session, "GET", endpoint, params=params, use_admin_token=True)

    async def _test_cache_performance(self, session: aiohttp.ClientSession):
        """Test cache performance specifically."""
        # Hit the same endpoint multiple times to test cache
        cache_endpoints = [
            ("/api/v1/optimized-reports/dashboard", {"salon_id": 1}),
            ("/api/v1/optimized-reports/booking-metrics", {"salon_id": 1}),
        ]

        endpoint, params = random.choice(cache_endpoints)

        # First request (cache miss)
        start_time = time.time()
        await self._make_request(session, "GET", endpoint, params=params, use_admin_token=True)
        first_response_time = (time.time() - start_time) * 1000

        # Second request (cache hit)
        start_time = time.time()
        await self._make_request(session, "GET", endpoint, params=params, use_admin_token=True)
        second_response_time = (time.time() - start_time) * 1000

        # Log cache performance
        if second_response_time < first_response_time * 0.5:  # 50% faster
            self.results.append(TestResult(
                endpoint=endpoint,
                method="GET",
                status_code=200,
                response_time_ms=second_response_time,
                success=True,
                cached=True
            ))

    async def _make_request(self, session: aiohttp.ClientSession, method: str,
                          endpoint: str, params: Dict = None, use_admin_token: bool = False):
        """Make HTTP request and record result."""
        url = f"{self.config.base_url}{endpoint}"

        headers = {}
        if use_admin_token:
            headers["Authorization"] = f"Bearer {self.config.admin_token}"

        start_time = time.time()

        try:
            async with session.request(method, url, params=params, headers=headers) as response:
                response_time = (time.time() - start_time) * 1000

                success = response.status < 400
                error_message = "" if success else f"HTTP {response.status}"

                result = TestResult(
                    endpoint=endpoint,
                    method=method,
                    status_code=response.status,
                    response_time_ms=response_time,
                    success=success,
                    error_message=error_message
                )

                self.results.append(result)

        except Exception as e:
            response_time = (time.time() - start_time) * 1000

            result = TestResult(
                endpoint=endpoint,
                method=method,
                status_code=0,
                response_time_ms=response_time,
                success=False,
                error_message=str(e)
            )

            self.results.append(result)

    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive load test report."""
        if not self.results:
            return {"error": "No test results available"}

        total_requests = len(self.results)
        successful_requests = sum(1 for r in self.results if r.success)
        failed_requests = total_requests - successful_requests

        # Response time statistics
        response_times = [r.response_time_ms for r in self.results if r.success]

        # Requests per second
        total_duration = self.end_time - self.start_time if self.end_time else 1
        rps = total_requests / total_duration

        # Group by endpoint
        endpoint_stats = {}
        for result in self.results:
            endpoint = result.endpoint
            if endpoint not in endpoint_stats:
                endpoint_stats[endpoint] = {
                    "total_requests": 0,
                    "successful_requests": 0,
                    "failed_requests": 0,
                    "response_times": [],
                    "cached_requests": 0
                }

            stats = endpoint_stats[endpoint]
            stats["total_requests"] += 1

            if result.success:
                stats["successful_requests"] += 1
                stats["response_times"].append(result.response_time_ms)
            else:
                stats["failed_requests"] += 1

            if result.cached:
                stats["cached_requests"] += 1

        # Calculate endpoint statistics
        for endpoint, stats in endpoint_stats.items():
            if stats["response_times"]:
                stats["avg_response_time"] = statistics.mean(stats["response_times"])
                stats["min_response_time"] = min(stats["response_times"])
                stats["max_response_time"] = max(stats["response_times"])
                stats["p95_response_time"] = statistics.quantiles(stats["response_times"], n=20)[18]  # 95th percentile
            else:
                stats["avg_response_time"] = 0
                stats["min_response_time"] = 0
                stats["max_response_time"] = 0
                stats["p95_response_time"] = 0

            stats["success_rate"] = (stats["successful_requests"] / stats["total_requests"]) * 100

        report = {
            "test_summary": {
                "total_duration_seconds": total_duration,
                "total_requests": total_requests,
                "successful_requests": successful_requests,
                "failed_requests": failed_requests,
                "success_rate_percent": (successful_requests / total_requests) * 100,
                "requests_per_second": rps,
                "concurrent_users": self.config.concurrent_users
            },
            "response_time_stats": {
                "avg_response_time_ms": statistics.mean(response_times) if response_times else 0,
                "min_response_time_ms": min(response_times) if response_times else 0,
                "max_response_time_ms": max(response_times) if response_times else 0,
                "p95_response_time_ms": statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 20 else 0,
                "p99_response_time_ms": statistics.quantiles(response_times, n=100)[98] if len(response_times) >= 100 else 0
            },
            "endpoint_performance": endpoint_stats,
            "cache_performance": {
                "total_cached_requests": sum(1 for r in self.results if r.cached),
                "cache_hit_rate": (sum(1 for r in self.results if r.cached) / total_requests) * 100,
                "avg_cached_response_time": statistics.mean([r.response_time_ms for r in self.results if r.cached and r.success]) if any(r.cached for r in self.results) else 0
            },
            "performance_targets": {
                "avg_response_time_target_ms": 500,
                "p95_response_time_target_ms": 1000,
                "success_rate_target_percent": 99.0,
                "cache_hit_rate_target_percent": 80.0
            },
            "test_config": {
                "concurrent_users": self.config.concurrent_users,
                "test_duration_seconds": self.config.test_duration_seconds,
                "ramp_up_time": self.config.ramp_up_time,
                "base_url": self.config.base_url
            }
        }

        return report


async def run_comprehensive_load_test():
    """Run comprehensive load test for Phase 3 systems."""
    config = LoadTestConfig(
        base_url="http://localhost:8000",
        concurrent_users=50,
        test_duration_seconds=300,  # 5 minutes
        admin_token="your_admin_token_here",  # Replace with actual token
        database_url="postgresql://user:pass@localhost/esalao_db"  # Replace with actual DB URL
    )

    tester = LoadTester(config)

    try:
        # Setup test data
        await tester.setup_test_data()

        # Run load test
        await tester.run_load_test()

        # Generate and save report
        report = tester.generate_report()

        # Save report to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"load_test_report_{timestamp}.json"

        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        print(f"Load test report saved to {report_file}")

        # Print summary
        print("\n" + "="*50)
        print("LOAD TEST SUMMARY")
        print("="*50)

        summary = report["test_summary"]
        print(f"Duration: {summary['total_duration_seconds']:.1f}s")
        print(f"Total Requests: {summary['total_requests']}")
        print(f"Success Rate: {summary['success_rate_percent']:.1f}%")
        print(f"Requests/Second: {summary['requests_per_second']:.1f}")

        response_stats = report["response_time_stats"]
        print(f"Avg Response Time: {response_stats['avg_response_time_ms']:.1f}ms")
        print(f"95th Percentile: {response_stats['p95_response_time_ms']:.1f}ms")

        cache_stats = report["cache_performance"]
        print(f"Cache Hit Rate: {cache_stats['cache_hit_rate']:.1f}%")

        return report

    except Exception as e:
        print(f"Load test failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(run_comprehensive_load_test())
