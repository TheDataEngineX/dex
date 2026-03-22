"""Data quality gates — completeness, uniqueness, custom SQL checks.

Quality gates run after transforms and before loading to the target layer.
They use DuckDB SQL aggregations for speed (no row-by-row Python).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import duckdb
import structlog

logger = structlog.get_logger()


@dataclass
class QualityResult:
    """Result of a quality gate check."""

    passed: bool
    completeness_score: float = 1.0
    uniqueness_score: float = 1.0
    custom_passed: bool = True
    details: dict[str, Any] = field(default_factory=dict)


def _check_completeness(
    conn: duckdb.DuckDBPyConnection,
    table: str,
    threshold: float,
    total_rows: int,
    result: QualityResult,
) -> None:
    """Check non-null ratio across all columns."""
    cols = [row[0] for row in conn.execute(f"DESCRIBE {table}").fetchall()]
    total_nulls = 0
    for c in cols:
        row = conn.execute(f"SELECT count(*) FROM {table} WHERE {c} IS NULL").fetchone()
        total_nulls += int(row[0]) if row else 0
    total_cells = total_rows * len(cols)
    score = (total_cells - total_nulls) / total_cells if total_cells > 0 else 1.0
    result.completeness_score = score
    if score < threshold:
        result.passed = False
        logger.warning(
            "quality check failed: completeness",
            table=table, score=round(score, 4), threshold=threshold,
        )


def _check_uniqueness(
    conn: duckdb.DuckDBPyConnection,
    table: str,
    columns: list[str],
    total_rows: int,
    result: QualityResult,
) -> None:
    """Check that specified columns have no duplicates."""
    key_cols = ", ".join(columns)
    distinct_row = conn.execute(
        f"SELECT count(DISTINCT ({key_cols})) FROM {table}"
    ).fetchone()
    distinct_count: int = int(distinct_row[0]) if distinct_row else 0
    score = distinct_count / total_rows if total_rows > 0 else 1.0
    result.uniqueness_score = score
    if distinct_count < total_rows:
        result.passed = False
        logger.warning(
            "quality check failed: uniqueness",
            table=table, columns=columns,
            distinct=distinct_count, total=total_rows,
        )


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
    count_row = conn.execute(f"SELECT count(*) FROM {table}").fetchone()
    total_rows: int = int(count_row[0]) if count_row else 0

    if total_rows == 0:
        logger.info("quality check: empty table — passing vacuously", table=table)
        return result

    if completeness is not None:
        _check_completeness(conn, table, completeness, total_rows, result)

    if uniqueness is not None:
        _check_uniqueness(conn, table, uniqueness, total_rows, result)

    if custom_sql is not None:
        custom_row = conn.execute(custom_sql).fetchone()
        custom_result = int(custom_row[0]) if custom_row else 0
        result.custom_passed = custom_result > 0
        if not result.custom_passed:
            result.passed = False
            logger.warning("quality check failed: custom SQL", table=table)

    if result.passed:
        logger.info("quality check passed", table=table)

    return result
