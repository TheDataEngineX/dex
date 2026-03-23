"""Unified exception hierarchy for DataEngineX.

All framework exceptions inherit from ``DataEngineXError`` so callers
can catch broad or narrow as needed::

    try:
        dex.validate("dex.yaml")
    except ConfigValidationError:
        ...  # specific
    except DataEngineXError:
        ...  # catch-all
"""

from __future__ import annotations


class DataEngineXError(Exception):
    """Base exception for all DataEngineX errors."""


# --- Config ---


class ConfigError(DataEngineXError):
    """Error loading or processing configuration."""


class ConfigValidationError(ConfigError):
    """A specific config field failed validation."""

    def __init__(self, field: str, message: str) -> None:
        self.field = field
        self.message = message
        super().__init__(f"Config error at '{field}': {message}")


# --- Pipeline ---


class PipelineError(DataEngineXError):
    """Error during pipeline execution."""


class PipelineStepError(PipelineError):
    """A specific pipeline step failed."""

    def __init__(
        self,
        step: str,
        cause: str = "",
        *,
        pipeline: str = "",
        message: str = "",
    ) -> None:
        self.step = step
        self.pipeline = pipeline
        self.cause = cause or message
        prefix = f"[{pipeline}] " if pipeline else ""
        super().__init__(f"{prefix}Pipeline step '{step}' failed: {self.cause}")


# --- Registry ---


class RegistryError(DataEngineXError):
    """Error in backend registry operations."""


class BackendNotInstalledError(DataEngineXError):
    """An optional backend was requested but its extra is not installed."""

    def __init__(self, backend: str, extra: str) -> None:
        self.backend = backend
        self.extra = extra
        super().__init__(f"Backend '{backend}' requires: pip install dataenginex[{extra}]")


# --- ML ---


class TrainingError(DataEngineXError):
    """Error during model training."""


class ServingError(DataEngineXError):
    """Error during model serving."""


# --- Agent ---


class AgentError(DataEngineXError):
    """Error in agent runtime."""


class LLMProviderError(AgentError):
    """Error communicating with LLM provider."""

    def __init__(self, provider: str, message: str) -> None:
        self.provider = provider
        super().__init__(f"LLM provider '{provider}': {message}")
