"""Reusable dashboard panels for pipeline monitoring."""

from __future__ import annotations

from typing import Any

import structlog

logger = structlog.get_logger()

try:
    import streamlit as st

    _HAS_STREAMLIT = True
except ImportError:
    _HAS_STREAMLIT = False


def _check_streamlit() -> None:
    if not _HAS_STREAMLIT:
        msg = (
            "streamlit is required for dashboard panels. Install it with: uv sync --group dashboard"
        )
        raise ImportError(msg)


def pipeline_status_panel(metrics: dict[str, Any]) -> None:
    """Display pipeline execution status.

    Args:
        metrics: Dict with keys like ``pipelines``, ``last_run``, ``status``.
    """
    _check_streamlit()
    st.subheader("Pipeline Status")

    pipelines = metrics.get("pipelines", [])
    if not pipelines:
        st.info("No pipeline data available. Connect to a running DEX instance.")
        return

    for pipeline in pipelines:
        name = pipeline.get("name", "unknown")
        status = pipeline.get("status", "unknown")
        icon = {"succeeded": "✅", "running": "🔄", "failed": "❌"}.get(status, "❓")
        col1, col2, col3 = st.columns(3)
        col1.metric("Pipeline", name)
        col2.metric("Status", f"{icon} {status}")
        col3.metric("Duration", pipeline.get("duration", "N/A"))

    logger.debug("rendered pipeline_status_panel", count=len(pipelines))


def quality_scores_panel(metrics: dict[str, Any]) -> None:
    """Display data quality scores across datasets.

    Args:
        metrics: Dict with ``datasets`` list, each having ``name`` and ``score``.
    """
    _check_streamlit()
    st.subheader("Data Quality Scores")

    datasets = metrics.get("datasets", [])
    if not datasets:
        st.info("No quality data available.")
        return

    for ds in datasets:
        name = ds.get("name", "unknown")
        score = ds.get("score", 0.0)
        color = "normal" if score >= 0.8 else ("off" if score >= 0.5 else "inverse")
        st.metric(label=name, value=f"{score:.1%}", delta_color=color)

    logger.debug("rendered quality_scores_panel", count=len(datasets))


def model_drift_panel(metrics: dict[str, Any]) -> None:
    """Display model drift detection results.

    Args:
        metrics: Dict with ``models`` list, each having ``name``, ``psi``, ``alert``.
    """
    _check_streamlit()
    st.subheader("Model Drift Detection")

    models = metrics.get("models", [])
    if not models:
        st.info("No model drift data available.")
        return

    for model in models:
        name = model.get("name", "unknown")
        psi = model.get("psi", 0.0)
        alert = model.get("alert", False)
        icon = "🚨" if alert else "✅"
        col1, col2 = st.columns(2)
        col1.metric(f"{icon} {name}", f"PSI: {psi:.4f}")
        threshold = model.get("threshold", 0.2)
        col2.progress(min(psi / threshold, 1.0), text=f"Threshold: {threshold}")

    logger.debug("rendered model_drift_panel", count=len(models))


def alerts_panel(metrics: dict[str, Any]) -> None:
    """Display recent alerts from the monitoring system.

    Args:
        metrics: Dict with ``alerts`` list, each having ``severity``, ``message``, ``time``.
    """
    _check_streamlit()
    st.subheader("Recent Alerts")

    alerts = metrics.get("alerts", [])
    if not alerts:
        st.success("No active alerts.")
        return

    for alert in alerts:
        severity = alert.get("severity", "info")
        message = alert.get("message", "")
        time_str = alert.get("time", "")

        if severity == "critical":
            st.error(f"🔴 [{time_str}] {message}")
        elif severity == "warning":
            st.warning(f"🟡 [{time_str}] {message}")
        else:
            st.info(f"🔵 [{time_str}] {message}")

    logger.debug("rendered alerts_panel", count=len(alerts))
