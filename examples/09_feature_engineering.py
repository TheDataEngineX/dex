#!/usr/bin/env python
"""09_feature_engineering.py — Feature engineering pipeline for weather ML.

Demonstrates:
- Time-based feature extraction (hour, day-of-week, month)
- Lag features for temporal patterns
- Rolling window statistics (mean, std)
- Interaction feature construction
- Using the DEX DataProfiler to summarise the engineered features

Requirements:
    uv sync --group data  # installs pyspark

Run:
    uv run python examples/09_feature_engineering.py
"""

from __future__ import annotations

from loguru import logger

try:
    import pyspark.sql
    from pyspark.sql import SparkSession
    from pyspark.sql.functions import avg, col, dayofweek, hour, lag, month, stddev, unix_timestamp
    from pyspark.sql.window import Window

    _HAS_PYSPARK = True
except ImportError:
    _HAS_PYSPARK = False


def create_spark() -> SparkSession:
    return (
        SparkSession.builder.master("local[2]")
        .appName("DEX-FeatureEngineering")
        .config("spark.ui.enabled", "false")
        .config("spark.driver.bindAddress", "127.0.0.1")
        .config("spark.sql.ansi.enabled", "true")
        .getOrCreate()
    )


def build_sample_data(spark: SparkSession) -> pyspark.sql.DataFrame:  # type: ignore[name-defined]
    """Create sample weather records spanning two cities over two days."""
    rows = [
        ("Seattle", "2025-01-01T00:00:00", 8.0, 82, 1013, 5.2, 90, 8.0),
        ("Seattle", "2025-01-01T06:00:00", 6.5, 85, 1012, 4.8, 95, 7.0),
        ("Seattle", "2025-01-01T12:00:00", 10.2, 78, 1014, 6.0, 70, 9.5),
        ("Seattle", "2025-01-01T18:00:00", 9.1, 80, 1013, 5.5, 80, 8.5),
        ("Seattle", "2025-01-02T00:00:00", 7.3, 83, 1011, 4.2, 92, 7.5),
        ("Seattle", "2025-01-02T06:00:00", 5.8, 87, 1010, 3.9, 97, 6.0),
        ("Austin", "2025-01-01T00:00:00", 22.0, 55, 1008, 3.1, 5, 15.0),
        ("Austin", "2025-01-01T06:00:00", 20.5, 58, 1009, 2.8, 10, 14.5),
        ("Austin", "2025-01-01T12:00:00", 28.7, 45, 1007, 4.0, 3, 16.0),
        ("Austin", "2025-01-01T18:00:00", 26.3, 50, 1008, 3.5, 8, 15.5),
        ("Austin", "2025-01-02T00:00:00", 21.1, 57, 1009, 2.5, 12, 14.0),
        ("Austin", "2025-01-02T06:00:00", 19.8, 60, 1010, 2.2, 15, 13.5),
    ]
    columns = [
        "city",
        "timestamp",
        "temperature",
        "humidity",
        "pressure",
        "wind_speed",
        "cloudiness",
        "visibility",
    ]
    return spark.createDataFrame(rows, schema=columns)


def add_time_features(df: pyspark.sql.DataFrame) -> pyspark.sql.DataFrame:  # type: ignore[name-defined]
    """Extract hour, day-of-week, and month from timestamp."""
    from pyspark.sql.functions import from_unixtime

    df = df.withColumn("ts_unix", unix_timestamp(col("timestamp"), "yyyy-MM-dd'T'HH:mm:ss"))
    df = df.withColumn("hour", hour(from_unixtime(col("ts_unix"))))
    df = df.withColumn("day_of_week", dayofweek(from_unixtime(col("ts_unix"))))
    df = df.withColumn("month", month(from_unixtime(col("ts_unix"))))
    logger.info("Time features added: hour, day_of_week, month")
    return df


def add_lag_features(
    df: pyspark.sql.DataFrame,  # type: ignore[name-defined]
    target: str = "temperature",
    lags: list[int] | None = None,
) -> pyspark.sql.DataFrame:  # type: ignore[name-defined]
    """Add lag features partitioned by city, ordered by timestamp."""
    if lags is None:
        lags = [1, 3, 6]

    window = Window.partitionBy("city").orderBy("ts_unix")
    for lag_val in lags:
        df = df.withColumn(f"{target}_lag_{lag_val}", lag(col(target), lag_val).over(window))

    logger.info("Lag features added: lags=%s target=%s", lags, target)
    return df


def add_rolling_features(
    df: pyspark.sql.DataFrame,  # type: ignore[name-defined]
    metrics: list[str] | None = None,
    window_sizes: list[int] | None = None,
) -> pyspark.sql.DataFrame:  # type: ignore[name-defined]
    """Add rolling mean and std over specified window sizes."""
    if metrics is None:
        metrics = ["temperature", "humidity", "pressure"]
    if window_sizes is None:
        window_sizes = [3, 6]

    for window_size in window_sizes:
        rolling = Window.partitionBy("city").orderBy("ts_unix").rangeBetween(-(window_size - 1), 0)
        for metric in metrics:
            df = df.withColumn(
                f"{metric}_rolling_mean_{window_size}", avg(col(metric)).over(rolling)
            )
            df = df.withColumn(
                f"{metric}_rolling_std_{window_size}", stddev(col(metric)).over(rolling)
            )

    logger.info("Rolling features added: window_sizes=%s metrics=%s", window_sizes, metrics)
    return df


def add_interaction_features(df: pyspark.sql.DataFrame) -> pyspark.sql.DataFrame:  # type: ignore[name-defined]
    """Create domain-specific interaction features."""
    df = df.withColumn("temp_humidity_interaction", col("temperature") * col("humidity") / 100.0)
    df = df.withColumn("cloud_visibility_ratio", col("cloudiness") / (col("visibility") + 0.1))
    df = df.withColumn("pressure_humidity_ratio", col("pressure") * col("humidity") / 1000.0)
    logger.info("Interaction features added")
    return df


def profile_features(df: pyspark.sql.DataFrame) -> None:  # type: ignore[name-defined]
    """Print a basic summary of engineered numeric features."""
    numeric_cols = [
        "temperature",
        "humidity",
        "temp_humidity_interaction",
        "cloud_visibility_ratio",
        "temperature_lag_1",
        "temperature_rolling_mean_3",
    ]
    available = [c for c in numeric_cols if c in df.columns]
    logger.info("Feature profile (%d columns):", len(available))
    df.select(available).describe().show(truncate=False)


def main() -> None:
    if not _HAS_PYSPARK:
        logger.warning("PySpark not installed — skipping. Install with: uv sync --group data")
        return

    spark = create_spark()
    try:
        logger.info("Loading sample weather data")
        df = build_sample_data(spark)
        logger.info("Rows before feature engineering: %d", df.count())

        logger.info("Step 1/4: time features")
        df = add_time_features(df)

        logger.info("Step 2/4: lag features")
        df = add_lag_features(df, target="temperature", lags=[1, 3, 6])

        logger.info("Step 3/4: rolling window features")
        df = add_rolling_features(df, window_sizes=[3, 6])

        logger.info("Step 4/4: interaction features")
        df = add_interaction_features(df)

        df = df.dropna()
        logger.info("Rows after dropping nulls from lag: %d", df.count())

        profile_features(df)
        logger.info("Feature engineering complete — total columns: %d", len(df.columns))
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
