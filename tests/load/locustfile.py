"""Locust load testing for CareerDEX API (Issue #96).

Run::

    # Start the API server first:
    uv run poe dev

    # Then run load tests (headless):
    uv run locust -f tests/load/locustfile.py --headless -u 10 -r 2 -t 30s

    # Or with the web UI:
    uv run locust -f tests/load/locustfile.py

    # Or via poe:
    uv run poe loadtest
"""

from __future__ import annotations

from locust import HttpUser, between, tag, task


class HealthCheckUser(HttpUser):
    """Simulates health probe traffic (Kubernetes liveness/readiness)."""

    wait_time = between(0.5, 1.5)
    weight = 3

    @tag("health")
    @task(3)
    def health(self) -> None:
        self.client.get("/health")

    @tag("health")
    @task(2)
    def ready(self) -> None:
        self.client.get("/ready")

    @tag("health")
    @task(1)
    def startup(self) -> None:
        self.client.get("/startup")


class CoreEndpointUser(HttpUser):
    """Simulates traffic to core endpoints."""

    wait_time = between(1, 3)
    weight = 2

    @tag("core")
    @task(3)
    def root(self) -> None:
        self.client.get("/")

    @tag("core")
    @task(2)
    def echo(self) -> None:
        self.client.post(
            "/echo",
            json={"message": "load test ping"},
        )

    @tag("core")
    @task(1)
    def metrics(self) -> None:
        self.client.get("/metrics")


class CareerDEXAPIUser(HttpUser):
    """Simulates realistic CareerDEX API traffic."""

    wait_time = between(1, 5)
    weight = 5

    @tag("careerdex", "salary")
    @task(3)
    def salary_prediction(self) -> None:
        self.client.post(
            "/api/v1/careerdex/salary/prediction",
            json={
                "title": "Data Engineer",
                "location": "San Francisco",
                "seniority": "senior",
                "skills": ["python", "spark", "sql"],
                "years_experience": 5,
            },
        )

    @tag("careerdex", "insights")
    @task(2)
    def skill_gaps(self) -> None:
        self.client.get(
            "/api/v1/careerdex/insights/skill-gaps",
            params={
                "target_role": "data engineer",
                "user_skills": "python,sql",
                "top_k": 5,
            },
        )

    @tag("careerdex", "market")
    @task(2)
    def career_paths(self) -> None:
        self.client.get(
            "/api/v1/careerdex/market/careers",
            params={"role": "data engineer", "max_paths": 3},
        )

    @tag("careerdex", "insights")
    @task(1)
    def career_health(self) -> None:
        self.client.get(
            "/api/v1/careerdex/insights/career-health",
            params={
                "days_since_login": 5,
                "profile_completeness": 0.85,
            },
        )

    @tag("careerdex", "market")
    @task(2)
    def market_trends(self) -> None:
        self.client.get("/api/v1/careerdex/market/trends")

    @tag("careerdex", "recommendations")
    @task(2)
    def job_recommendations(self) -> None:
        self.client.get(
            "/api/v1/careerdex/jobs/recommendations",
            params={"user_id": "loadtest-user", "limit": 10},
        )

    @tag("data")
    @task(1)
    def data_sources(self) -> None:
        self.client.get("/api/v1/careerdex/data/sources")

    @tag("system")
    @task(1)
    def system_config(self) -> None:
        self.client.get("/api/v1/careerdex/system/config")
