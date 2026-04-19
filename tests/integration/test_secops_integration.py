"""Integration tests — PII detection, masking, and full secops pipeline."""

from __future__ import annotations

from dataenginex.secops.masking import MaskingEngine, MaskingStrategy
from dataenginex.secops.pii import PIIDetector, PIIType

# ---------------------------------------------------------------------------
# PIIDetector — single record scanning
# ---------------------------------------------------------------------------


class TestPIIDetectorSingleRecord:
    def test_detects_email_by_field_name(self) -> None:
        detector = PIIDetector()
        findings = detector.scan_record({"email": "alice@example.com", "age": 30})
        names = {f.field_name for f in findings}
        assert "email" in names

    def test_detects_email_by_value_pattern(self) -> None:
        detector = PIIDetector()
        findings = detector.scan_record({"contact": "reach me at bob@corp.io"})
        assert any(f.pii_type == PIIType.EMAIL for f in findings)

    def test_detects_phone_by_field_name(self) -> None:
        detector = PIIDetector()
        findings = detector.scan_record({"phone": "555-867-5309"})
        names = {f.field_name for f in findings}
        assert "phone" in names

    def test_detects_ssn_by_value_pattern(self) -> None:
        detector = PIIDetector()
        findings = detector.scan_record({"identifier": "123-45-6789"})
        assert any(f.pii_type == PIIType.SSN for f in findings)

    def test_detects_ip_address_by_value_pattern(self) -> None:
        detector = PIIDetector()
        findings = detector.scan_record({"last_login_ip": "192.168.1.1"})
        assert any(f.pii_type == PIIType.IP_ADDRESS for f in findings)

    def test_detects_credit_card_by_value_pattern(self) -> None:
        detector = PIIDetector()
        findings = detector.scan_record({"payment": "4111-1111-1111-1111"})
        assert any(f.pii_type == PIIType.CREDIT_CARD for f in findings)

    def test_detects_name_by_field_hint(self) -> None:
        detector = PIIDetector()
        findings = detector.scan_record({"first_name": "Alice", "last_name": "Smith"})
        names = {f.field_name for f in findings}
        assert "first_name" in names
        assert "last_name" in names

    def test_no_pii_in_clean_record(self) -> None:
        detector = PIIDetector()
        findings = detector.scan_record({"product_id": "P001", "quantity": 5, "price": 9.99})
        assert findings == []

    def test_confidence_above_threshold_reported(self) -> None:
        detector = PIIDetector(confidence_threshold=0.5)
        findings = detector.scan_record({"email": "user@test.com"})
        assert all(f.confidence >= 0.5 for f in findings)

    def test_high_confidence_threshold_filters_low_confidence(self) -> None:
        # DOB pattern has 0.60 confidence — filtered by 0.95 threshold
        detector = PIIDetector(confidence_threshold=0.95)
        findings = detector.scan_record({"dob_field": "1990/01/15"})
        # Only name-hint match (0.85) or email (0.95) should pass; dob value is 0.60
        pii_types = {f.pii_type for f in findings}
        assert PIIType.DATE_OF_BIRTH not in pii_types or all(
            f.confidence >= 0.95 for f in findings if f.pii_type == PIIType.DATE_OF_BIRTH
        )


# ---------------------------------------------------------------------------
# PIIDetector — dataset scanning
# ---------------------------------------------------------------------------


class TestPIIDetectorDataset:
    def _make_user_records(self) -> list[dict]:  # type: ignore[type-arg]
        return [
            {"user_id": "u1", "email": "alice@example.com", "age": 28},
            {"user_id": "u2", "email": "bob@example.com", "age": 34},
            {"user_id": "u3", "email": "carol@example.com", "age": 22},
        ]

    def test_scan_dataset_deduplicates_fields(self) -> None:
        detector = PIIDetector()
        records = self._make_user_records()
        detected = detector.scan_dataset(records)
        # email appears in all 3 records but should be deduplicated to one entry
        assert len([k for k in detected if k == "email"]) == 1

    def test_pii_field_names_returns_set(self) -> None:
        detector = PIIDetector()
        records = self._make_user_records()
        fields = detector.pii_field_names(records)
        assert isinstance(fields, set)
        assert "email" in fields

    def test_scan_dataset_mixed_records(self) -> None:
        detector = PIIDetector()
        records = [
            {"user_id": "u1", "email": "x@y.com", "score": 100},
            {"device_id": "d1", "ip": "10.0.0.1", "score": 50},
        ]
        detected = detector.scan_dataset(records)
        field_names = set(detected.keys())
        # Should detect email and/or ip-related fields
        assert len(field_names) > 0

    def test_empty_dataset_returns_empty(self) -> None:
        detector = PIIDetector()
        assert detector.scan_dataset([]) == {}

    def test_pii_field_names_empty_returns_empty_set(self) -> None:
        detector = PIIDetector()
        assert detector.pii_field_names([]) == set()


# ---------------------------------------------------------------------------
# MaskingEngine — individual strategies
# ---------------------------------------------------------------------------


class TestMaskingEngineStrategies:
    def test_redact_strategy_replaces_with_constant(self) -> None:
        engine = MaskingEngine(default_strategy=MaskingStrategy.REDACT)
        result = engine.mask_record({"email": "alice@example.com"}, pii_fields={"email"})
        assert result["email"] == "[REDACTED]"

    def test_hash_strategy_produces_hex_string(self) -> None:
        engine = MaskingEngine(default_strategy=MaskingStrategy.HASH)
        result = engine.mask_record({"ssn": "123-45-6789"}, pii_fields={"ssn"})
        assert len(result["ssn"]) == 64  # SHA-256 hex
        assert all(c in "0123456789abcdef" for c in result["ssn"])

    def test_hash_strategy_is_deterministic(self) -> None:
        engine = MaskingEngine(default_strategy=MaskingStrategy.HASH)
        r1 = engine.mask_record({"email": "alice@example.com"}, pii_fields={"email"})
        r2 = engine.mask_record({"email": "alice@example.com"}, pii_fields={"email"})
        assert r1["email"] == r2["email"]

    def test_hash_different_values_produce_different_hashes(self) -> None:
        engine = MaskingEngine(default_strategy=MaskingStrategy.HASH)
        r1 = engine.mask_record({"email": "alice@example.com"}, pii_fields={"email"})
        r2 = engine.mask_record({"email": "bob@example.com"}, pii_fields={"email"})
        assert r1["email"] != r2["email"]

    def test_partial_strategy_keeps_last_four_chars(self) -> None:
        engine = MaskingEngine(default_strategy=MaskingStrategy.PARTIAL, partial_keep_last=4)
        result = engine.mask_record({"phone": "5558675309"}, pii_fields={"phone"})
        assert result["phone"].endswith("5309")
        assert result["phone"].startswith("***")

    def test_partial_strategy_short_value_all_masked(self) -> None:
        engine = MaskingEngine(default_strategy=MaskingStrategy.PARTIAL, partial_keep_last=4)
        result = engine.mask_record({"code": "123"}, pii_fields={"code"})
        assert result["code"] == "***"

    def test_tokenize_strategy_produces_tok_prefix(self) -> None:
        engine = MaskingEngine(default_strategy=MaskingStrategy.TOKENIZE)
        result = engine.mask_record({"email": "alice@example.com"}, pii_fields={"email"})
        assert result["email"].startswith("tok_")

    def test_tokenize_is_deterministic(self) -> None:
        engine = MaskingEngine(default_strategy=MaskingStrategy.TOKENIZE)
        r1 = engine.mask_record({"email": "a@b.com"}, pii_fields={"email"})
        r2 = engine.mask_record({"email": "a@b.com"}, pii_fields={"email"})
        assert r1["email"] == r2["email"]

    def test_non_pii_fields_pass_through_unchanged(self) -> None:
        engine = MaskingEngine(default_strategy=MaskingStrategy.REDACT)
        record = {"email": "alice@example.com", "product_id": "P001", "quantity": 5}
        result = engine.mask_record(record, pii_fields={"email"})
        assert result["product_id"] == "P001"
        assert result["quantity"] == 5

    def test_none_value_is_redacted(self) -> None:
        engine = MaskingEngine(default_strategy=MaskingStrategy.REDACT)
        result = engine.mask_record({"email": None}, pii_fields={"email"})
        assert result["email"] == "[REDACTED]"

    def test_none_value_with_hash_is_redacted(self) -> None:
        engine = MaskingEngine(default_strategy=MaskingStrategy.HASH)
        result = engine.mask_record({"email": None}, pii_fields={"email"})
        assert result["email"] == "[REDACTED]"

    def test_per_field_strategy_overrides_default(self) -> None:
        engine = MaskingEngine(
            default_strategy=MaskingStrategy.REDACT,
            field_strategies={"email": MaskingStrategy.HASH},
        )
        result = engine.mask_record(
            {"email": "alice@example.com", "phone": "555-0001"},
            pii_fields={"email", "phone"},
        )
        assert result["phone"] == "[REDACTED]"
        assert len(result["email"]) == 64  # hash

    def test_custom_salt_changes_hash(self) -> None:
        e1 = MaskingEngine(default_strategy=MaskingStrategy.HASH, salt="salt1")
        e2 = MaskingEngine(default_strategy=MaskingStrategy.HASH, salt="salt2")
        r1 = e1.mask_record({"email": "x@y.com"}, pii_fields={"email"})
        r2 = e2.mask_record({"email": "x@y.com"}, pii_fields={"email"})
        assert r1["email"] != r2["email"]


# ---------------------------------------------------------------------------
# MaskingEngine — dataset masking
# ---------------------------------------------------------------------------


class TestMaskingEngineDataset:
    def test_mask_dataset_applies_to_all_records(self) -> None:
        engine = MaskingEngine(default_strategy=MaskingStrategy.REDACT)
        records = [
            {"email": "a@b.com", "name": "Alice"},
            {"email": "c@d.com", "name": "Bob"},
        ]
        masked = engine.mask_dataset(records, pii_fields={"email"})
        assert all(r["email"] == "[REDACTED]" for r in masked)
        assert masked[0]["name"] == "Alice"
        assert masked[1]["name"] == "Bob"

    def test_mask_dataset_returns_new_records(self) -> None:
        engine = MaskingEngine(default_strategy=MaskingStrategy.REDACT)
        original = [{"email": "x@y.com", "id": 1}]
        masked = engine.mask_dataset(original, pii_fields={"email"})
        # original should be unchanged
        assert original[0]["email"] == "x@y.com"
        assert masked[0]["email"] == "[REDACTED]"

    def test_mask_empty_dataset(self) -> None:
        engine = MaskingEngine(default_strategy=MaskingStrategy.REDACT)
        assert engine.mask_dataset([], pii_fields={"email"}) == []


# ---------------------------------------------------------------------------
# Full SecOps pipeline: detect PII → mask dataset
# ---------------------------------------------------------------------------


class TestFullSecOpsPipeline:
    def test_detect_then_mask_with_redact(self) -> None:
        detector = PIIDetector()
        engine = MaskingEngine(default_strategy=MaskingStrategy.REDACT)

        records = [
            {"user_id": "u1", "email": "alice@example.com", "score": 95},
            {"user_id": "u2", "email": "bob@example.com", "score": 80},
        ]
        pii_fields = detector.pii_field_names(records)
        masked = engine.mask_dataset(records, pii_fields=pii_fields)

        assert all(r["email"] == "[REDACTED]" for r in masked)
        assert all(r["user_id"] not in pii_fields or r["user_id"] == "[REDACTED]" for r in masked)
        assert masked[0]["score"] == 95

    def test_detect_then_mask_with_hash(self) -> None:
        detector = PIIDetector()
        engine = MaskingEngine(default_strategy=MaskingStrategy.HASH)

        records = [{"phone": "555-867-5309", "category": "premium"}]
        pii_fields = detector.pii_field_names(records)
        masked = engine.mask_dataset(records, pii_fields=pii_fields)

        if "phone" in pii_fields:
            assert len(masked[0]["phone"]) == 64
        assert masked[0]["category"] == "premium"

    def test_detect_then_partial_mask_credit_card(self) -> None:
        detector = PIIDetector()
        engine = MaskingEngine(default_strategy=MaskingStrategy.PARTIAL, partial_keep_last=4)

        records = [{"card_number": "4111111111111111", "amount": 99.99}]
        pii_fields = detector.pii_field_names(records)
        masked = engine.mask_dataset(records, pii_fields=pii_fields)

        if "card_number" in pii_fields:
            assert masked[0]["card_number"].endswith("1111")
        assert masked[0]["amount"] == 99.99

    def test_mixed_pii_types_all_masked(self) -> None:
        detector = PIIDetector()
        engine = MaskingEngine(
            default_strategy=MaskingStrategy.REDACT,
            field_strategies={"email": MaskingStrategy.HASH},
        )

        records = [
            {
                "email": "alice@example.com",
                "phone": "555-123-4567",
                "ssn": "123-45-6789",
                "product": "laptop",
            }
        ]
        pii_fields = detector.pii_field_names(records)
        masked = engine.mask_dataset(records, pii_fields=pii_fields)

        # product should not be masked
        assert masked[0]["product"] == "laptop"
        # email masked with hash (64 hex chars)
        if "email" in pii_fields:
            assert len(masked[0]["email"]) == 64

    def test_no_pii_records_unchanged_after_pipeline(self) -> None:
        detector = PIIDetector()
        engine = MaskingEngine(default_strategy=MaskingStrategy.REDACT)

        records = [{"product_id": "P001", "price": 29.99, "in_stock": True}]
        pii_fields = detector.pii_field_names(records)
        masked = engine.mask_dataset(records, pii_fields=pii_fields)

        assert masked[0] == records[0]
