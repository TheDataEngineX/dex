"""Drift monitoring scheduler — periodic distribution checks.

``DriftScheduler`` runs background drift checks on registered models,
updates Prometheus gauges, and fires alert counters when drift
exceeds configured thresholds.

Usage::

    from dataenginex.ml import DriftScheduler, DriftMonitorConfig

    scheduler = DriftScheduler()

    def fetch_current() -> dict[str, list[float]]:
        return {"feature_a": [...], "feature_b": [...]}

    config = DriftMonitorConfig(
        model_name="churn_model",
        reference_data={"feature_a": [...], "feature_b": [...]},
        check_interval_seconds=300,
    )
    scheduler.register(config, data_fn=fetch_current)
    scheduler.start()
    # ... later ...
    scheduler.stop()
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol

from loguru import logger

from .drift import DriftDetector, DriftReport
from .metrics import model_drift_alerts_total, model_drift_psi

__all__ = [
    "DriftCheckResult",
    "DriftMonitorConfig",
    "DriftScheduler",
]


class DataProvider(Protocol):
    """Callable that returns current feature data for drift comparison.

    Returns a mapping of ``feature_name → list[float]`` with the
    current distribution values for each monitored feature.
    """

    def __call__(self) -> dict[str, list[float]]: ...


@dataclass
class DriftMonitorConfig:
    """Configuration for monitoring a single model's data drift.

    Attributes:
        model_name: Name of the model being monitored.
        reference_data: Mapping of feature_name → reference distribution values.
        psi_threshold: PSI value above which drift is flagged (default 0.20).
        check_interval_seconds: Seconds between consecutive checks (default 300).
        n_bins: Number of histogram bins for PSI calculation (default 10).
    """

    model_name: str
    reference_data: dict[str, list[float]]
    psi_threshold: float = 0.20
    check_interval_seconds: float = 300.0
    n_bins: int = 10


@dataclass
class DriftCheckResult:
    """Aggregated result of a drift check across all features of a model.

    Attributes:
        model_name: Name of the model checked.
        reports: Per-feature drift reports.
        drift_detected: ``True`` if any feature exceeded the PSI threshold.
        max_psi: Highest PSI score across all features.
        checked_at: Timestamp of the check.
    """

    model_name: str
    reports: list[DriftReport]
    drift_detected: bool
    max_psi: float
    checked_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dictionary."""
        return {
            "model_name": self.model_name,
            "drift_detected": self.drift_detected,
            "max_psi": round(self.max_psi, 6),
            "checked_at": self.checked_at.isoformat(),
            "features": [r.to_dict() for r in self.reports],
        }


_MonitorEntry = tuple[DriftMonitorConfig, DataProvider, float]
"""(config, data_fn, last_check_epoch)"""


class DriftScheduler:
    """Background scheduler for periodic model drift checks.

    Runs a daemon thread that iterates registered monitors and
    invokes ``DriftDetector`` when each monitor's interval has elapsed.
    Results are published to Prometheus gauges and counters.

    Parameters
    ----------
    tick_seconds:
        How often the scheduler loop wakes up to check deadlines
        (default ``5.0``).  Lower values give more precise timing
        at the cost of CPU.
    """

    def __init__(self, tick_seconds: float = 5.0) -> None:
        self._monitors: dict[str, _MonitorEntry] = {}
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._tick = tick_seconds
        self._results: dict[str, DriftCheckResult] = {}

    # -- public API ----------------------------------------------------------

    def register(
        self,
        config: DriftMonitorConfig,
        data_fn: DataProvider,
    ) -> None:
        """Register a model for periodic drift monitoring.

        Parameters
        ----------
        config:
            Monitor configuration (thresholds, interval, reference data).
        data_fn:
            Callable returning current feature data as
            ``dict[str, list[float]]``.

        Raises
        ------
        ValueError:
            If ``config.reference_data`` is empty.
        """
        if not config.reference_data:
            msg = f"reference_data must not be empty for model {config.model_name!r}"
            raise ValueError(msg)

        with self._lock:
            self._monitors[config.model_name] = (config, data_fn, 0.0)
        logger.info(
            "Drift monitor registered: model=%s interval=%ss features=%d",
            config.model_name,
            config.check_interval_seconds,
            len(config.reference_data),
        )

    def unregister(self, model_name: str) -> None:
        """Remove a model from drift monitoring.

        Parameters
        ----------
        model_name:
            Name of the model to unregister.

        Raises
        ------
        KeyError:
            If the model is not registered.
        """
        with self._lock:
            if model_name not in self._monitors:
                msg = f"Model {model_name!r} is not registered for drift monitoring"
                raise KeyError(msg)
            del self._monitors[model_name]
            self._results.pop(model_name, None)
        logger.info("Drift monitor unregistered: model=%s", model_name)

    def start(self) -> None:
        """Start the background monitoring thread.

        Raises
        ------
        RuntimeError:
            If the scheduler is already running.
        """
        if self._thread is not None and self._thread.is_alive():
            msg = "DriftScheduler is already running"
            raise RuntimeError(msg)

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop,
            name="drift-scheduler",
            daemon=True,
        )
        self._thread.start()
        logger.info("DriftScheduler started (tick=%ss)", self._tick)

    def stop(self, timeout: float = 10.0) -> None:
        """Stop the background monitoring thread.

        Parameters
        ----------
        timeout:
            Seconds to wait for the thread to join (default ``10.0``).
        """
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)
            self._thread = None
        logger.info("DriftScheduler stopped")

    @property
    def is_running(self) -> bool:
        """Whether the scheduler thread is alive."""
        return self._thread is not None and self._thread.is_alive()

    @property
    def registered_models(self) -> list[str]:
        """Names of all registered models."""
        with self._lock:
            return list(self._monitors.keys())

    def get_last_result(self, model_name: str) -> DriftCheckResult | None:
        """Return the most recent drift check result for a model."""
        return self._results.get(model_name)

    def run_check(self, model_name: str) -> DriftCheckResult:
        """Manually trigger a drift check for one model.

        Parameters
        ----------
        model_name:
            Name of a registered model to check.

        Raises
        ------
        KeyError:
            If the model is not registered.

        Returns
        -------
        DriftCheckResult:
            Aggregated result with per-feature reports.
        """
        with self._lock:
            entry = self._monitors.get(model_name)
            if entry is None:
                msg = f"Model {model_name!r} is not registered for drift monitoring"
                raise KeyError(msg)
            config, data_fn, _ = entry

        return self._execute_check(config, data_fn)

    # -- internal ------------------------------------------------------------

    def _run_loop(self) -> None:
        """Background loop — check each monitor when its interval elapses."""
        logger.debug("Drift scheduler loop entered")
        while not self._stop_event.is_set():
            now = time.monotonic()
            with self._lock:
                snapshot = list(self._monitors.items())

            for name, (config, data_fn, last_check) in snapshot:
                if now - last_check >= config.check_interval_seconds:
                    try:
                        self._execute_check(config, data_fn)
                    except Exception:
                        logger.exception("Drift check failed for model=%s", name)
                    # Update last_check regardless of success/failure
                    with self._lock:
                        if name in self._monitors:
                            old = self._monitors[name]
                            self._monitors[name] = (old[0], old[1], time.monotonic())

            self._stop_event.wait(timeout=self._tick)

    def _execute_check(
        self,
        config: DriftMonitorConfig,
        data_fn: DataProvider,
    ) -> DriftCheckResult:
        """Run a single drift check and publish metrics."""
        detector = DriftDetector(
            psi_threshold=config.psi_threshold,
            n_bins=config.n_bins,
        )

        current_data = data_fn()
        reports = detector.check_dataset(config.reference_data, current_data)

        drift_detected = any(r.drift_detected for r in reports)
        max_psi = max((r.psi for r in reports), default=0.0)

        result = DriftCheckResult(
            model_name=config.model_name,
            reports=reports,
            drift_detected=drift_detected,
            max_psi=max_psi,
        )

        # Publish to Prometheus
        for report in reports:
            model_drift_psi.labels(
                model=config.model_name,
                feature=report.feature_name,
            ).set(report.psi)

            if report.drift_detected:
                model_drift_alerts_total.labels(
                    model=config.model_name,
                    severity=report.severity,
                ).inc()

        self._results[config.model_name] = result

        if drift_detected:
            logger.warning(
                "Drift detected: model=%s max_psi=%.4f features_drifted=%d/%d",
                config.model_name,
                max_psi,
                sum(1 for r in reports if r.drift_detected),
                len(reports),
            )
        else:
            logger.info(
                "Drift check OK: model=%s max_psi=%.4f features=%d",
                config.model_name,
                max_psi,
                len(reports),
            )

        return result
