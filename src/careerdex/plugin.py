"""CareerDEX plugin — registers CareerDEX with the DataEngineX plugin system.

Discovered automatically via ``entry_points(group="dataenginex.plugins")``
when the ``careerdex-app`` package is installed.

Configuration in ``pyproject.toml``::

    [project.entry-points."dataenginex.plugins"]
    careerdex = "careerdex.plugin:CareerDEXPlugin"
"""

from __future__ import annotations

from typing import Any

from dataenginex.plugins import DataEngineXPlugin

_CAREERDEX_VERSION = "0.5.0"


class CareerDEXPlugin(DataEngineXPlugin):
    """CareerDEX plugin for the DataEngineX ecosystem.

    Exposes health checks, metrics, and routes for the CareerDEX
    job-data platform.
    """

    @property
    def name(self) -> str:
        return "careerdex"

    @property
    def version(self) -> str:
        return _CAREERDEX_VERSION

    def health_check(self) -> dict[str, Any]:
        """Check CareerDEX component health.

        Verifies that the core modules can be imported and the
        settings are loadable.
        """
        checks: dict[str, str] = {}
        try:
            from careerdex.core.settings import get_settings

            get_settings()
            checks["settings"] = "healthy"
        except Exception:
            checks["settings"] = "unhealthy"

        try:
            from careerdex.phases.phase4_ml_models import SalaryPredictor

            SalaryPredictor()
            checks["ml_models"] = "healthy"
        except Exception:
            checks["ml_models"] = "degraded"

        statuses = set(checks.values())
        if "unhealthy" in statuses:
            overall = "unhealthy"
        elif "degraded" in statuses:
            overall = "degraded"
        else:
            overall = "healthy"

        return {"status": overall, "components": checks}

    def get_metrics(self) -> dict[str, Any]:
        """Return CareerDEX-specific metrics."""
        return {
            "plugin": self.name,
            "version": self.version,
            "endpoints": 6,
            "ml_models": 5,
        }

    def register_routes(self, app: Any) -> None:
        """Mount CareerDEX API routes onto the FastAPI app."""
        from careerdex.phases.phase5_api_services import careerdex_router

        app.include_router(careerdex_router)
