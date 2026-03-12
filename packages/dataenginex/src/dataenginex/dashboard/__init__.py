"""DataEngineX dashboard — Streamlit-based pipeline monitoring.

Provides a configurable dashboard template that pulls data from
Prometheus metrics and displays pipeline status, quality scores,
model drift, and alerts.

Requires ``streamlit`` (install via the ``dashboard`` dependency group).

Usage::

    from dataenginex.dashboard import DashboardConfig, BaseDashboard

    config = DashboardConfig.from_yaml("dashboard_config.yaml")
    dashboard = BaseDashboard(config)
    dashboard.run()

Or standalone::

    streamlit run examples/dashboard/run_dashboard.py
"""

from __future__ import annotations

from .app import BaseDashboard, DashboardConfig

__all__ = [
    "BaseDashboard",
    "DashboardConfig",
]
