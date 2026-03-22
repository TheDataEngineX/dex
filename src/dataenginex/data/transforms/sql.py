"""DuckDB SQL-based transforms.

All transforms execute SQL against a DuckDB connection and return
the name of the output table. Each transform is registered in the transform_registry.
The PipelineRunner chains them: input_table -> transform1 -> transform2 -> ...
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
        sql = (
            f"CREATE OR REPLACE TABLE {output} AS "
            f"SELECT * FROM {input_table} WHERE {self._condition}"
        )
        conn.execute(sql)
        count_row = conn.execute(f"SELECT count(*) FROM {output}").fetchone()
        count = int(count_row[0]) if count_row else 0
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
        self._col_name = name
        self._expression = expression

    def apply(self, conn: duckdb.DuckDBPyConnection, input_table: str) -> str:
        output = f"{input_table}_derived"
        sql = (
            f"CREATE OR REPLACE TABLE {output} AS "
            f"SELECT *, ({self._expression}) AS {self._col_name} FROM {input_table}"
        )
        conn.execute(sql)
        logger.info("derive applied", column=self._col_name, expression=self._expression)
        return output

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self._col_name.strip():
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
        conn.execute(f"""
            CREATE OR REPLACE TABLE {output} AS
            SELECT * FROM (
                SELECT *, ROW_NUMBER() OVER (PARTITION BY {key_cols} ORDER BY rowid) AS _rn
                FROM {input_table}
            ) WHERE _rn = 1
        """)
        conn.execute(f"ALTER TABLE {output} DROP COLUMN _rn")
        before_row = conn.execute(f"SELECT count(*) FROM {input_table}").fetchone()
        before = int(before_row[0]) if before_row else 0
        after_row = conn.execute(f"SELECT count(*) FROM {output}").fetchone()
        after = int(after_row[0]) if after_row else 0
        logger.info(
            "deduplicate applied", key=self._key,
            before=before, after=after, removed=before - after,
        )
        return output

    def validate(self) -> list[str]:
        if not self._key:
            return ["deduplicate requires at least one key column"]
        return []
