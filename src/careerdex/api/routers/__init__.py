"""CareerDEX API routers — v1 data/warehouse and ML model serving."""

from __future__ import annotations

__all__: list[str] = ["ml_router", "v1_router"]

from careerdex.api.routers.ml import ml_router
from careerdex.api.routers.v1 import v1_router
