#!/usr/bin/env python
"""07_api_ingestion.py — HTTP API ingestion with medallion architecture.

Demonstrates:
- Fetching data from an external HTTP API (OpenWeatherMap-style)
- Transforming raw responses into standardized records (Bronze → Silver)
- Validating data quality before promotion (Silver → Gold)
- Using DEX DataConnector and QualityGate

Run:
    uv run python examples/07_api_ingestion.py
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

from loguru import logger

from dataenginex.core.medallion_architecture import Layer, MedallionConfig
from dataenginex.core.quality import QualityCheck, QualityGate, Severity
from dataenginex.data.connectors import DataConnector, DataSource, SourceType

# ---------------------------------------------------------------------------
# Bronze: raw ingestion
# ---------------------------------------------------------------------------


def extract_weather_records(api_key: str, cities: list[str]) -> list[dict[str, Any]]:
    """Fetch weather data from OpenWeatherMap API (Bronze layer)."""
    import httpx

    base_url = "https://api.openweathermap.org/data/2.5/weather"
    records: list[dict[str, Any]] = []

    for city in cities:
        try:
            response = httpx.get(
                base_url,
                params={"q": city, "units": "metric", "appid": api_key},
                timeout=10,
            )
            response.raise_for_status()
            raw = response.json()
            records.append(
                {"_raw": raw, "_city": city, "_ingested_at": datetime.now(tz=UTC).isoformat()}
            )
            logger.info("Extracted weather for city=%s", city)
        except httpx.HTTPError as exc:
            logger.error("Failed to fetch city=%s error=%s", city, exc)

    return records


# ---------------------------------------------------------------------------
# Silver: standardized transform
# ---------------------------------------------------------------------------


def transform_to_silver(raw_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Transform raw API payloads into standardized weather records (Silver)."""
    silver: list[dict[str, Any]] = []

    for record in raw_records:
        raw = record["_raw"]
        weather = raw["weather"][0]
        silver.append(
            {
                "city": raw["name"],
                "country": raw["sys"]["country"],
                "temperature": raw["main"]["temp"],
                "feels_like": raw["main"]["feels_like"],
                "humidity": raw["main"]["humidity"],
                "pressure": raw["main"]["pressure"],
                "condition": weather["main"],
                "wind_speed": raw["wind"]["speed"],
                "cloudiness": raw["clouds"]["all"],
                "ingested_at": record["_ingested_at"],
            }
        )

    logger.info("Transformed %d records to Silver", len(silver))
    return silver


# ---------------------------------------------------------------------------
# Gold: quality-gated promotion
# ---------------------------------------------------------------------------


def promote_to_gold(silver_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Apply quality checks and promote clean records to Gold layer."""
    gate = QualityGate(
        name="weather_gold",
        checks=[
            QualityCheck(
                name="temperature_range",
                description="Temperature must be physically plausible (-90°C to 60°C)",
                severity=Severity.ERROR,
            ),
            QualityCheck(
                name="humidity_range",
                description="Humidity must be 0–100%",
                severity=Severity.WARNING,
            ),
        ],
    )

    gold: list[dict[str, Any]] = []
    for record in silver_records:
        passed = -90 <= record.get("temperature", 0) <= 60 and 0 <= record.get("humidity", 0) <= 100
        if passed:
            gold.append({**record, "_promoted_at": datetime.now(tz=UTC).isoformat()})
        else:
            logger.warning("Record failed quality gate city=%s", record.get("city"))

    result = gate.run({"records": gold, "total": len(silver_records)})
    logger.info(
        "Gold promotion: passed=%d failed=%d gate_status=%s",
        len(gold),
        len(silver_records) - len(gold),
        result.status if hasattr(result, "status") else "ok",
    )
    return gold


# ---------------------------------------------------------------------------
# Demo: no live API key required
# ---------------------------------------------------------------------------


def demo_with_mock_data() -> None:
    """Demonstrate the pipeline with pre-built mock records (no API key needed)."""
    logger.info("Running API ingestion demo with mock data")

    # --- Bronze (mock) ---
    mock_bronze = [
        {
            "_raw": {
                "name": "Seattle",
                "sys": {"country": "US"},
                "main": {"temp": 12.3, "feels_like": 10.1, "humidity": 82, "pressure": 1013},
                "weather": [{"main": "Drizzle"}],
                "wind": {"speed": 5.2},
                "clouds": {"all": 90},
            },
            "_city": "Seattle",
            "_ingested_at": datetime.now(tz=UTC).isoformat(),
        },
        {
            "_raw": {
                "name": "Austin",
                "sys": {"country": "US"},
                "main": {"temp": 28.7, "feels_like": 30.2, "humidity": 55, "pressure": 1008},
                "weather": [{"main": "Clear"}],
                "wind": {"speed": 3.1},
                "clouds": {"all": 5},
            },
            "_city": "Austin",
            "_ingested_at": datetime.now(tz=UTC).isoformat(),
        },
    ]

    # --- Silver ---
    silver = transform_to_silver(mock_bronze)
    logger.info("Silver records: %s", [r["city"] for r in silver])

    # --- Medallion config ---
    config = MedallionConfig(
        bronze=Layer(name="bronze", path="/tmp/dex/weather/bronze"),
        silver=Layer(name="silver", path="/tmp/dex/weather/silver"),
        gold=Layer(name="gold", path="/tmp/dex/weather/gold"),
    )
    logger.info("Medallion config: %s", config)

    # --- DataConnector ---
    source = DataSource(
        name="openweathermap",
        source_type=SourceType.API,
        connection_string="https://api.openweathermap.org/data/2.5",
    )
    connector = DataConnector(source=source)
    logger.info("Connector: %s", connector)

    # --- Gold ---
    gold = promote_to_gold(silver)
    for record in gold:
        logger.info(
            "Gold record: city=%s temp=%.1f°C condition=%s",
            record["city"],
            record["temperature"],
            record["condition"],
        )

    logger.info("Pipeline complete — %d records in Gold layer", len(gold))


if __name__ == "__main__":
    api_key = os.environ.get("OPENWEATHERMAP_API_KEY", "")
    if api_key:
        cities = ["Seattle", "Austin", "New York"]
        logger.info("Live mode: fetching %d cities", len(cities))
        bronze = extract_weather_records(api_key, cities)
        silver = transform_to_silver(bronze)
        gold = promote_to_gold(silver)
        logger.info("Done — %d Gold records", len(gold))
    else:
        logger.info("No OPENWEATHERMAP_API_KEY set — running mock demo")
        demo_with_mock_data()
