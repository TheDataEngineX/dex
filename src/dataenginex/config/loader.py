"""Load, resolve, validate, and layer dex.yaml configurations.

Usage::

    from dataenginex.config.loader import load_config

    cfg = load_config(Path("dex.yaml"))
    cfg = load_config(Path("dex.yaml"), overlay=Path("dex.prod.yaml"))
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import structlog
import yaml
from pydantic import ValidationError

from dataenginex.config.schema import DexConfig
from dataenginex.core.exceptions import ConfigError

logger = structlog.get_logger()

# Matches ${VAR} and ${VAR:-default}
_ENV_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-(.*?))?\}")


def resolve_env_vars(text: str) -> str:
    """Replace ``${VAR}`` and ``${VAR:-default}`` in *text*.

    Raises:
        ConfigError: If a variable has no value and no default.
    """

    def _replace(match: re.Match[str]) -> str:
        var_name = match.group(1)
        default = match.group(2)
        value = os.environ.get(var_name)
        if value is not None:
            return value
        if default is not None:
            return default
        msg = (
            f"Environment variable '{var_name}' is not set and has no default. "
            f"Use ${{{var_name}:-default}} to provide a fallback."
        )
        raise ConfigError(msg)

    return _ENV_PATTERN.sub(_replace, text)


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge *overlay* into *base*. Overlay values win."""
    merged = base.copy()
    for key, value in overlay.items():
        if (
            key in merged
            and isinstance(merged[key], dict)
            and isinstance(value, dict)
        ):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _load_yaml(path: Path) -> dict[str, Any]:
    """Read a YAML file, resolve env vars, and return the parsed dict."""
    if not path.exists():
        msg = f"Config file not found: {path}"
        raise ConfigError(msg)

    raw_text = path.read_text(encoding="utf-8")

    try:
        resolved_text = resolve_env_vars(raw_text)
    except ConfigError:
        raise
    except Exception as exc:
        msg = f"Failed to resolve env vars in {path}: {exc}"
        raise ConfigError(msg) from exc

    try:
        data = yaml.safe_load(resolved_text)
    except yaml.YAMLError as exc:
        msg = f"Failed to parse YAML in {path}: {exc}"
        raise ConfigError(msg) from exc

    if not isinstance(data, dict):
        msg = f"Config file {path} must be a YAML mapping, got {type(data).__name__}"
        raise ConfigError(msg)

    return data


def load_config(
    path: Path,
    *,
    overlay: Path | None = None,
) -> DexConfig:
    """Load a ``dex.yaml`` and return a validated ``DexConfig``.

    Parameters:
        path: Path to the base config file.
        overlay: Optional overlay file (e.g. ``dex.prod.yaml``).

    Raises:
        ConfigError: If the file is missing or cannot be parsed.
    """
    data = _load_yaml(path)

    if overlay is not None:
        overlay_data = _load_yaml(overlay)
        data = _deep_merge(data, overlay_data)

    try:
        config = DexConfig.model_validate(data)
    except ValidationError as exc:
        msg = f"Config validation failed: {exc}"
        raise ConfigError(msg) from exc

    logger.info("config loaded", path=str(path), project=config.project.name)
    return config


def validate_config(config: DexConfig) -> list[str]:
    """Run cross-reference validation on a loaded config.

    Returns a list of error messages (empty = valid).
    """
    errors: list[str] = []

    source_names = set(config.data.sources.keys())
    pipeline_names = set(config.data.pipelines.keys())

    for pipe_name, pipe_cfg in config.data.pipelines.items():
        if pipe_cfg.source and pipe_cfg.source not in source_names:
            errors.append(
                f"Pipeline '{pipe_name}' references undefined source '{pipe_cfg.source}'"
            )
        for dep in pipe_cfg.depends_on:
            if dep not in pipeline_names:
                errors.append(
                    f"Pipeline '{pipe_name}' depends_on undefined pipeline '{dep}'"
                )

    if errors:
        logger.warning("config validation issues", count=len(errors))

    return errors
