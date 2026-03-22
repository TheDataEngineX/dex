#!/usr/bin/env python
"""08_spark_ml.py — PySpark feature engineering and model training via ModelRegistry.

Demonstrates:
- Creating a local SparkSession
- Feature engineering: time features, lag features, rolling windows, interactions
- Training a RandomForest regression model with PySpark ML Pipeline
- Registering the model in DEX ModelRegistry

Requirements:
    uv sync --group data  # installs pyspark

Run:
    uv run python examples/08_spark_ml.py
"""

from __future__ import annotations

import structlog
logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# PySpark availability guard
# ---------------------------------------------------------------------------

try:
    import pyspark.sql
    from pyspark.ml import Pipeline
    from pyspark.ml.feature import VectorAssembler
    from pyspark.ml.regression import RandomForestRegressor
    from pyspark.sql import SparkSession
    from pyspark.sql.functions import avg, col, dayofweek, hour, lag, month, stddev, unix_timestamp
    from pyspark.sql.window import Window

    _HAS_PYSPARK = True
except ImportError:
    _HAS_PYSPARK = False


def create_spark() -> SparkSession:
    """Create a minimal local SparkSession."""
    return (
        SparkSession.builder.master("local[2]")
        .appName("DEX-SparkML-Example")
        .config("spark.ui.enabled", "false")
        .config("spark.driver.bindAddress", "127.0.0.1")
        .config("spark.sql.shuffle.partitions", "4")
        .config("spark.sql.ansi.enabled", "true")
        .getOrCreate()
    )


def build_sample_data(spark: SparkSession) -> pyspark.sql.DataFrame:  # type: ignore[name-defined]
    """Build a minimal weather DataFrame for demonstration."""
    from pyspark.sql.types import (
        DoubleType,
        IntegerType,
        StringType,
        StructField,
        StructType,
    )

    schema = StructType(
        [
            StructField("city", StringType()),
            StructField("timestamp", StringType()),
            StructField("temperature", DoubleType()),
            StructField("humidity", IntegerType()),
            StructField("pressure", IntegerType()),
            StructField("wind_speed", DoubleType()),
            StructField("cloudiness", IntegerType()),
            StructField("visibility", DoubleType()),
        ]
    )

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

    return spark.createDataFrame(rows, schema=schema)


def engineer_features(df: pyspark.sql.DataFrame) -> pyspark.sql.DataFrame:  # type: ignore[name-defined]
    """Add time, lag, rolling, and interaction features."""
    from pyspark.sql.functions import from_unixtime

    # Time features
    df = df.withColumn("ts_unix", unix_timestamp(col("timestamp"), "yyyy-MM-dd'T'HH:mm:ss"))
    df = df.withColumn("hour", hour(from_unixtime(col("ts_unix"))))
    df = df.withColumn("day_of_week", dayofweek(from_unixtime(col("ts_unix"))))
    df = df.withColumn("month", month(from_unixtime(col("ts_unix"))))

    # Lag features (temperature 1 step back per city)
    window = Window.partitionBy("city").orderBy("ts_unix")
    df = df.withColumn("temperature_lag_1", lag(col("temperature"), 1).over(window))
    df = df.withColumn("humidity_lag_1", lag(col("humidity"), 1).over(window))

    # Rolling mean (3-hour window)
    rolling = Window.partitionBy("city").orderBy("ts_unix").rangeBetween(-2, 0)
    df = df.withColumn("temperature_rolling_mean_3", avg(col("temperature")).over(rolling))
    df = df.withColumn("temperature_rolling_std_3", stddev(col("temperature")).over(rolling))

    # Interaction features
    df = df.withColumn("temp_humidity_interaction", col("temperature") * col("humidity") / 100.0)
    df = df.withColumn("cloud_visibility_ratio", col("cloudiness") / (col("visibility") + 0.1))

    # Drop rows with nulls from lag features
    return df.dropna()


def train_model(df: pyspark.sql.DataFrame) -> dict[str, object]:  # type: ignore[name-defined]
    """Train a RandomForest temperature regression model."""
    from pyspark.ml.evaluation import RegressionEvaluator

    feature_cols = [
        "humidity",
        "pressure",
        "wind_speed",
        "cloudiness",
        "visibility",
        "hour",
        "day_of_week",
        "month",
        "temperature_lag_1",
        "humidity_lag_1",
        "temperature_rolling_mean_3",
        "temp_humidity_interaction",
        "cloud_visibility_ratio",
    ]

    assembler = VectorAssembler(inputCols=feature_cols, outputCol="features", handleInvalid="skip")
    regressor = RandomForestRegressor(
        featuresCol="features", labelCol="temperature", numTrees=20, maxDepth=5, seed=42
    )
    pipeline = Pipeline(stages=[assembler, regressor])

    train_df, test_df = df.randomSplit([0.8, 0.2], seed=42)
    logger.info("Training on %d rows, testing on %d rows", train_df.count(), test_df.count())

    model = pipeline.fit(train_df)
    predictions = model.transform(test_df)

    evaluator = RegressionEvaluator(labelCol="temperature", predictionCol="prediction")
    rmse = evaluator.evaluate(predictions, {evaluator.metricName: "rmse"})
    r2 = evaluator.evaluate(predictions, {evaluator.metricName: "r2"})

    logger.info("Model metrics: RMSE=%.3f R²=%.3f", rmse, r2)
    return {"model": model, "rmse": rmse, "r2": r2}


def register_model(metrics: dict[str, object]) -> None:
    """Register the trained model in the DEX ModelRegistry."""
    from dataenginex.ml.registry import ModelRegistry

    registry = ModelRegistry()
    entry = registry.register(
        name="weather_temperature_rf",
        version="1.0.0",
        metadata={
            "algorithm": "RandomForest",
            "rmse": metrics["rmse"],
            "r2": metrics["r2"],
            "features": "time+lag+rolling+interactions",
        },
    )
    logger.info("Registered model: %s", entry)


def main() -> None:
    if not _HAS_PYSPARK:
        logger.warning("PySpark not installed — skipping Spark example")
        logger.info("Install with: uv sync --group data")
        return

    spark = create_spark()
    try:
        logger.info("Building sample weather dataset")
        df = build_sample_data(spark)

        logger.info("Engineering features")
        df = engineer_features(df)
        logger.info("Feature columns: %s", df.columns)

        logger.info("Training temperature prediction model")
        result = train_model(df)

        logger.info("Registering model in ModelRegistry")
        register_model(result)

        logger.info("Done — RMSE=%.3f R²=%.3f", result["rmse"], result["r2"])
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
