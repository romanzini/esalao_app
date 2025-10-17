"""
Locust load testing for eSalão Platform API.

This file defines load test scenarios for critical endpoints.
Run with: locust -f performance/locustfile.py --host=http://localhost:8000
"""

import random
from datetime import date, timedelta

from locust import HttpUser, between, task


class eSalaoUser(HttpUser):
    """
    Simulates a user interacting with the eSalão API.

    Performs typical user actions: browsing slots, creating bookings, viewing professionals.
    Wait time between tasks: 1-5 seconds (realistic user behavior).
    """

    wait_time = between(1, 5)

    def on_start(self):
        """
        Called when a simulated user starts.

        Creates an authenticated user session by registering and logging in.
        Stores the authentication token for subsequent requests.
        """
        # Register a new user (only if not exists)
        user_id = random.randint(10000, 99999)
        self.email = f"loadtest{user_id}@example.com"
        self.password = "TestPass123!"

        # Try to register
        register_response = self.client.post(
            "/v1/auth/register",
            json={
                "email": self.email,
                "password": self.password,
                "name": f"Load Test User {user_id}",
                "phone": f"+5511{user_id:08d}",
                "role": "CLIENT",
            },
            name="/v1/auth/register",
        )

        # Login to get token
        login_response = self.client.post(
            "/v1/auth/login",
            json={"email": self.email, "password": self.password},
            name="/v1/auth/login",
        )

        if login_response.status_code == 200:
            self.token = login_response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.token = None
            self.headers = {}

    @task(3)
    def get_available_slots(self):
        """
        Test GET /v1/scheduling/slots - Most frequently used endpoint.

        Weight: 3 (executed 3x more often than other tasks).
        Simulates users browsing available appointment slots.
        """
        today = date.today()
        future_date = today + timedelta(days=random.randint(1, 7))

        params = {
            "date": future_date.isoformat(),
            "professional_id": random.randint(1, 5),
            "service_id": random.randint(1, 10),
        }

        self.client.get(
            "/v1/scheduling/slots",
            params=params,
            headers=self.headers,
            name="/v1/scheduling/slots",
        )

    @task(1)
    def list_professionals(self):
        """
        Test GET /v1/professionals - Browse professionals.

        Weight: 1 (standard frequency).
        Simulates users browsing available professionals.
        """
        self.client.get(
            "/v1/professionals",
            headers=self.headers,
            name="/v1/professionals",
        )

    @task(1)
    def list_services(self):
        """
        Test GET /v1/services - Browse services.

        Weight: 1 (standard frequency).
        Simulates users browsing available services.
        """
        self.client.get(
            "/v1/services",
            headers=self.headers,
            name="/v1/services",
        )

    @task(1)
    def create_booking(self):
        """
        Test POST /v1/bookings - Create a booking.

        Weight: 1 (standard frequency).
        Simulates users creating bookings (write operation).

        Note: May fail if professional/service doesn't exist in test DB.
        """
        if not self.token:
            return

        today = date.today()
        future_date = today + timedelta(days=random.randint(1, 7))

        booking_data = {
            "professional_id": random.randint(1, 5),
            "service_id": random.randint(1, 10),
            "scheduled_time": f"{future_date.isoformat()}T{random.randint(9, 17):02d}:00:00Z",
        }

        self.client.post(
            "/v1/bookings",
            json=booking_data,
            headers=self.headers,
            name="/v1/bookings [POST]",
        )

    @task(1)
    def list_my_bookings(self):
        """
        Test GET /v1/bookings - List user bookings.

        Weight: 1 (standard frequency).
        Simulates users viewing their booking history.
        """
        if not self.token:
            return

        self.client.get(
            "/v1/bookings",
            headers=self.headers,
            name="/v1/bookings [GET]",
        )


class ReadOnlyUser(HttpUser):
    """
    Simulates a read-only user (browsing without authentication).

    Only performs read operations without creating bookings.
    Useful for testing public endpoints and caching behavior.
    """

    wait_time = between(1, 3)

    @task(4)
    def get_available_slots(self):
        """Browse available slots (unauthenticated)."""
        today = date.today()
        future_date = today + timedelta(days=random.randint(1, 7))

        params = {
            "date": future_date.isoformat(),
            "professional_id": random.randint(1, 5),
            "service_id": random.randint(1, 10),
        }

        self.client.get(
            "/v1/scheduling/slots",
            params=params,
            name="/v1/scheduling/slots [unauthenticated]",
        )

    @task(2)
    def list_professionals(self):
        """Browse professionals (unauthenticated)."""
        self.client.get(
            "/v1/professionals",
            name="/v1/professionals [unauthenticated]",
        )

    @task(2)
    def list_services(self):
        """Browse services (unauthenticated)."""
        self.client.get(
            "/v1/services",
            name="/v1/services [unauthenticated]",
        )
