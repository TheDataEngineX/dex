# dataenginex.secops

Security operations — PII detection, data masking, audit logging, access gates, and privacy guards.

## Quick import

```python
from dataenginex.secops import (
    PiiDetector,
    DataMasker,
    AuditLogger,
    AccessGate,
    PrivacyGuard,
)
```

______________________________________________________________________

## PII Detection

`dataenginex.secops.pii`

Detects PII in DataFrames and text using rule-based patterns (email, phone, SSN, credit card, IP address) and optional NER model integration.

::: dataenginex.secops.pii

**Key class:** `PiiDetector`

```python
from dataenginex.secops.pii import PiiDetector

detector = PiiDetector()
report = detector.scan(df)
for finding in report.findings:
    print(finding.column, finding.pii_type, finding.sample_count)
```

______________________________________________________________________

## Data Masking

`dataenginex.secops.masking`

Masks or redacts PII and sensitive columns in DataFrames. Supports hash, truncation, fake-data substitution, and full redaction strategies.

::: dataenginex.secops.masking

**Key class:** `DataMasker`

```python
from dataenginex.secops.masking import DataMasker, MaskStrategy

masker = DataMasker(
    rules={"email": MaskStrategy.HASH, "phone": MaskStrategy.REDACT}
)
masked_df = masker.mask(df)
```

______________________________________________________________________

## Audit Logging

`dataenginex.secops.audit`

Immutable audit log for data access, pipeline runs, model predictions, and config changes. Persisted to DuckDB.

::: dataenginex.secops.audit

**Key class:** `AuditLogger`

```python
from dataenginex.secops.audit import AuditLogger

logger = AuditLogger(db_path=".dex/store.duckdb")
logger.log(
    action="pipeline_run",
    resource="ingest_events",
    user="svc-account",
    outcome="success",
)
entries = logger.query(action="pipeline_run", since="2024-01-01")
```

______________________________________________________________________

## Access Gate

`dataenginex.secops.gate`

Policy-based access control gate. Checks whether a caller is permitted to read, write, or run a named resource.

::: dataenginex.secops.gate

**Key class:** `AccessGate`

```python
from dataenginex.secops.gate import AccessGate

gate = AccessGate.from_config(engine.config)
gate.check(user="analyst@example.com", action="read", resource="gold.user_summary")
# raises PermissionError if denied
```

______________________________________________________________________

## Privacy Guard

`dataenginex.secops.guard`

End-to-end privacy layer: wraps pipeline runs with automatic PII scanning, masking, and audit logging before data leaves a layer boundary.

::: dataenginex.secops.guard

**Key class:** `PrivacyGuard`

```python
from dataenginex.secops.guard import PrivacyGuard

guard = PrivacyGuard(detector=PiiDetector(), masker=DataMasker(), audit=AuditLogger())
safe_df = guard.enforce(df, destination_layer="gold")
```
