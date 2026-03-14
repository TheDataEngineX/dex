"""DataEngineX dashboard — Streamlit application entry point.

Configurable via YAML. Pulls metrics from a Prometheus-compatible endpoint
and renders panels for pipeline status, data quality, model drift, and alerts.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import yaml
from loguru import logger
from pydantic import BaseModel, Field

try:
    import streamlit as st

    _HAS_STREAMLIT = True
except ImportError:
    _HAS_STREAMLIT = False


class DashboardConfig(BaseModel):
    """Dashboard configuration loaded from YAML."""

    title: str = Field(default="DataEngineX Dashboard", description="Page title")
    prometheus_url: str = Field(
        default="http://localhost:9090",
        description="Base URL of the Prometheus server",
    )
    dex_api_url: str = Field(
        default="http://localhost:8000",
        description="Base URL of the DEX API for metrics/health",
    )
    refresh_interval_seconds: int = Field(default=30, ge=5, description="Auto-refresh interval")
    panels: list[str] = Field(
        default_factory=lambda: [
            "pipeline_status",
            "quality_scores",
            "model_drift",
            "alerts",
        ],
        description="Which panels to display",
    )

    @classmethod
    def from_yaml(cls, path: str | Path) -> DashboardConfig:
        """Load configuration from a YAML file."""
        p = Path(path)
        if not p.exists():
            logger.warning("config file not found at %s, using defaults", p)
            return cls()
        raw = yaml.safe_load(p.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            logger.warning("invalid config format in %s, using defaults", p)
            return cls()
        return cls(**raw)


def _fetch_metrics(config: DashboardConfig) -> dict[str, Any]:
    """Fetch metrics from the DEX API.

    Tries ``/metrics`` and ``/health`` endpoints. Falls back to empty
    dicts if the API is unreachable.
    """
    metrics: dict[str, Any] = {
        "pipelines": [],
        "datasets": [],
        "models": [],
        "alerts": [],
    }

    try:
        with httpx.Client(timeout=5.0) as client:
            health = client.get(f"{config.dex_api_url}/health")
            if health.status_code == 200:
                metrics["health"] = health.json()

            try:
                quality = client.get(f"{config.dex_api_url}/api/v1/data/quality/summary")
                if quality.status_code == 200:
                    data = quality.json()
                    metrics["datasets"] = data.get("datasets", [])
            except httpx.HTTPError:
                pass

            try:
                models = client.get(f"{config.dex_api_url}/api/v1/models")
                if models.status_code == 200:
                    data = models.json()
                    metrics["models"] = [
                        {"name": m.get("name", ""), "psi": 0.0, "alert": False}
                        for m in data.get("models", [])
                    ]
            except httpx.HTTPError:
                pass

    except httpx.ConnectError:
        logger.warning("cannot reach DEX API at %s", config.dex_api_url)

    return metrics


class BaseDashboard:
    """Streamlit-based dashboard for DataEngineX pipeline monitoring.

    Usage::

        config = DashboardConfig.from_yaml("config.yaml")
        dashboard = BaseDashboard(config)
        dashboard.run()
    """

    def __init__(self, config: DashboardConfig | None = None) -> None:
        self.config = config or DashboardConfig()

    def run(self) -> None:
        """Render the dashboard using Streamlit.

        Must be called from within ``streamlit run``.
        """
        if not _HAS_STREAMLIT:
            msg = (
                "streamlit is required for the dashboard. "
                "Install it with: uv sync --group dashboard"
            )
            raise ImportError(msg)

        from dataenginex.dashboard.panels import (
            alerts_panel,
            model_drift_panel,
            pipeline_status_panel,
            quality_scores_panel,
        )

        st.set_page_config(
            page_title=self.config.title,
            page_icon="📊",
            layout="wide",
        )
        st.title(self.config.title)
        st.caption(f"Auto-refresh: {self.config.refresh_interval_seconds}s")

        metrics = _fetch_metrics(self.config)

        panel_map = {
            "pipeline_status": pipeline_status_panel,
            "quality_scores": quality_scores_panel,
            "model_drift": model_drift_panel,
            "alerts": alerts_panel,
        }

        for panel_name in self.config.panels:
            fn = panel_map.get(panel_name)
            if fn:
                fn(metrics)
            else:
                st.warning(f"Unknown panel: {panel_name}")

        st.divider()
        st.caption(f"API: {self.config.dex_api_url} | Prometheus: {self.config.prometheus_url}")
