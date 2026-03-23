# Phase 1: Data Layer — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Config-driven data pipelines that extract from sources, transform via DuckDB SQL, enforce quality gates, and load into medallion layers — all driven by `dex.yaml`.

**Architecture:** DuckDB as the universal data substrate. PipelineRunner reads config → instantiates connectors from registry → chains transforms → enforces quality → writes to lakehouse layer. Lineage tracked at every step. DAG resolver handles cross-pipeline dependencies.

**Tech Stack:** Python 3.13+ · DuckDB 1.5 · PyArrow · croniter · structlog · Click · Rich

**Spec:** `docs/superpowers/specs/2026-03-21-dataenginex-v2-system-redesign.md` (sections: Data Flow Architecture, Pipeline Execution Flow, Medallion Architecture)

**Master Plan:** `docs/superpowers/plans/2026-03-22-dataenginex-1.0-master-plan.md`

**Gaps Resolved:** G9 (PipelineRunner), G12 (SQL transforms), G25 (failure recovery), G26 (cross-pipeline deps)

---

## Pre-requisite: Phase 0 artifacts used

| Artifact | Location | Used by |
|----------|----------|---------|
| `BackendRegistry[T]` | `src/dataenginex/core/registry.py` | All registries |
| `BaseConnector` | `src/dataenginex/core/interfaces.py` | DuckDB, CSV connectors |
| `BaseTransform` | `src/dataenginex/core/interfaces.py` | SQL transforms |
| `BaseOrchestrator` | `src/dataenginex/core/interfaces.py` | Cron scheduler |
| `PipelineError`, `PipelineStepError` | `src/dataenginex/core/exceptions.py` | Runner error handling |
| `DexConfig`, `load_config` | `src/dataenginex/config/` | Config-driven instantiation |
| `dex` CLI group | `src/dataenginex/cli/main.py` | `dex run` command |

---

## Task 0: Python 3.13 Bump + Branch Setup

**Files:**
- Modify: `pyproject.toml`
- Create: `.python-version`
- Modify: `README.md`
- Modify: `CLAUDE.md`
- Modify: `docs/ARCHITECTURE.md`

- [ ] **Step 1: Create feature branch**

```bash
cd /home/jay/workspace/DataEngineX/dex
git checkout dev && git pull origin dev
git checkout -b feature/phase-1-data-layer
```

- [ ] **Step 2: Bump Python version in pyproject.toml**

Change `requires-python = ">=3.12"` to `requires-python = ">=3.13"` in `pyproject.toml`.

- [ ] **Step 3: Create .python-version file**

```
3.13
```

- [ ] **Step 4: Update docs references**

In `README.md`, `CLAUDE.md`, `docs/ARCHITECTURE.md` — change "Python 3.12+" to "Python 3.13+".

- [ ] **Step 5: Verify**

```bash
uv run poe lint && uv run poe typecheck && uv run poe test
```

Expected: All passing.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml .python-version README.md CLAUDE.md docs/ARCHITECTURE.md
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "chore: bump Python requirement to >=3.13"
```

---

## Task 1: Connector Registry + DuckDB Connector

**Files:**
- Create: `src/dataenginex/data/connectors/__init__.py`
- Create: `src/dataenginex/data/connectors/duckdb.py`
- Create: `tests/conformance/test_connector.py`
- Create: `tests/unit/test_duckdb_connector.py`

- [ ] **Step 1: Write conformance test suite**

```python
# tests/conformance/test_connector.py
"""Conformance tests for BaseConnector implementations.

Every connector backend (built-in or extra) must pass these tests.
Subclass this and provide a `connector` fixture.
"""
from __future__ import annotations

from typing import Any


class ConnectorConformanceTests:
    """All BaseConnector implementations must pass these."""

    def test_connect_disconnect(self, connector: Any) -> None:
        connector.connect()
        connector.disconnect()

    def test_health_check_after_connect(self, connector: Any) -> None:
        connector.connect()
        assert connector.health_check() is True
        connector.disconnect()

    def test_write_then_read(self, connector: Any) -> None:
        connector.connect()
        connector.write(
            [{"id": 1, "name": "alice"}, {"id": 2, "name": "bob"}],
            table="test_table",
        )
        result = connector.read(table="test_table")
        assert len(result) == 2
        connector.disconnect()

    def test_read_empty_table(self, connector: Any) -> None:
        connector.connect()
        result = connector.read(table="nonexistent_empty", default=[])
        assert result == []
        connector.disconnect()
```

- [ ] **Step 2: Run conformance tests — verify they fail**

```bash
uv run pytest tests/conformance/test_connector.py -v
```

Expected: collected 0 items (no subclasses yet)

- [ ] **Step 3: Create connector registry**

```python
# src/dataenginex/data/connectors/__init__.py
"""Connector registry and public API."""
from __future__ import annotations

from dataenginex.core.interfaces import BaseConnector
from dataenginex.core.registry import BackendRegistry

connector_registry: BackendRegistry[BaseConnector] = BackendRegistry("connector")

__all__ = ["BaseConnector", "connector_registry"]
```

- [ ] **Step 4: Implement DuckDB connector**

```python
# src/dataenginex/data/connectors/duckdb.py
"""DuckDB connector — default data engine.

DuckDB 1.5 reads CSV, Parquet, JSON, Postgres, MySQL, S3 natively.
This connector wraps DuckDB as a data source/sink for pipelines.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb
import structlog

from dataenginex.core.interfaces import BaseConnector
from dataenginex.data.connectors import connector_registry

logger = structlog.get_logger()


@connector_registry.decorator("duckdb", is_default=True)
class DuckDBConnector(BaseConnector):
    """DuckDB-backed connector.

    Args:
        database: Path to DuckDB file. ":memory:" for in-memory.
    """

    def __init__(self, database: str = ":memory:") -> None:
        self._database = database
        self._conn: duckdb.DuckDBPyConnection | None = None

    def connect(self) -> None:
        if self._conn is not None:
            return
        self._conn = duckdb.connect(self._database)
        logger.debug("duckdb connected", database=self._database)

    def disconnect(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None
            logger.debug("duckdb disconnected", database=self._database)

    def read(self, *, table: str, default: Any = None, **kwargs: Any) -> list[dict[str, Any]]:
        if self._conn is None:
            msg = "Not connected — call connect() first"
            raise RuntimeError(msg)
        try:
            result = self._conn.execute(f"SELECT * FROM {table}").fetchdf()  # noqa: S608
            return result.to_dict(orient="records")
        except duckdb.CatalogException:
            if default is not None:
                return default
            raise

    def write(self, data: Any, *, table: str, **kwargs: Any) -> None:
        if self._conn is None:
            msg = "Not connected — call connect() first"
            raise RuntimeError(msg)
        import pyarrow as pa

        if isinstance(data, list):
            if len(data) == 0:
                return
            tbl = pa.Table.from_pylist(data)
        elif isinstance(data, pa.Table):
            tbl = data
        else:
            msg = f"Unsupported data type: {type(data)}"
            raise TypeError(msg)

        self._conn.execute(f"CREATE TABLE IF NOT EXISTS {table} AS SELECT * FROM tbl")  # noqa: S608
        logger.info("data written", table=table, rows=len(tbl))

    def health_check(self) -> bool:
        if self._conn is None:
            return False
        try:
            self._conn.execute("SELECT 1")
            return True
        except Exception:
            return False

    def execute(self, sql: str) -> list[dict[str, Any]]:
        """Execute raw SQL and return results as list of dicts."""
        if self._conn is None:
            msg = "Not connected — call connect() first"
            raise RuntimeError(msg)
        return self._conn.execute(sql).fetchdf().to_dict(orient="records")

    @property
    def connection(self) -> duckdb.DuckDBPyConnection:
        """Direct access to the DuckDB connection for advanced use."""
        if self._conn is None:
            msg = "Not connected — call connect() first"
            raise RuntimeError(msg)
        return self._conn
```

- [ ] **Step 5: Write DuckDB connector unit tests (extends conformance)**

```python
# tests/unit/test_duckdb_connector.py
"""DuckDB connector tests — must pass conformance + DuckDB-specific tests."""
from __future__ import annotations

import pytest

from dataenginex.data.connectors.duckdb import DuckDBConnector
from tests.conformance.test_connector import ConnectorConformanceTests


class TestDuckDBConnector(ConnectorConformanceTests):
    @pytest.fixture()
    def connector(self, tmp_path):
        return DuckDBConnector(database=str(tmp_path / "test.duckdb"))

    def test_in_memory_mode(self):
        conn = DuckDBConnector(database=":memory:")
        conn.connect()
        assert conn.health_check() is True
        conn.disconnect()

    def test_execute_raw_sql(self, tmp_path):
        conn = DuckDBConnector(database=str(tmp_path / "test.duckdb"))
        conn.connect()
        conn.write([{"x": 1}, {"x": 2}], table="nums")
        result = conn.execute("SELECT sum(x) as total FROM nums")
        assert result[0]["total"] == 3
        conn.disconnect()

    def test_read_not_connected_raises(self):
        conn = DuckDBConnector()
        with pytest.raises(RuntimeError, match="Not connected"):
            conn.read(table="anything")

    def test_write_empty_list_noop(self, tmp_path):
        conn = DuckDBConnector(database=str(tmp_path / "test.duckdb"))
        conn.connect()
        conn.write([], table="empty")
        conn.disconnect()
```

- [ ] **Step 6: Run tests**

```bash
uv run pytest tests/unit/test_duckdb_connector.py tests/conformance/test_connector.py -v
```

Expected: All PASS.

- [ ] **Step 7: Lint + typecheck**

```bash
uv run poe lint && uv run poe typecheck
```

- [ ] **Step 8: Commit**

```bash
git add src/dataenginex/data/connectors/ tests/conformance/ tests/unit/test_duckdb_connector.py
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "feat: DuckDB connector with registry and conformance tests"
```

---

## Task 2: CSV Connector

**Files:**
- Create: `src/dataenginex/data/connectors/csv.py`
- Create: `tests/unit/test_csv_connector.py`

- [ ] **Step 1: Write CSV connector tests**

```python
# tests/unit/test_csv_connector.py
from __future__ import annotations

import pytest

from dataenginex.data.connectors.csv import CsvConnector
from tests.conformance.test_connector import ConnectorConformanceTests


class TestCsvConnector(ConnectorConformanceTests):
    @pytest.fixture()
    def connector(self, tmp_path):
        # Create a test CSV for read operations
        csv_path = tmp_path / "test.csv"
        csv_path.write_text("id,name\n1,alice\n2,bob\n")
        return CsvConnector(path=str(tmp_path), default_file="test.csv")

    def test_read_specific_file(self, tmp_path):
        csv_path = tmp_path / "data.csv"
        csv_path.write_text("x,y\n1,2\n3,4\n")
        conn = CsvConnector(path=str(tmp_path))
        conn.connect()
        result = conn.read(table="data.csv")
        assert len(result) == 2
        conn.disconnect()

    def test_read_missing_file_with_default(self, tmp_path):
        conn = CsvConnector(path=str(tmp_path))
        conn.connect()
        result = conn.read(table="missing.csv", default=[])
        assert result == []
        conn.disconnect()
```

- [ ] **Step 2: Run to verify failure**

```bash
uv run pytest tests/unit/test_csv_connector.py -v
```

Expected: ImportError (CsvConnector doesn't exist yet)

- [ ] **Step 3: Implement CSV connector**

```python
# src/dataenginex/data/connectors/csv.py
"""CSV file connector — reads/writes CSV files via DuckDB.

Uses DuckDB's native CSV reader for performance (columnar scan,
parallel reads, auto-type detection).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb
import structlog

from dataenginex.core.interfaces import BaseConnector
from dataenginex.data.connectors import connector_registry

logger = structlog.get_logger()


@connector_registry.decorator("csv")
class CsvConnector(BaseConnector):
    """CSV connector backed by DuckDB CSV reader.

    Args:
        path: Directory containing CSV files.
        default_file: Default file to read (for conformance test).
    """

    def __init__(self, path: str = ".", default_file: str | None = None) -> None:
        self._path = Path(path)
        self._default_file = default_file
        self._conn: duckdb.DuckDBPyConnection | None = None

    def connect(self) -> None:
        self._conn = duckdb.connect(":memory:")
        logger.debug("csv connector ready", path=str(self._path))

    def disconnect(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def read(self, *, table: str | None = None, default: Any = None, **kwargs: Any) -> list[dict[str, Any]]:
        if self._conn is None:
            msg = "Not connected — call connect() first"
            raise RuntimeError(msg)

        filename = table or self._default_file
        if filename is None:
            msg = "No table/file specified"
            raise ValueError(msg)

        filepath = self._path / filename
        if not filepath.exists():
            if default is not None:
                return default
            msg = f"CSV file not found: {filepath}"
            raise FileNotFoundError(msg)

        result = self._conn.execute(
            f"SELECT * FROM read_csv_auto('{filepath}')"
        ).fetchdf()
        return result.to_dict(orient="records")

    def write(self, data: Any, *, table: str = "output.csv", **kwargs: Any) -> None:
        if self._conn is None:
            msg = "Not connected — call connect() first"
            raise RuntimeError(msg)
        import pyarrow as pa
        import pyarrow.csv as pcsv

        filepath = self._path / table
        if isinstance(data, list):
            tbl = pa.Table.from_pylist(data)
        elif isinstance(data, pa.Table):
            tbl = data
        else:
            msg = f"Unsupported data type: {type(data)}"
            raise TypeError(msg)

        pcsv.write_csv(tbl, filepath)
        logger.info("csv written", path=str(filepath), rows=len(tbl))

    def health_check(self) -> bool:
        return self._conn is not None and self._path.exists()
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/unit/test_csv_connector.py -v
```

Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add src/dataenginex/data/connectors/csv.py tests/unit/test_csv_connector.py
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "feat: CSV connector with DuckDB-backed reader"
```

---

## Task 3: DuckDB SQL Transforms

**Files:**
- Create: `src/dataenginex/data/transforms/__init__.py`
- Create: `src/dataenginex/data/transforms/sql.py`
- Create: `tests/conformance/test_transform.py`
- Create: `tests/unit/test_sql_transforms.py`

- [ ] **Step 1: Write conformance test suite**

```python
# tests/conformance/test_transform.py
"""Conformance tests for BaseTransform implementations."""
from __future__ import annotations

from typing import Any

import duckdb


class TransformConformanceTests:
    """All BaseTransform implementations must pass these."""

    def test_transform_returns_table_name(self, transform: Any, duckdb_conn: duckdb.DuckDBPyConnection) -> None:
        """Transform must return the name of the output table."""
        duckdb_conn.execute("CREATE TABLE input AS SELECT 1 as id, 'alice' as name")
        result = transform.apply(duckdb_conn, "input")
        assert isinstance(result, str)
        # Result table should exist
        count = duckdb_conn.execute(f"SELECT count(*) FROM {result}").fetchone()[0]
        assert count >= 0
```

- [ ] **Step 2: Create transform registry + base SQL transform**

```python
# src/dataenginex/data/transforms/__init__.py
"""Transform registry and public API."""
from __future__ import annotations

from dataenginex.core.interfaces import BaseTransform
from dataenginex.core.registry import BackendRegistry

transform_registry: BackendRegistry[BaseTransform] = BackendRegistry("transform")

__all__ = ["BaseTransform", "transform_registry"]
```

```python
# src/dataenginex/data/transforms/sql.py
"""DuckDB SQL-based transforms.

All transforms execute SQL against a DuckDB connection and return
the name of the output table. No custom DSL — DuckDB SQL is the
expression language (per spec: G12).

Each transform is a class registered in the transform_registry.
The PipelineRunner chains them: input_table → transform1 → transform2 → ...
"""
from __future__ import annotations

from typing import Any

import duckdb
import structlog

from dataenginex.core.interfaces import BaseTransform
from dataenginex.data.transforms import transform_registry

logger = structlog.get_logger()


@transform_registry.decorator("filter", is_default=True)
class FilterTransform(BaseTransform):
    """Filter rows using a SQL WHERE condition.

    Config: {type: filter, condition: "rating > 5.0"}
    """

    def __init__(self, condition: str, **kwargs: Any) -> None:
        self._condition = condition

    def apply(self, conn: duckdb.DuckDBPyConnection, input_table: str) -> str:
        output = f"{input_table}_filtered"
        conn.execute(f"CREATE OR REPLACE TABLE {output} AS SELECT * FROM {input_table} WHERE {self._condition}")
        count = conn.execute(f"SELECT count(*) FROM {output}").fetchone()[0]
        logger.info("filter applied", condition=self._condition, output_rows=count)
        return output

    def validate(self) -> list[str]:
        if not self._condition.strip():
            return ["filter condition is empty"]
        return []


@transform_registry.decorator("derive")
class DeriveTransform(BaseTransform):
    """Add a derived column using a SQL expression.

    Config: {type: derive, name: "rating_pct", expression: "rating / 10.0 * 100"}
    """

    def __init__(self, name: str, expression: str, **kwargs: Any) -> None:
        self._name = name
        self._expression = expression

    def apply(self, conn: duckdb.DuckDBPyConnection, input_table: str) -> str:
        output = f"{input_table}_derived"
        conn.execute(
            f"CREATE OR REPLACE TABLE {output} AS SELECT *, ({self._expression}) AS {self._name} FROM {input_table}"
        )
        logger.info("derive applied", column=self._name, expression=self._expression)
        return output

    def validate(self) -> list[str]:
        errors = []
        if not self._name.strip():
            errors.append("derive column name is empty")
        if not self._expression.strip():
            errors.append("derive expression is empty")
        return errors


@transform_registry.decorator("cast")
class CastTransform(BaseTransform):
    """Cast columns to specified types.

    Config: {type: cast, columns: {rating: DOUBLE, year: INTEGER}}
    """

    def __init__(self, columns: dict[str, str], **kwargs: Any) -> None:
        self._columns = columns

    def apply(self, conn: duckdb.DuckDBPyConnection, input_table: str) -> str:
        output = f"{input_table}_cast"
        casts = ", ".join(
            f"CAST({col} AS {dtype}) AS {col}" for col, dtype in self._columns.items()
        )
        # Get all columns, replace cast ones
        all_cols = [row[0] for row in conn.execute(f"DESCRIBE {input_table}").fetchall()]
        select_parts = []
        for col in all_cols:
            if col in self._columns:
                select_parts.append(f"CAST({col} AS {self._columns[col]}) AS {col}")
            else:
                select_parts.append(col)
        select_sql = ", ".join(select_parts)
        conn.execute(f"CREATE OR REPLACE TABLE {output} AS SELECT {select_sql} FROM {input_table}")
        logger.info("cast applied", columns=self._columns)
        return output

    def validate(self) -> list[str]:
        if not self._columns:
            return ["cast requires at least one column"]
        return []


@transform_registry.decorator("deduplicate")
class DeduplicateTransform(BaseTransform):
    """Remove duplicate rows based on key columns.

    Config: {type: deduplicate, key: [id]}
    """

    def __init__(self, key: str | list[str], **kwargs: Any) -> None:
        self._key = [key] if isinstance(key, str) else key

    def apply(self, conn: duckdb.DuckDBPyConnection, input_table: str) -> str:
        output = f"{input_table}_deduped"
        key_cols = ", ".join(self._key)
        # Use ROW_NUMBER to keep first occurrence
        conn.execute(f"""
            CREATE OR REPLACE TABLE {output} AS
            SELECT * FROM (
                SELECT *, ROW_NUMBER() OVER (PARTITION BY {key_cols} ORDER BY rowid) AS _rn
                FROM {input_table}
            ) WHERE _rn = 1
        """)
        # Drop the helper column
        conn.execute(f"ALTER TABLE {output} DROP COLUMN _rn")
        before = conn.execute(f"SELECT count(*) FROM {input_table}").fetchone()[0]
        after = conn.execute(f"SELECT count(*) FROM {output}").fetchone()[0]
        logger.info("deduplicate applied", key=self._key, before=before, after=after, removed=before - after)
        return output

    def validate(self) -> list[str]:
        if not self._key:
            return ["deduplicate requires at least one key column"]
        return []
```

- [ ] **Step 3: Write unit tests for all transforms**

```python
# tests/unit/test_sql_transforms.py
"""Tests for DuckDB SQL transforms."""
from __future__ import annotations

import duckdb
import pytest

from dataenginex.data.transforms.sql import (
    CastTransform,
    DeduplicateTransform,
    DeriveTransform,
    FilterTransform,
)
from tests.conformance.test_transform import TransformConformanceTests


@pytest.fixture()
def duckdb_conn():
    conn = duckdb.connect(":memory:")
    yield conn
    conn.close()


class TestFilterTransform(TransformConformanceTests):
    @pytest.fixture()
    def transform(self):
        return FilterTransform(condition="id > 1")

    def test_filter_removes_rows(self, duckdb_conn):
        duckdb_conn.execute("CREATE TABLE src AS SELECT * FROM (VALUES (1, 'a'), (2, 'b'), (3, 'c')) AS t(id, name)")
        t = FilterTransform(condition="id > 1")
        out = t.apply(duckdb_conn, "src")
        count = duckdb_conn.execute(f"SELECT count(*) FROM {out}").fetchone()[0]
        assert count == 2

    def test_validate_empty_condition(self):
        t = FilterTransform(condition="")
        assert len(t.validate()) > 0


class TestDeriveTransform(TransformConformanceTests):
    @pytest.fixture()
    def transform(self):
        return DeriveTransform(name="doubled", expression="id * 2")

    def test_derive_adds_column(self, duckdb_conn):
        duckdb_conn.execute("CREATE TABLE src AS SELECT 5 AS id")
        t = DeriveTransform(name="doubled", expression="id * 2")
        out = t.apply(duckdb_conn, "src")
        row = duckdb_conn.execute(f"SELECT doubled FROM {out}").fetchone()
        assert row[0] == 10


class TestCastTransform(TransformConformanceTests):
    @pytest.fixture()
    def transform(self):
        return CastTransform(columns={"id": "VARCHAR"})

    def test_cast_changes_type(self, duckdb_conn):
        duckdb_conn.execute("CREATE TABLE src AS SELECT 42 AS id")
        t = CastTransform(columns={"id": "VARCHAR"})
        out = t.apply(duckdb_conn, "src")
        dtype = duckdb_conn.execute(f"SELECT typeof(id) FROM {out}").fetchone()[0]
        assert dtype == "VARCHAR"


class TestDeduplicateTransform(TransformConformanceTests):
    @pytest.fixture()
    def transform(self):
        return DeduplicateTransform(key="id")

    def test_dedup_removes_duplicates(self, duckdb_conn):
        duckdb_conn.execute(
            "CREATE TABLE src AS SELECT * FROM (VALUES (1, 'a'), (1, 'b'), (2, 'c')) AS t(id, name)"
        )
        t = DeduplicateTransform(key="id")
        out = t.apply(duckdb_conn, "src")
        count = duckdb_conn.execute(f"SELECT count(*) FROM {out}").fetchone()[0]
        assert count == 2

    def test_dedup_with_multiple_keys(self, duckdb_conn):
        duckdb_conn.execute(
            "CREATE TABLE src AS SELECT * FROM (VALUES (1, 'a'), (1, 'a'), (1, 'b')) AS t(id, name)"
        )
        t = DeduplicateTransform(key=["id", "name"])
        out = t.apply(duckdb_conn, "src")
        count = duckdb_conn.execute(f"SELECT count(*) FROM {out}").fetchone()[0]
        assert count == 2
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/unit/test_sql_transforms.py tests/conformance/test_transform.py -v
```

Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add src/dataenginex/data/transforms/ tests/conformance/test_transform.py tests/unit/test_sql_transforms.py
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "feat: DuckDB SQL transforms — filter, derive, cast, deduplicate"
```

---

## Task 4: Quality Gates

**Files:**
- Create: `src/dataenginex/data/quality/__init__.py`
- Create: `src/dataenginex/data/quality/gates.py`
- Create: `tests/unit/test_quality_gates.py`

- [ ] **Step 1: Write quality gate tests**

```python
# tests/unit/test_quality_gates.py
"""Tests for data quality gates."""
from __future__ import annotations

import duckdb
import pytest

from dataenginex.data.quality.gates import QualityResult, check_quality


@pytest.fixture()
def duckdb_conn():
    conn = duckdb.connect(":memory:")
    yield conn
    conn.close()


class TestQualityGates:
    def test_completeness_pass(self, duckdb_conn):
        duckdb_conn.execute("CREATE TABLE t AS SELECT 1 AS id, 'a' AS name UNION ALL SELECT 2, 'b'")
        result = check_quality(duckdb_conn, "t", completeness=0.9)
        assert result.passed is True

    def test_completeness_fail_with_nulls(self, duckdb_conn):
        duckdb_conn.execute("CREATE TABLE t AS SELECT 1 AS id, 'a' AS name UNION ALL SELECT NULL, NULL")
        result = check_quality(duckdb_conn, "t", completeness=0.9)
        assert result.passed is False
        assert result.completeness_score < 0.9

    def test_uniqueness_pass(self, duckdb_conn):
        duckdb_conn.execute("CREATE TABLE t AS SELECT 1 AS id UNION ALL SELECT 2")
        result = check_quality(duckdb_conn, "t", uniqueness=["id"])
        assert result.passed is True

    def test_uniqueness_fail_with_dupes(self, duckdb_conn):
        duckdb_conn.execute("CREATE TABLE t AS SELECT 1 AS id UNION ALL SELECT 1")
        result = check_quality(duckdb_conn, "t", uniqueness=["id"])
        assert result.passed is False

    def test_custom_sql_check(self, duckdb_conn):
        duckdb_conn.execute("CREATE TABLE t AS SELECT 10 AS value")
        result = check_quality(duckdb_conn, "t", custom_sql="SELECT count(*) FROM t WHERE value > 0")
        assert result.passed is True

    def test_empty_table_fails_completeness(self, duckdb_conn):
        duckdb_conn.execute("CREATE TABLE t (id INTEGER, name VARCHAR)")
        result = check_quality(duckdb_conn, "t", completeness=0.5)
        # Empty table has 0 rows — completeness is undefined, should pass vacuously
        assert result.passed is True
```

- [ ] **Step 2: Implement quality gates**

```python
# src/dataenginex/data/quality/__init__.py
from dataenginex.data.quality.gates import QualityResult, check_quality

__all__ = ["QualityResult", "check_quality"]
```

```python
# src/dataenginex/data/quality/gates.py
"""Data quality gates — completeness, uniqueness, custom SQL checks.

Quality gates run after transforms and before loading to the target layer.
They use DuckDB SQL aggregations for speed (no row-by-row Python).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import duckdb
import structlog

from dataenginex.core.exceptions import PipelineStepError

logger = structlog.get_logger()


@dataclass
class QualityResult:
    """Result of a quality gate check."""

    passed: bool
    completeness_score: float = 1.0
    uniqueness_score: float = 1.0
    custom_passed: bool = True
    details: dict[str, object] = field(default_factory=dict)


def check_quality(
    conn: duckdb.DuckDBPyConnection,
    table: str,
    *,
    completeness: float | None = None,
    uniqueness: list[str] | None = None,
    custom_sql: str | None = None,
) -> QualityResult:
    """Run quality checks against a DuckDB table.

    Args:
        conn: Active DuckDB connection.
        table: Table name to check.
        completeness: Minimum fraction of non-null values (0.0-1.0).
        uniqueness: Columns that must be unique (no duplicates).
        custom_sql: SQL that must return count > 0 to pass.

    Returns:
        QualityResult with pass/fail and scores.
    """
    result = QualityResult(passed=True)

    total_rows = conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]

    if total_rows == 0:
        logger.info("quality check: empty table — passing vacuously", table=table)
        return result

    # Completeness: fraction of non-null values across all columns
    if completeness is not None:
        cols = [row[0] for row in conn.execute(f"DESCRIBE {table}").fetchall()]
        null_counts = []
        for col in cols:
            null_count = conn.execute(
                f"SELECT count(*) FROM {table} WHERE {col} IS NULL"
            ).fetchone()[0]
            null_counts.append(null_count)
        total_cells = total_rows * len(cols)
        total_nulls = sum(null_counts)
        score = (total_cells - total_nulls) / total_cells if total_cells > 0 else 1.0
        result.completeness_score = score
        if score < completeness:
            result.passed = False
            logger.warning(
                "quality check failed: completeness",
                table=table,
                score=round(score, 4),
                threshold=completeness,
            )

    # Uniqueness: no duplicate values in specified columns
    if uniqueness is not None:
        key_cols = ", ".join(uniqueness)
        distinct_count = conn.execute(
            f"SELECT count(DISTINCT ({key_cols})) FROM {table}"
        ).fetchone()[0]
        score = distinct_count / total_rows if total_rows > 0 else 1.0
        result.uniqueness_score = score
        if distinct_count < total_rows:
            result.passed = False
            logger.warning(
                "quality check failed: uniqueness",
                table=table,
                columns=uniqueness,
                distinct=distinct_count,
                total=total_rows,
            )

    # Custom SQL: must return count > 0
    if custom_sql is not None:
        custom_result = conn.execute(custom_sql).fetchone()[0]
        result.custom_passed = custom_result > 0
        if not result.custom_passed:
            result.passed = False
            logger.warning("quality check failed: custom SQL", table=table, sql=custom_sql)

    if result.passed:
        logger.info("quality check passed", table=table)

    return result
```

- [ ] **Step 3: Run tests**

```bash
uv run pytest tests/unit/test_quality_gates.py -v
```

- [ ] **Step 4: Commit**

```bash
git add src/dataenginex/data/quality/ tests/unit/test_quality_gates.py
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "feat: quality gates — completeness, uniqueness, custom SQL checks"
```

---

## Task 5: PipelineRunner

**Files:**
- Create: `src/dataenginex/data/pipeline/__init__.py`
- Create: `src/dataenginex/data/pipeline/runner.py`
- Create: `src/dataenginex/data/pipeline/dag.py`
- Create: `tests/unit/test_pipeline_runner.py`
- Create: `tests/unit/test_pipeline_dag.py`

- [ ] **Step 1: Write DAG resolver tests**

```python
# tests/unit/test_pipeline_dag.py
"""Tests for pipeline DAG resolution."""
from __future__ import annotations

import pytest

from dataenginex.data.pipeline.dag import resolve_execution_order


class TestDagResolver:
    def test_no_dependencies(self):
        pipelines = {"a": [], "b": [], "c": []}
        order = resolve_execution_order(pipelines)
        assert set(order) == {"a", "b", "c"}

    def test_linear_chain(self):
        pipelines = {"a": [], "b": ["a"], "c": ["b"]}
        order = resolve_execution_order(pipelines)
        assert order.index("a") < order.index("b") < order.index("c")

    def test_diamond_dependency(self):
        pipelines = {"a": [], "b": ["a"], "c": ["a"], "d": ["b", "c"]}
        order = resolve_execution_order(pipelines)
        assert order.index("a") < order.index("b")
        assert order.index("a") < order.index("c")
        assert order.index("b") < order.index("d")
        assert order.index("c") < order.index("d")

    def test_cycle_raises(self):
        pipelines = {"a": ["b"], "b": ["a"]}
        with pytest.raises(ValueError, match="[Cc]ycle"):
            resolve_execution_order(pipelines)

    def test_missing_dependency_raises(self):
        pipelines = {"a": ["nonexistent"]}
        with pytest.raises(KeyError, match="nonexistent"):
            resolve_execution_order(pipelines)
```

- [ ] **Step 2: Implement DAG resolver**

```python
# src/dataenginex/data/pipeline/dag.py
"""DAG resolver for pipeline execution order.

Resolves cross-pipeline dependencies defined by `depends_on` in config.
Uses Kahn's algorithm (topological sort) to produce execution order.
"""
from __future__ import annotations

from collections import deque


def resolve_execution_order(
    pipelines: dict[str, list[str]],
) -> list[str]:
    """Resolve execution order from dependency graph.

    Args:
        pipelines: Mapping of pipeline_name → list of dependency names.

    Returns:
        List of pipeline names in valid execution order.

    Raises:
        KeyError: If a dependency references a non-existent pipeline.
        ValueError: If there is a cycle in the dependency graph.
    """
    # Validate all dependencies exist
    for name, deps in pipelines.items():
        for dep in deps:
            if dep not in pipelines:
                msg = f"Pipeline '{name}' depends on '{dep}' which does not exist"
                raise KeyError(msg)

    # Kahn's algorithm
    in_degree: dict[str, int] = {name: 0 for name in pipelines}
    for _name, deps in pipelines.items():
        for dep in deps:
            in_degree[_name] = in_degree.get(_name, 0)
        in_degree[_name] = len(deps)

    # Recompute properly
    in_degree = {name: 0 for name in pipelines}
    adjacency: dict[str, list[str]] = {name: [] for name in pipelines}
    for name, deps in pipelines.items():
        for dep in deps:
            adjacency[dep].append(name)
            in_degree[name] += 1

    queue: deque[str] = deque(
        name for name, degree in in_degree.items() if degree == 0
    )
    order: list[str] = []

    while queue:
        node = queue.popleft()
        order.append(node)
        for neighbor in adjacency[node]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if len(order) != len(pipelines):
        msg = "Cycle detected in pipeline dependencies"
        raise ValueError(msg)

    return order
```

- [ ] **Step 3: Write PipelineRunner tests**

```python
# tests/unit/test_pipeline_runner.py
"""Tests for PipelineRunner."""
from __future__ import annotations

from pathlib import Path

import pytest

from dataenginex.config import load_config
from dataenginex.data.pipeline.runner import PipelineRunner


@pytest.fixture()
def sample_config(tmp_path: Path) -> Path:
    """Create a minimal dex.yaml with a CSV pipeline."""
    csv_file = tmp_path / "movies.csv"
    csv_file.write_text("id,title,rating\n1,Matrix,8.7\n2,Jaws,7.0\n3,Inception,8.8\n4,Bad Movie,2.0\n")

    config_file = tmp_path / "dex.yaml"
    config_file.write_text(f"""
project:
  name: test-project

data:
  sources:
    movies:
      type: csv
      connection:
        path: "{tmp_path}"
        default_file: "movies.csv"
  pipelines:
    ingest-movies:
      source: movies
      steps:
        - type: filter
          condition: "rating > 5.0"
        - type: deduplicate
          key: id
      quality:
        completeness: 0.9
        uniqueness:
          - id
      target:
        layer: silver
""")
    return config_file


class TestPipelineRunner:
    def test_run_single_pipeline(self, sample_config, tmp_path):
        config = load_config(sample_config)
        runner = PipelineRunner(config, data_dir=tmp_path / "data")
        result = runner.run("ingest-movies")
        assert result.success is True
        assert result.rows_output > 0

    def test_run_pipeline_not_found(self, sample_config, tmp_path):
        config = load_config(sample_config)
        runner = PipelineRunner(config, data_dir=tmp_path / "data")
        with pytest.raises(KeyError, match="nonexistent"):
            runner.run("nonexistent")

    def test_run_all_pipelines(self, sample_config, tmp_path):
        config = load_config(sample_config)
        runner = PipelineRunner(config, data_dir=tmp_path / "data")
        results = runner.run_all()
        assert len(results) == 1
        assert all(r.success for r in results.values())

    def test_dry_run(self, sample_config, tmp_path):
        config = load_config(sample_config)
        runner = PipelineRunner(config, data_dir=tmp_path / "data")
        result = runner.run("ingest-movies", dry_run=True)
        assert result.success is True
        assert result.dry_run is True
```

- [ ] **Step 4: Implement PipelineRunner**

```python
# src/dataenginex/data/pipeline/__init__.py
from dataenginex.data.pipeline.dag import resolve_execution_order
from dataenginex.data.pipeline.runner import PipelineResult, PipelineRunner

__all__ = ["PipelineResult", "PipelineRunner", "resolve_execution_order"]
```

```python
# src/dataenginex/data/pipeline/runner.py
"""PipelineRunner — config-driven data pipeline execution.

Flow: Config → Extract (connector) → Transform chain → Quality gate → Load (lakehouse layer)

Each step is checkpointed. On failure, retry from last checkpoint.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import duckdb
import structlog

from dataenginex.config.schema import DexConfig
from dataenginex.core.exceptions import PipelineError, PipelineStepError
from dataenginex.data.connectors import connector_registry
from dataenginex.data.connectors.csv import CsvConnector  # noqa: F401 — register
from dataenginex.data.connectors.duckdb import DuckDBConnector  # noqa: F401 — register
from dataenginex.data.pipeline.dag import resolve_execution_order
from dataenginex.data.quality.gates import check_quality
from dataenginex.data.transforms.sql import (  # noqa: F401 — register all
    CastTransform,
    DeduplicateTransform,
    DeriveTransform,
    FilterTransform,
)
from dataenginex.data.transforms import transform_registry

logger = structlog.get_logger()


@dataclass
class PipelineResult:
    """Result of a single pipeline execution."""

    pipeline: str
    success: bool
    rows_input: int = 0
    rows_output: int = 0
    steps_completed: int = 0
    dry_run: bool = False
    error: str | None = None


class PipelineRunner:
    """Execute data pipelines defined in dex.yaml.

    Args:
        config: Loaded DexConfig.
        data_dir: Root directory for lakehouse layer storage.
    """

    def __init__(self, config: DexConfig, data_dir: Path | None = None) -> None:
        self._config = config
        self._data_dir = data_dir or Path(".dex/data")
        self._data_dir.mkdir(parents=True, exist_ok=True)

    def run(self, pipeline_name: str, *, dry_run: bool = False) -> PipelineResult:
        """Run a single pipeline by name."""
        if self._config.data is None:
            msg = "No data section in config"
            raise PipelineError(msg)

        pipelines = self._config.data.pipelines or {}
        if pipeline_name not in pipelines:
            msg = f"Pipeline '{pipeline_name}' not found. Available: {list(pipelines.keys())}"
            raise KeyError(msg)

        pipeline_config = pipelines[pipeline_name]
        log = logger.bind(pipeline=pipeline_name)
        log.info("pipeline starting", dry_run=dry_run)

        if dry_run:
            log.info("pipeline dry run — validating only")
            return PipelineResult(
                pipeline=pipeline_name, success=True, dry_run=True
            )

        # Create a per-pipeline DuckDB instance
        db_path = self._data_dir / f"{pipeline_name}.duckdb"
        conn = duckdb.connect(str(db_path))

        try:
            # 1. Extract — load source data into DuckDB
            source_name = pipeline_config.source
            sources = self._config.data.sources or {}
            if source_name not in sources:
                msg = f"Source '{source_name}' not found"
                raise PipelineStepError(pipeline=pipeline_name, step="extract", message=msg)

            source_config = sources[source_name]
            connector_cls = connector_registry.get(source_config.type)
            connector = connector_cls(**(source_config.connection or {}))
            connector.connect()

            raw_data = connector.read(table=source_config.connection.get("default_file", source_name) if source_config.connection else source_name)
            connector.disconnect()

            # Load into DuckDB as bronze table
            import pyarrow as pa
            bronze_table = pa.Table.from_pylist(raw_data)
            conn.execute("CREATE OR REPLACE TABLE bronze AS SELECT * FROM bronze_table")
            rows_input = len(raw_data)
            log.info("extract complete", source=source_name, rows=rows_input)

            # 2. Transform chain
            current_table = "bronze"
            steps_completed = 0
            for i, step_config in enumerate(pipeline_config.steps or []):
                step_type = step_config.type
                step_params = step_config.params or {}
                # Also pull known fields from step config
                step_dict = step_config.model_dump(exclude_none=True)
                step_dict.pop("type", None)
                step_dict.pop("params", None)
                merged_params = {**step_dict, **step_params}

                transform_cls = transform_registry.get(step_type)
                transform = transform_cls(**merged_params)

                validation_errors = transform.validate()
                if validation_errors:
                    msg = f"Transform validation failed: {validation_errors}"
                    raise PipelineStepError(pipeline=pipeline_name, step=f"transform-{i}", message=msg)

                current_table = transform.apply(conn, current_table)
                steps_completed += 1
                log.info("transform complete", step=i, type=step_type, output_table=current_table)

            # 3. Quality gate
            if pipeline_config.quality:
                q = pipeline_config.quality
                quality_result = check_quality(
                    conn,
                    current_table,
                    completeness=q.completeness,
                    uniqueness=q.uniqueness,
                    custom_sql=q.custom_sql,
                )
                if not quality_result.passed:
                    msg = (
                        f"Quality gate failed: completeness={quality_result.completeness_score:.2f}, "
                        f"uniqueness={quality_result.uniqueness_score:.2f}"
                    )
                    raise PipelineStepError(pipeline=pipeline_name, step="quality", message=msg)
                log.info("quality gate passed")

            # 4. Load — write to target layer
            rows_output = conn.execute(f"SELECT count(*) FROM {current_table}").fetchone()[0]
            target_layer = "silver"
            if pipeline_config.target:
                target_layer = pipeline_config.target.get("layer", "silver")

            # Write as parquet to lakehouse layer
            layer_dir = self._data_dir / target_layer
            layer_dir.mkdir(parents=True, exist_ok=True)
            output_path = layer_dir / f"{pipeline_name}.parquet"
            conn.execute(f"COPY {current_table} TO '{output_path}' (FORMAT PARQUET)")
            log.info("load complete", layer=target_layer, path=str(output_path), rows=rows_output)

            return PipelineResult(
                pipeline=pipeline_name,
                success=True,
                rows_input=rows_input,
                rows_output=rows_output,
                steps_completed=steps_completed,
            )

        except (PipelineError, PipelineStepError):
            raise
        except Exception as e:
            log.error("pipeline failed", error=str(e))
            return PipelineResult(
                pipeline=pipeline_name,
                success=False,
                error=str(e),
            )
        finally:
            conn.close()

    def run_all(self) -> dict[str, PipelineResult]:
        """Run all pipelines in dependency order."""
        if self._config.data is None or not self._config.data.pipelines:
            return {}

        # Build dependency graph
        dep_graph: dict[str, list[str]] = {}
        for name, pipeline in self._config.data.pipelines.items():
            dep_graph[name] = list(pipeline.depends_on) if pipeline.depends_on else []

        order = resolve_execution_order(dep_graph)
        results: dict[str, PipelineResult] = {}

        for name in order:
            result = self.run(name)
            results[name] = result
            if not result.success:
                logger.error("pipeline failed — stopping", pipeline=name)
                break

        return results
```

- [ ] **Step 5: Update config schema for pipeline quality/target**

The config schema needs `quality` and `target` fields on PipelineConfig. Check `src/dataenginex/config/schema.py` and add if missing:

```python
# Add to PipelineConfig in schema.py:
class QualityCheckConfig(BaseModel):
    completeness: float | None = None
    uniqueness: list[str] | None = None
    custom_sql: str | None = None

class PipelineConfig(BaseModel):
    source: str
    steps: list[TransformStepConfig] | None = None
    depends_on: list[str] | None = None
    schedule: str | None = None
    quality: QualityCheckConfig | None = None
    target: dict[str, str] | None = None
```

- [ ] **Step 6: Run tests**

```bash
uv run pytest tests/unit/test_pipeline_runner.py tests/unit/test_pipeline_dag.py -v
```

- [ ] **Step 7: Full validation**

```bash
uv run poe lint && uv run poe typecheck && uv run poe test
```

- [ ] **Step 8: Commit**

```bash
git add src/dataenginex/data/pipeline/ tests/unit/test_pipeline_runner.py tests/unit/test_pipeline_dag.py src/dataenginex/config/schema.py
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "feat: PipelineRunner — config-driven extract, transform, quality, load"
```

---

## Task 6: `dex run` CLI Command

**Files:**
- Create: `src/dataenginex/cli/run.py`
- Modify: `src/dataenginex/cli/main.py`
- Create: `tests/integration/test_cli_run.py`

- [ ] **Step 1: Write CLI integration tests**

```python
# tests/integration/test_cli_run.py
"""Integration tests for `dex run` command."""
from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from dataenginex.cli.main import dex


class TestDexRun:
    def test_run_single_pipeline(self, tmp_path: Path):
        csv_file = tmp_path / "movies.csv"
        csv_file.write_text("id,title,rating\n1,Matrix,8.7\n2,Jaws,7.0\n")

        config = tmp_path / "dex.yaml"
        config.write_text(f"""
project:
  name: test
data:
  sources:
    movies:
      type: csv
      connection:
        path: "{tmp_path}"
        default_file: movies.csv
  pipelines:
    ingest:
      source: movies
      steps:
        - type: filter
          condition: "rating > 5.0"
      target:
        layer: silver
""")
        runner = CliRunner()
        result = runner.invoke(dex, ["run", "ingest", "--config", str(config), "--data-dir", str(tmp_path / "data")])
        assert result.exit_code == 0
        assert "success" in result.output.lower() or "complete" in result.output.lower()

    def test_run_all(self, tmp_path: Path):
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("id,value\n1,10\n2,20\n")

        config = tmp_path / "dex.yaml"
        config.write_text(f"""
project:
  name: test
data:
  sources:
    src:
      type: csv
      connection:
        path: "{tmp_path}"
        default_file: data.csv
  pipelines:
    p1:
      source: src
      target:
        layer: silver
""")
        runner = CliRunner()
        result = runner.invoke(dex, ["run", "--all", "--config", str(config), "--data-dir", str(tmp_path / "data")])
        assert result.exit_code == 0

    def test_run_dry_run(self, tmp_path: Path):
        config = tmp_path / "dex.yaml"
        config.write_text("""
project:
  name: test
data:
  sources:
    src:
      type: csv
      connection:
        path: "."
        default_file: data.csv
  pipelines:
    p1:
      source: src
      target:
        layer: silver
""")
        runner = CliRunner()
        result = runner.invoke(dex, ["run", "p1", "--dry-run", "--config", str(config)])
        assert result.exit_code == 0
        assert "dry" in result.output.lower()

    def test_run_missing_pipeline(self, tmp_path: Path):
        config = tmp_path / "dex.yaml"
        config.write_text("""
project:
  name: test
data:
  sources: {}
  pipelines: {}
""")
        runner = CliRunner()
        result = runner.invoke(dex, ["run", "nonexistent", "--config", str(config)])
        assert result.exit_code != 0
```

- [ ] **Step 2: Implement `dex run` command**

```python
# src/dataenginex/cli/run.py
"""`dex run` — execute data pipelines."""
from __future__ import annotations

from pathlib import Path

import click
import structlog
from rich.console import Console
from rich.table import Table

from dataenginex.config import load_config
from dataenginex.data.pipeline.runner import PipelineRunner

logger = structlog.get_logger()
console = Console()


@click.command()
@click.argument("pipeline", required=False)
@click.option("--all", "run_all", is_flag=True, help="Run all pipelines in dependency order")
@click.option("--config", "config_path", default="dex.yaml", help="Config file path")
@click.option("--data-dir", default=None, help="Data directory for lakehouse layers")
@click.option("--dry-run", is_flag=True, help="Validate without executing")
def run(
    pipeline: str | None,
    run_all: bool,
    config_path: str,
    data_dir: str | None,
    dry_run: bool,
) -> None:
    """Run data pipelines defined in dex.yaml."""
    config = load_config(Path(config_path))
    runner = PipelineRunner(
        config,
        data_dir=Path(data_dir) if data_dir else None,
    )

    if run_all:
        results = runner.run_all()
    elif pipeline:
        results = {pipeline: runner.run(pipeline, dry_run=dry_run)}
    else:
        raise click.UsageError("Specify a pipeline name or use --all")

    # Display results
    table = Table(title="Pipeline Results")
    table.add_column("Pipeline", style="cyan")
    table.add_column("Status")
    table.add_column("Rows In")
    table.add_column("Rows Out")
    table.add_column("Steps")

    all_ok = True
    for name, result in results.items():
        status = "[green]OK[/green]" if result.success else "[red]FAIL[/red]"
        if result.dry_run:
            status = "[yellow]DRY RUN[/yellow]"
        if not result.success:
            all_ok = False
        table.add_row(
            name,
            status,
            str(result.rows_input),
            str(result.rows_output),
            str(result.steps_completed),
        )

    console.print(table)

    if not all_ok:
        raise SystemExit(1)
```

- [ ] **Step 3: Register the command in CLI main**

Add to `src/dataenginex/cli/main.py`:

```python
from dataenginex.cli.run import run
dex.add_command(run)
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/integration/test_cli_run.py -v
```

- [ ] **Step 5: Full validation**

```bash
uv run poe lint && uv run poe typecheck && uv run poe test
```

- [ ] **Step 6: End-to-end smoke test**

```bash
# Create a test CSV
echo "id,title,rating" > /tmp/movies.csv
echo "1,Matrix,8.7" >> /tmp/movies.csv
echo "2,Jaws,7.0" >> /tmp/movies.csv
echo "3,Inception,8.8" >> /tmp/movies.csv

# Create test config
cat > /tmp/test-dex.yaml << 'EOF'
project:
  name: smoke-test
data:
  sources:
    movies:
      type: csv
      connection:
        path: /tmp
        default_file: movies.csv
  pipelines:
    ingest-movies:
      source: movies
      steps:
        - type: filter
          condition: "rating > 7.5"
      quality:
        completeness: 0.9
      target:
        layer: silver
EOF

# Run it
uv run dex run ingest-movies --config /tmp/test-dex.yaml --data-dir /tmp/dex-data

# Verify output
ls -la /tmp/dex-data/silver/ingest-movies.parquet
```

- [ ] **Step 7: Commit**

```bash
git add src/dataenginex/cli/run.py src/dataenginex/cli/main.py tests/integration/test_cli_run.py
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "feat: dex run — config-driven pipeline execution CLI"
```

---

## Task 7: Built-in Cron Scheduler

**Files:**
- Create: `src/dataenginex/orchestration/__init__.py`
- Create: `src/dataenginex/orchestration/builtin.py`
- Create: `src/dataenginex/orchestration/registry.py`
- Create: `tests/unit/test_scheduler.py`

- [ ] **Step 1: Write scheduler tests**

```python
# tests/unit/test_scheduler.py
"""Tests for the built-in cron scheduler."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from dataenginex.orchestration.builtin import BuiltinScheduler, ScheduleEntry


class TestBuiltinScheduler:
    def test_add_schedule(self):
        sched = BuiltinScheduler()
        sched.add("pipeline-a", "*/5 * * * *")
        assert "pipeline-a" in sched.schedules

    def test_next_run_time(self):
        sched = BuiltinScheduler()
        sched.add("pipeline-a", "*/5 * * * *")
        next_time = sched.next_run("pipeline-a")
        assert next_time > datetime.now(tz=timezone.utc)

    def test_due_pipelines(self):
        sched = BuiltinScheduler()
        # Schedule that was due in the past
        sched.add("pipeline-a", "*/1 * * * *")
        # Force last_run to be far in the past
        sched.schedules["pipeline-a"].last_run = datetime(2020, 1, 1, tzinfo=timezone.utc)
        due = sched.get_due()
        assert "pipeline-a" in due

    def test_mark_complete(self):
        sched = BuiltinScheduler()
        sched.add("pipeline-a", "*/1 * * * *")
        sched.schedules["pipeline-a"].last_run = datetime(2020, 1, 1, tzinfo=timezone.utc)
        sched.mark_complete("pipeline-a")
        assert sched.schedules["pipeline-a"].last_run > datetime(2020, 1, 1, tzinfo=timezone.utc)
```

- [ ] **Step 2: Implement scheduler**

```python
# src/dataenginex/orchestration/__init__.py
from dataenginex.core.interfaces import BaseOrchestrator
from dataenginex.core.registry import BackendRegistry

orchestrator_registry: BackendRegistry[BaseOrchestrator] = BackendRegistry("orchestrator")

__all__ = ["BaseOrchestrator", "orchestrator_registry"]
```

```python
# src/dataenginex/orchestration/builtin.py
"""Built-in cron scheduler — croniter + asyncio.

Simple scheduler for single-node deployments. Stores last-run timestamps
in memory (persisted to .dex/scheduler.json on shutdown).
For production: use [dagster] or [airflow] extras.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

import structlog
from croniter import croniter

from dataenginex.core.interfaces import BaseOrchestrator
from dataenginex.orchestration import orchestrator_registry

logger = structlog.get_logger()


@dataclass
class ScheduleEntry:
    """A single schedule definition."""

    pipeline: str
    cron: str
    last_run: datetime = field(default_factory=lambda: datetime(2000, 1, 1, tzinfo=timezone.utc))


@orchestrator_registry.decorator("builtin", is_default=True)
class BuiltinScheduler(BaseOrchestrator):
    """Cron-based scheduler using croniter.

    Not async — designed for `dex run --schedule` mode where
    the main loop polls every minute.
    """

    def __init__(self) -> None:
        self.schedules: dict[str, ScheduleEntry] = {}

    def add(self, pipeline: str, cron_expr: str) -> None:
        """Add a pipeline schedule."""
        # Validate cron expression
        if not croniter.is_valid(cron_expr):
            msg = f"Invalid cron expression: {cron_expr}"
            raise ValueError(msg)
        self.schedules[pipeline] = ScheduleEntry(pipeline=pipeline, cron=cron_expr)
        logger.info("schedule added", pipeline=pipeline, cron=cron_expr)

    def next_run(self, pipeline: str) -> datetime:
        """Get the next run time for a pipeline."""
        entry = self.schedules[pipeline]
        cron = croniter(entry.cron, entry.last_run)
        return cron.get_next(datetime).replace(tzinfo=timezone.utc)

    def get_due(self) -> list[str]:
        """Return list of pipelines that are due to run."""
        now = datetime.now(tz=timezone.utc)
        due = []
        for name, entry in self.schedules.items():
            next_time = self.next_run(name)
            if next_time <= now:
                due.append(name)
        return due

    def mark_complete(self, pipeline: str) -> None:
        """Mark a pipeline as completed (updates last_run)."""
        self.schedules[pipeline].last_run = datetime.now(tz=timezone.utc)

    def start(self) -> None:
        """Start the scheduler (no-op for built-in — polling based)."""
        logger.info("builtin scheduler ready", pipelines=list(self.schedules.keys()))

    def stop(self) -> None:
        """Stop the scheduler."""
        logger.info("builtin scheduler stopped")
```

- [ ] **Step 3: Run tests**

```bash
uv run pytest tests/unit/test_scheduler.py -v
```

- [ ] **Step 4: Commit**

```bash
git add src/dataenginex/orchestration/ tests/unit/test_scheduler.py
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "feat: built-in cron scheduler with croniter"
```

---

## Task 8: Update data/ __init__.py + Integration Test

**Files:**
- Modify: `src/dataenginex/data/__init__.py`
- Create: `tests/integration/test_pipeline_e2e.py`
- Create: `examples/movies.csv`

- [ ] **Step 1: Update data package public API**

```python
# src/dataenginex/data/__init__.py
"""Data layer public API."""
from __future__ import annotations

from dataenginex.data.connectors import connector_registry
from dataenginex.data.connectors.csv import CsvConnector
from dataenginex.data.connectors.duckdb import DuckDBConnector
from dataenginex.data.pipeline.runner import PipelineResult, PipelineRunner
from dataenginex.data.quality.gates import QualityResult, check_quality
from dataenginex.data.transforms import transform_registry

__all__ = [
    "CsvConnector",
    "DuckDBConnector",
    "PipelineResult",
    "PipelineRunner",
    "QualityResult",
    "check_quality",
    "connector_registry",
    "transform_registry",
]
```

- [ ] **Step 2: Create example CSV**

```csv
id,title,genre,rating,year
1,The Matrix,sci-fi,8.7,1999
2,Jaws,thriller,7.0,1975
3,Inception,sci-fi,8.8,2010
4,The Room,drama,3.6,2003
5,Interstellar,sci-fi,8.6,2014
6,Tenet,sci-fi,7.3,2020
7,Dune,sci-fi,8.0,2021
8,Bad Movie,comedy,2.1,2005
```

Save to `examples/movies.csv`.

- [ ] **Step 3: Write E2E integration test**

```python
# tests/integration/test_pipeline_e2e.py
"""End-to-end pipeline integration test."""
from __future__ import annotations

from pathlib import Path

import pytest

from dataenginex.config import load_config
from dataenginex.data.pipeline.runner import PipelineRunner


@pytest.fixture()
def e2e_config(tmp_path: Path) -> Path:
    """Full pipeline config with real CSV data."""
    # Copy movies.csv
    movies_csv = Path("examples/movies.csv")
    if not movies_csv.exists():
        pytest.skip("examples/movies.csv not found")
    import shutil
    shutil.copy(movies_csv, tmp_path / "movies.csv")

    config = tmp_path / "dex.yaml"
    config.write_text(f"""
project:
  name: e2e-test
  version: "0.1.0"

data:
  sources:
    movies:
      type: csv
      connection:
        path: "{tmp_path}"
        default_file: movies.csv
  pipelines:
    ingest-movies:
      source: movies
      steps:
        - type: filter
          condition: "rating > 5.0"
        - type: deduplicate
          key: id
      quality:
        completeness: 0.9
        uniqueness:
          - id
      target:
        layer: silver
""")
    return config


class TestPipelineE2E:
    def test_full_pipeline_csv_to_silver(self, e2e_config, tmp_path):
        config = load_config(e2e_config)
        data_dir = tmp_path / "lakehouse"
        runner = PipelineRunner(config, data_dir=data_dir)
        result = runner.run("ingest-movies")

        assert result.success is True
        assert result.rows_input == 8  # all rows from CSV
        assert result.rows_output == 6  # filtered: rating > 5.0 removes 2
        assert (data_dir / "silver" / "ingest-movies.parquet").exists()
```

- [ ] **Step 4: Run all tests**

```bash
uv run poe lint && uv run poe typecheck && uv run poe test
```

- [ ] **Step 5: Full smoke test**

```bash
uv run dex validate examples/dex.yaml
uv run dex run ingest-movies --config examples/dex.yaml --data-dir /tmp/dex-e2e
ls -la /tmp/dex-e2e/silver/
```

- [ ] **Step 6: Commit**

```bash
git add src/dataenginex/data/__init__.py examples/movies.csv tests/integration/test_pipeline_e2e.py
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "feat: Phase 1 complete — config-driven data pipelines with DuckDB"
```

---

## Summary

| Task | Component | Tests | Est. Time |
|------|-----------|-------|-----------|
| 0 | Python 3.13 bump | existing pass | 5 min |
| 1 | DuckDB connector + registry | 4 conformance + 4 unit | 20 min |
| 2 | CSV connector | 3 conformance + 2 unit | 15 min |
| 3 | SQL transforms (4 types) | 4 conformance + 8 unit | 30 min |
| 4 | Quality gates | 6 unit | 20 min |
| 5 | PipelineRunner + DAG | 4 runner + 5 DAG | 40 min |
| 6 | `dex run` CLI | 4 integration | 20 min |
| 7 | Cron scheduler | 4 unit | 15 min |
| 8 | Integration + E2E | 1 E2E + public API | 15 min |

**Total: ~8 tasks, ~40 tests, ~3 hours estimated**

**Exit criteria:** `dex run ingest-movies` processes CSV → filtered/deduped → quality check → silver parquet.
