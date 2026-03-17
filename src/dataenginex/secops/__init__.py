"""DataSecOps — PII detection, masking, and audit logging.

Public API::

    from dataenginex.secops import (
        PIIDetector, PIIField, PIIType,
        MaskingEngine, MaskingStrategy,
        AuditLogger, AuditEvent,
        SecOpsGate,
    )
"""

from __future__ import annotations

from .audit import AuditEvent, AuditLogger, AuditOperation
from .gate import SecOpsGate
from .masking import MaskingEngine, MaskingStrategy
from .pii import PIIDetector, PIIField, PIIType

__all__ = [
    "AuditEvent",
    "AuditLogger",
    "AuditOperation",
    "MaskingEngine",
    "MaskingStrategy",
    "PIIDetector",
    "PIIField",
    "PIIType",
    "SecOpsGate",
]
