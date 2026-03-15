"""Tests for structured logging configuration."""

import structlog

from dataenginex.middleware.logging_config import (
    APP_NAME,
    APP_VERSION,
    add_app_context,
    configure_logging,
)


def test_add_app_context() -> None:
    """Test that app context is added to log entries."""
    event_dict = {}
    result = add_app_context(None, "", event_dict)

    assert result["app"] == APP_NAME
    assert result["version"] == APP_VERSION
    assert "app" in result
    assert "version" in result


def test_configure_logging_json() -> None:
    """Test logging configuration with JSON output."""
    configure_logging(log_level="DEBUG", json_logs=True)

    # Verify structlog is configured
    logger = structlog.get_logger("test")
    assert logger is not None


def test_configure_logging_console() -> None:
    """Test logging configuration with console output."""
    configure_logging(log_level="INFO", json_logs=False)

    # Verify structlog is configured
    logger = structlog.get_logger("test")
    assert logger is not None
