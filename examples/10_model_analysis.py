#!/usr/bin/env python
"""10_model_analysis.py — Drift detection and prediction analysis.

Demonstrates:
- Loading a trained PySpark ML model
- Computing prediction error metrics (MAE, RMSE, error %)
- Grouping performance by city, hour, day-of-week, and weather condition
- Using the DEX DriftDetector (PSI-based) for feature drift monitoring

Requirements:
    uv sync --group data  # installs pyspark

Run:
    uv run python examples/10_model_analysis.py

    # Optional: train a model first with example 08:
    uv run python examples/08_spark_ml.py
"""

from __future__ import annotations

import structlog

logger = structlog.get_logger()

try:
    import pyspark.sql
    from pyspark.sql import SparkSession
    from pyspark.sql.functions import abs as spark_abs
    from pyspark.sql.functions import col
    from pyspark.sql.functions import round as spark_round

    _HAS_PYSPARK = True
except ImportError:
    _HAS_PYSPARK = False


def create_spark() -> SparkSession:
    return (
        SparkSession.builder.master("local[2]")
        .appName("DEX-ModelAnalysis")
        .config("spark.ui.enabled", "false")
        .config("spark.driver.bindAddress", "127.0.0.1")
        .config("spark.sql.ansi.enabled", "true")
        .getOrCreate()
    )


def build_mock_predictions(spark: SparkSession) -> pyspark.sql.DataFrame:  # type: ignore[name-defined]
    """Build synthetic prediction results (actual vs predicted temperature)."""
    rows = [
        ("Seattle", "2025-01-01T00:00:00", 8.0, 7.8, "Drizzle", 3, 1),
        ("Seattle", "2025-01-01T06:00:00", 6.5, 7.1, "Drizzle", 9, 1),
        ("Seattle", "2025-01-01T12:00:00", 10.2, 9.5, "Clouds", 15, 1),
        ("Seattle", "2025-01-01T18:00:00", 9.1, 9.3, "Rain", 21, 1),
        ("Seattle", "2025-01-02T00:00:00", 7.3, 6.9, "Rain", 3, 2),
        ("Austin", "2025-01-01T00:00:00", 22.0, 21.5, "Clear", 3, 1),
        ("Austin", "2025-01-01T06:00:00", 20.5, 21.0, "Clear", 9, 1),
        ("Austin", "2025-01-01T12:00:00", 28.7, 27.2, "Clear", 15, 1),
        ("Austin", "2025-01-01T18:00:00", 26.3, 25.8, "Clouds", 21, 1),
        ("Austin", "2025-01-02T00:00:00", 21.1, 22.3, "Clear", 3, 2),
    ]
    columns = ["city", "timestamp", "temperature", "prediction", "condition", "hour", "day_of_week"]
    return spark.createDataFrame(rows, schema=columns)


def compute_error_metrics(df: pyspark.sql.DataFrame) -> pyspark.sql.DataFrame:  # type: ignore[name-defined]
    """Add error, absolute error, and error percentage columns."""
    df = df.withColumn("error", col("temperature") - col("prediction"))
    df = df.withColumn("abs_error", spark_abs(col("error")))
    df = df.withColumn(
        "error_pct", spark_round(spark_abs(col("error")) / col("temperature") * 100, 2)
    )
    return df


def performance_by_city(df: pyspark.sql.DataFrame) -> None:  # type: ignore[name-defined]
    logger.info("=== Performance by City ===")
    df.groupBy("city").agg({"abs_error": "avg", "temperature": "count"}).withColumnRenamed(
        "avg(abs_error)", "mean_abs_error"
    ).show()


def performance_by_hour(df: pyspark.sql.DataFrame) -> None:  # type: ignore[name-defined]
    logger.info("=== Performance by Hour of Day ===")
    df.groupBy("hour").agg({"abs_error": "avg"}).orderBy("hour").show()


def performance_by_condition(df: pyspark.sql.DataFrame) -> None:  # type: ignore[name-defined]
    logger.info("=== Performance by Weather Condition ===")
    df.groupBy("condition").agg({"abs_error": "avg"}).orderBy("avg(abs_error)").show()


def best_and_worst(df: pyspark.sql.DataFrame, n: int = 3) -> None:  # type: ignore[name-defined]
    logger.info("=== Best %d Predictions ===", n)
    df.orderBy("abs_error").select(
        "city", "timestamp", "temperature", "prediction", "abs_error"
    ).limit(n).show()

    logger.info("=== Worst %d Predictions ===", n)
    df.orderBy(col("abs_error").desc()).select(
        "city", "timestamp", "temperature", "prediction", "abs_error"
    ).limit(n).show()


def drift_check(df: pyspark.sql.DataFrame) -> None:  # type: ignore[name-defined]
    """Demonstrate DEX DriftDetector with PSI-based detection."""
    from dataenginex.ml.drift import DriftDetector

    detector = DriftDetector(threshold=0.2)

    # Simulate reference and current distributions (temperature values)
    reference = [row.temperature for row in df.collect()]
    current = [row.prediction for row in df.collect()]

    result = detector.check_feature(
        reference=reference, current=current, feature_name="temperature"
    )
    logger.info(
        "Drift detection: feature=temperature psi=%.4f drifted=%s",
        result.psi,
        result.drift_detected,
    )


def summary_stats(df: pyspark.sql.DataFrame) -> None:  # type: ignore[name-defined]
    avg_err = df.agg({"abs_error": "avg"}).collect()[0][0]
    max_err = df.agg({"abs_error": "max"}).collect()[0][0]
    total = df.count()
    logger.info("=== Summary ===")
    logger.info("Average Absolute Error: %.4f°C", avg_err)
    logger.info("Max Absolute Error:     %.4f°C", max_err)
    logger.info("Total Predictions:      %d", total)


def main() -> None:
    if not _HAS_PYSPARK:
        logger.warning("PySpark not installed — skipping. Install with: uv sync --group data")
        return

    spark = create_spark()
    try:
        logger.info("Building mock prediction results")
        predictions = build_mock_predictions(spark)

        logger.info("Computing error metrics")
        predictions = compute_error_metrics(predictions)

        performance_by_city(predictions)
        performance_by_hour(predictions)
        performance_by_condition(predictions)
        best_and_worst(predictions, n=3)
        summary_stats(predictions)

        logger.info("Running drift detection")
        drift_check(predictions)

        logger.info("Model analysis complete")
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
