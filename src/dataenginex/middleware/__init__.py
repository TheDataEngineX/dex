"""Middleware — logging, metrics, tracing, and request handling.

Public API::

    from dataenginex.middleware import (
        configure_logging, get_logger, APP_VERSION,
        get_metrics, PrometheusMetricsMiddleware,
        RequestLoggingMiddleware,
        configure_tracing, instrument_fastapi, get_tracer,
    )

Requires the ``[api]`` extra::

    pip install dataenginex[api]
"""

from __future__ import annotations

try:
    from .domain_metrics import (
        ai_agent_iterations,
        ai_tokens_total,
        ai_tool_calls_total,
        ml_drift_score,
        ml_model_predictions_total,
        pipeline_run_duration_seconds,
        pipeline_runs_total,
        quality_gate_evaluations_total,
        tenant_operations_total,
    )
    from .logging_config import APP_VERSION, configure_logging, get_logger
    from .metrics import get_metrics
    from .metrics_middleware import PrometheusMetricsMiddleware
    from .request_logging import RequestLoggingMiddleware
    from .tracing import configure_tracing, get_tracer, instrument_fastapi
except ImportError as _exc:
    _MISSING_MSG = (
        "dataenginex.middleware requires the [api] extra. "
        "Install it with: pip install dataenginex[api]"
    )
    raise ImportError(_MISSING_MSG) from _exc

__all__ = [
    # Logging
    "APP_VERSION",
    "configure_logging",
    "get_logger",
    # Metrics
    "PrometheusMetricsMiddleware",
    "get_metrics",
    # Domain metrics
    "ai_agent_iterations",
    "ai_tokens_total",
    "ai_tool_calls_total",
    "ml_drift_score",
    "ml_model_predictions_total",
    "pipeline_run_duration_seconds",
    "pipeline_runs_total",
    "quality_gate_evaluations_total",
    "tenant_operations_total",
    # Request logging
    "RequestLoggingMiddleware",
    # Tracing
    "configure_tracing",
    "get_tracer",
    "instrument_fastapi",
]
