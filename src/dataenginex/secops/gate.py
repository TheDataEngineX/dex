"""SecOpsGate — scan, mask, and audit a dataset in one call.

Integrates ``PIIDetector``, ``MaskingEngine``, and ``AuditLogger`` with
the same batch-oriented interface as ``QualityGate``.

Typical usage::

    from dataenginex.secops import SecOpsGate, MaskingStrategy

    gate = SecOpsGate(
        field_strategies={"email": MaskingStrategy.HASH},
        dataset_name="users",
    )
    clean_records = gate.process(raw_records)
"""

from __future__ import annotations

from typing import Any

from dataenginex.secops.audit import AuditLogger
from dataenginex.secops.masking import MaskingEngine, MaskingStrategy
from dataenginex.secops.pii import PIIDetector, PIIField

__all__ = ["SecOpsGate"]


class SecOpsGate:
    """Scan for PII, mask it, and emit an audit event — in one call.

    Parameters
    ----------
    detector:
        ``PIIDetector`` instance.  Created with defaults if omitted.
    masker:
        ``MaskingEngine`` instance.  Created with defaults if omitted.
    audit_logger:
        ``AuditLogger`` instance.  Created with defaults if omitted.
    dataset_name:
        Logical name used in audit events.
    actor:
        Actor label written to audit events (user ID, service name, …).
    default_strategy:
        Default masking strategy when no per-field override exists.
    field_strategies:
        Per-field masking strategy overrides.
    """

    def __init__(
        self,
        detector: PIIDetector | None = None,
        masker: MaskingEngine | None = None,
        audit_logger: AuditLogger | None = None,
        *,
        dataset_name: str = "dataset",
        actor: str = "system",
        default_strategy: MaskingStrategy = MaskingStrategy.REDACT,
        field_strategies: dict[str, MaskingStrategy] | None = None,
    ) -> None:
        self._detector = detector or PIIDetector()
        self._masker = masker or MaskingEngine(
            default_strategy=default_strategy,
            field_strategies=field_strategies or {},
        )
        self._audit = audit_logger or AuditLogger()
        self._dataset_name = dataset_name
        self._actor = actor

    @property
    def audit_logger(self) -> AuditLogger:
        """Return the attached audit logger."""
        return self._audit

    def scan(self, records: list[dict[str, Any]]) -> dict[str, PIIField]:
        """Scan records for PII and log the result.  Does NOT mask."""
        detected = self._detector.scan_dataset(records)
        self._audit.log_scan(
            dataset_name=self._dataset_name,
            pii_fields=list(detected.keys()),
            record_count=len(records),
            actor=self._actor,
            metadata={f: d.pii_type.value for f, d in detected.items()},
        )
        return detected

    def mask(
        self,
        records: list[dict[str, Any]],
        pii_fields: set[str],
        strategy: str = "default",
    ) -> list[dict[str, Any]]:
        """Mask *pii_fields* in *records* and log the operation."""
        masked = self._masker.mask_dataset(records, pii_fields)
        self._audit.log_mask(
            dataset_name=self._dataset_name,
            pii_fields=sorted(pii_fields),
            record_count=len(records),
            strategy=strategy,
            actor=self._actor,
        )
        return masked

    def process(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Scan for PII, mask all detected fields, and audit both steps.

        Returns the masked records.  The original *records* list is not
        mutated.
        """
        detected = self.scan(records)
        if not detected:
            return list(records)
        return self.mask(records, set(detected.keys()), strategy="auto")
