"""DataEngineX Dashboard — Standalone runner.

Launch with::

    streamlit run examples/dashboard/run_dashboard.py

Requires the ``dashboard`` dependency group::

    uv sync --group dashboard

The dashboard connects to a running DEX API (default: http://localhost:17000)
and displays pipeline status, data quality, model drift, and alerts.
"""

from __future__ import annotations

from pathlib import Path

from dataenginex.dashboard import BaseDashboard, DashboardConfig

_CONFIG_PATH = Path(__file__).parent / "dashboard_config.yaml"

config = DashboardConfig.from_yaml(_CONFIG_PATH)
dashboard = BaseDashboard(config)
dashboard.run()
