"""CareerDEX custom exceptions — fail loudly, never silently.

All exceptions carry actionable context so operators know exactly
what is missing and how to fix it.
"""

from __future__ import annotations


class CareerDEXError(Exception):
    """Base exception for all CareerDEX errors."""


class ConfigurationError(CareerDEXError):
    """Raised when required configuration is missing or invalid.

    Includes the config key and expected format so operators can
    fix the issue without reading source code.
    """


class StubNotImplementedError(NotImplementedError):
    """Raised by stub connectors / models that have no real implementation.

    Forces consumers to implement real integrations before calling
    production code paths.  The message includes what needs to be
    implemented and where.
    """


class MissingDependencyError(CareerDEXError):
    """Raised when an optional dependency is required but not installed.

    Includes the pip install command so operators can fix it immediately.
    """


class NotificationError(CareerDEXError):
    """Raised when a notification (Slack, GitHub) fails to send.

    Callers must handle this explicitly — notifications are never
    silently skipped.
    """
