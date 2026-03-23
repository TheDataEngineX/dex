"""Unified config system for dex.yaml.

Public API::

    from dataenginex.config import DexConfig, load_config, validate_config
"""

from __future__ import annotations

from dataenginex.config.loader import load_config, resolve_env_vars, validate_config
from dataenginex.config.schema import DexConfig

__all__ = ["DexConfig", "load_config", "resolve_env_vars", "validate_config"]
