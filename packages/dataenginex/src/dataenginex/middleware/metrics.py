"""Prometheus metrics configuration for DataEngineX.

Provides pre-configured Prometheus counters, histograms, and gauges
for HTTP request monitoring.

Functions:
    get_metrics: Generate Prometheus metrics in text format.

Metrics:
    http_requests_total: Total HTTP requests by method/endpoint/status.
    http_request_duration_seconds: Request duration histogram.
    http_requests_in_flight: Gauge of in-progress requests.
    http_exceptions_total: Exception counter by exception type.
"""

from __future__ import annotations

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    REGISTRY,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

__all__ = [
    "get_metrics",
    "http_exceptions_total",
    "http_request_duration_seconds",
    "http_requests_in_flight",
    "http_requests_total",
]

# Request metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status", "environment"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint", "environment"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

http_requests_in_flight = Gauge(
    "http_requests_in_flight",
    "Number of HTTP requests currently being processed",
    ["environment"],
)

http_exceptions_total = Counter(
    "http_exceptions_total",
    "Total HTTP exceptions",
    ["exception_type", "environment"],
)


def get_metrics() -> tuple[bytes, str]:
    """
    Generate Prometheus metrics in text format.

    Returns:
        Tuple of (metrics_data, content_type)
    """
    return generate_latest(REGISTRY), CONTENT_TYPE_LATEST
