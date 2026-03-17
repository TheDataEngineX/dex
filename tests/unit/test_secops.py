"""Unit tests for the dataenginex.secops module."""

from __future__ import annotations

from dataenginex.secops import (
    AuditLogger,
    AuditOperation,
    MaskingEngine,
    MaskingStrategy,
    PIIDetector,
    PIIType,
    SecOpsGate,
)

# ---------------------------------------------------------------------------
# PIIDetector
# ---------------------------------------------------------------------------


class TestPIIDetectorNameHints:
    def test_email_field_detected(self) -> None:
        detector = PIIDetector()
        fields = detector.pii_field_names([{"email": "user@example.com"}])
        assert "email" in fields

    def test_phone_field_detected(self) -> None:
        detector = PIIDetector()
        fields = detector.pii_field_names([{"phone_number": "555-1234"}])
        assert "phone_number" in fields

    def test_ssn_field_detected(self) -> None:
        detector = PIIDetector()
        fields = detector.pii_field_names([{"ssn": "123-45-6789"}])
        assert "ssn" in fields

    def test_non_pii_field_not_detected(self) -> None:
        detector = PIIDetector()
        fields = detector.pii_field_names([{"product_id": "ABC-001", "quantity": 5}])
        assert fields == set()


class TestPIIDetectorValuePatterns:
    def test_email_value_detected(self) -> None:
        detector = PIIDetector()
        findings = detector.scan_record({"contact": "reach me at alice@example.com please"})
        assert any(f.pii_type == PIIType.EMAIL for f in findings)

    def test_ssn_value_detected(self) -> None:
        detector = PIIDetector()
        findings = detector.scan_record({"data": "SSN: 123-45-6789"})
        assert any(f.pii_type == PIIType.SSN for f in findings)

    def test_credit_card_value_detected(self) -> None:
        detector = PIIDetector()
        findings = detector.scan_record({"payment": "4111 1111 1111 1111"})
        assert any(f.pii_type == PIIType.CREDIT_CARD for f in findings)

    def test_ip_address_value_detected(self) -> None:
        detector = PIIDetector()
        findings = detector.scan_record({"client": "192.168.1.100"})
        assert any(f.pii_type == PIIType.IP_ADDRESS for f in findings)


class TestPIIDetectorDataset:
    def test_scan_dataset_deduplicates(self) -> None:
        detector = PIIDetector()
        records = [{"email": "a@b.com"}, {"email": "c@d.com"}]
        result = detector.scan_dataset(records)
        assert "email" in result
        assert len(result) == 1  # deduped to one entry per field name

    def test_confidence_threshold_filters(self) -> None:
        # High threshold should suppress name-hint detections (confidence 0.85)
        detector = PIIDetector(confidence_threshold=0.99)
        fields = detector.pii_field_names([{"email": "user@example.com"}])
        # Name hint confidence is 0.85 < 0.99 → not reported
        assert "email" not in fields


# ---------------------------------------------------------------------------
# MaskingEngine
# ---------------------------------------------------------------------------


class TestMaskingEngineRedact:
    def test_redact_replaces_value(self) -> None:
        engine = MaskingEngine(default_strategy=MaskingStrategy.REDACT)
        result = engine.mask_record({"email": "user@example.com"}, {"email"})
        assert result["email"] == "[REDACTED]"

    def test_non_pii_field_unchanged(self) -> None:
        engine = MaskingEngine()
        result = engine.mask_record({"name": "Alice", "id": 1}, {"name"})
        assert result["id"] == 1


class TestMaskingEngineHash:
    def test_hash_produces_hex_string(self) -> None:
        engine = MaskingEngine(default_strategy=MaskingStrategy.HASH)
        result = engine.mask_record({"email": "user@example.com"}, {"email"})
        assert isinstance(result["email"], str)
        assert len(result["email"]) == 64  # SHA-256 hex

    def test_hash_is_deterministic(self) -> None:
        engine = MaskingEngine(default_strategy=MaskingStrategy.HASH)
        r1 = engine.mask_record({"email": "user@example.com"}, {"email"})
        r2 = engine.mask_record({"email": "user@example.com"}, {"email"})
        assert r1["email"] == r2["email"]

    def test_different_values_produce_different_hashes(self) -> None:
        engine = MaskingEngine(default_strategy=MaskingStrategy.HASH)
        r1 = engine.mask_record({"email": "a@example.com"}, {"email"})
        r2 = engine.mask_record({"email": "b@example.com"}, {"email"})
        assert r1["email"] != r2["email"]


class TestMaskingEnginePartial:
    def test_partial_keeps_last_4(self) -> None:
        engine = MaskingEngine(default_strategy=MaskingStrategy.PARTIAL)
        result = engine.mask_record({"phone": "555-867-5309"}, {"phone"})
        assert result["phone"].endswith("5309")
        assert "*" in result["phone"]

    def test_partial_short_value_fully_masked(self) -> None:
        engine = MaskingEngine(default_strategy=MaskingStrategy.PARTIAL, partial_keep_last=4)
        result = engine.mask_record({"pin": "123"}, {"pin"})
        assert result["pin"] == "***"


class TestMaskingEngineTokenize:
    def test_tokenize_produces_tok_prefix(self) -> None:
        engine = MaskingEngine(default_strategy=MaskingStrategy.TOKENIZE)
        result = engine.mask_record({"email": "user@example.com"}, {"email"})
        assert str(result["email"]).startswith("tok_")

    def test_tokenize_is_deterministic(self) -> None:
        engine = MaskingEngine(default_strategy=MaskingStrategy.TOKENIZE)
        r1 = engine.mask_record({"email": "user@example.com"}, {"email"})
        r2 = engine.mask_record({"email": "user@example.com"}, {"email"})
        assert r1["email"] == r2["email"]


class TestMaskingEngineFieldStrategies:
    def test_per_field_strategy_overrides_default(self) -> None:
        engine = MaskingEngine(
            default_strategy=MaskingStrategy.REDACT,
            field_strategies={"email": MaskingStrategy.HASH},
        )
        result = engine.mask_record({"email": "x@y.com", "phone": "555-0000"}, {"email", "phone"})
        # email → hash (64 hex chars), phone → [REDACTED]
        assert len(str(result["email"])) == 64
        assert result["phone"] == "[REDACTED]"


class TestMaskingEngineNone:
    def test_none_value_redacted(self) -> None:
        engine = MaskingEngine()
        result = engine.mask_record({"email": None}, {"email"})
        assert result["email"] == "[REDACTED]"


# ---------------------------------------------------------------------------
# AuditLogger
# ---------------------------------------------------------------------------


class TestAuditLogger:
    def test_log_scan_appends_event(self) -> None:
        log = AuditLogger()
        log.log_scan("users", ["email"], 100)
        assert len(log.events) == 1
        assert log.events[0].operation == AuditOperation.PII_SCAN

    def test_log_mask_appends_event(self) -> None:
        log = AuditLogger()
        log.log_mask("users", ["email"], 100, strategy="redact")
        assert len(log.events) == 1
        assert log.events[0].operation == AuditOperation.PII_MASK

    def test_events_for_filters_by_dataset(self) -> None:
        log = AuditLogger()
        log.log_scan("users", ["email"], 10)
        log.log_scan("orders", ["phone"], 5)
        assert len(log.events_for("users")) == 1
        assert len(log.events_for("orders")) == 1

    def test_max_history_evicts_oldest(self) -> None:
        log = AuditLogger(max_history=3)
        for i in range(5):
            log.log_scan(f"ds_{i}", [], 1)
        assert len(log.events) == 3
        # Oldest events evicted; most recent retained
        assert log.events[0].dataset_name == "ds_2"

    def test_clear_removes_all_events(self) -> None:
        log = AuditLogger()
        log.log_scan("x", [], 1)
        log.clear()
        assert log.events == []


# ---------------------------------------------------------------------------
# SecOpsGate (integration)
# ---------------------------------------------------------------------------


class TestSecOpsGate:
    def _records(self) -> list[dict[str, object]]:
        return [
            {"id": 1, "email": "alice@example.com", "order_total": 99.99},
            {"id": 2, "email": "bob@example.com", "order_total": 49.50},
        ]

    def test_process_masks_pii_fields(self) -> None:
        gate = SecOpsGate(dataset_name="orders")
        result = gate.process(self._records())
        assert all(r["email"] == "[REDACTED]" for r in result)

    def test_process_preserves_non_pii_fields(self) -> None:
        gate = SecOpsGate(dataset_name="orders")
        result = gate.process(self._records())
        assert result[0]["id"] == 1
        assert abs(float(str(result[0]["order_total"])) - 99.99) < 0.001

    def test_process_emits_audit_events(self) -> None:
        gate = SecOpsGate(dataset_name="orders")
        gate.process(self._records())
        events = gate.audit_logger.events
        ops = {e.operation for e in events}
        assert AuditOperation.PII_SCAN in ops
        assert AuditOperation.PII_MASK in ops

    def test_process_no_pii_returns_original(self) -> None:
        gate = SecOpsGate(dataset_name="clean")
        records = [{"product_id": "X1", "qty": 3}]
        result = gate.process(records)
        assert result == records

    def test_scan_only_does_not_mask(self) -> None:
        gate = SecOpsGate(dataset_name="orders")
        detected = gate.scan(self._records())
        assert "email" in detected
        # scan() should NOT modify the original records
        assert self._records()[0]["email"] == "alice@example.com"

    def test_custom_field_strategy(self) -> None:
        gate = SecOpsGate(
            dataset_name="users",
            field_strategies={"email": MaskingStrategy.HASH},
        )
        result = gate.process(self._records())
        # hash produces 64-char hex, not "[REDACTED]"
        assert len(str(result[0]["email"])) == 64

    def test_original_records_not_mutated(self) -> None:
        gate = SecOpsGate(dataset_name="orders")
        original = self._records()
        original_email = original[0]["email"]
        gate.process(original)
        assert original[0]["email"] == original_email

    def test_empty_dataset_returns_empty(self) -> None:
        gate = SecOpsGate(dataset_name="empty")
        assert gate.process([]) == []

    def test_audit_actor_propagated(self) -> None:
        gate = SecOpsGate(dataset_name="orders", actor="pipeline-v2")
        gate.process(self._records())
        assert all(e.actor == "pipeline-v2" for e in gate.audit_logger.events)


# ---------------------------------------------------------------------------
# PIIField sample helper
# ---------------------------------------------------------------------------


class TestSafeSample:
    def test_sample_masks_leading_chars(self) -> None:
        from dataenginex.secops.pii import _safe_sample

        result = _safe_sample("1234567890")
        assert result.endswith("7890")
        assert result.startswith("******")

    def test_sample_short_value_fully_masked(self) -> None:
        from dataenginex.secops.pii import _safe_sample

        result = _safe_sample("hi")
        assert result == "**"

    def test_sample_none_value(self) -> None:
        from dataenginex.secops.pii import _safe_sample

        # None → empty string → empty sample
        result = _safe_sample(None)
        assert result == ""


# Ensure AuditOperation imported at module level for isinstance check
assert AuditOperation.PII_SCAN is not None
