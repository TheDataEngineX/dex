"""Reusable sample data for DataEngineX tests.

Provides factory helpers that return plain-dict records matching the DataEngineX
schemas.  These are intentionally *not* Pydantic model instances so they
can feed both schema validation tests and Spark DataFrame construction.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def sample_job_records(count: int = 5) -> list[dict[str, Any]]:
    """Return *count* minimal valid job-posting dicts."""
    now = datetime.now(tz=UTC).isoformat()
    return [
        {
            "job_id": f"j_{i}",
            "source": "linkedin" if i % 2 == 0 else "indeed",
            "source_job_id": f"src_{i}",
            "company_name": f"Company-{i}",
            "job_title": f"Engineer-{i}",
            "job_description": f"Description for role {i} " * 15,
            "location": {"country": "US", "city": "Seattle"},
            "employment_type": "full_time",
            "posted_date": now,
            "last_modified_date": now,
            "dex_hash": f"hash_{i}",
            "required_skills": ["Python", "SQL"],
            "benefits": {
                "salary_min": 70000 + i * 5000,
                "salary_max": 120000 + i * 5000,
                "benefits": ["health", "dental"],
            },
        }
        for i in range(count)
    ]


def sample_user_records(count: int = 3) -> list[dict[str, Any]]:
    """Return *count* minimal valid user-profile dicts."""
    now = datetime.now(tz=UTC).isoformat()
    return [
        {
            "user_id": f"u_{i}",
            "email": f"user{i}@example.com",
            "first_name": f"First{i}",
            "last_name": f"Last{i}",
            "created_date": now,
            "last_activity_date": now,
            "current_title": "Engineer",
            "skills": ["Python"],
            "years_experience": 3 + i,
        }
        for i in range(count)
    ]


def sample_weather_rows() -> list[dict[str, Any]]:
    """Return sample weather observation dicts."""
    return [
        {"city": "Seattle", "date": "2025-01-01", "temp_c": 5.0, "humidity": 82.0},
        {"city": "Seattle", "date": "2025-01-02", "temp_c": 4.5, "humidity": 80.0},
        {"city": "New York", "date": "2025-01-01", "temp_c": -2.0, "humidity": 60.0},
        {"city": "Austin", "date": "2025-01-01", "temp_c": 12.0, "humidity": 45.0},
    ]
