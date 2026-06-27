#!/usr/bin/env python
"""01_hello_pipeline.py — Minimal DataEngineX pipeline walkthrough.

Demonstrates:
- Data profiling with ``DataProfiler``
- Medallion architecture layer configuration
- Storage backend basics

Uses generic e-commerce order data — no domain-specific schemas required.
"""

from __future__ import annotations

from dataenginex.core import (
    DataLayer,
    MedallionArchitecture,
)
from dataenginex.data import DataProfiler


def main() -> None:
    # ----- 1. Prepare sample e-commerce records ---------------------------
    records = [
        {
            "order_id": f"ORD-{1000 + i}",
            "customer_name": name,
            "product": product,
            "category": category,
            "quantity": qty,
            "unit_price": price,
            "total": round(qty * price, 2),
            "region": region,
        }
        for i, (name, product, category, qty, price, region) in enumerate(
            [
                ("Alice Johnson", "Wireless Mouse", "Electronics", 2, 29.99, "US-West"),
                ("Bob Smith", "USB-C Hub", "Electronics", 1, 49.99, "US-East"),
                ("Carol Lee", "Standing Desk", "Furniture", 1, 399.00, "EU-West"),
                ("David Chen", "Mechanical Keyboard", "Electronics", 1, 89.99, "APAC"),
                ("Eve Martinez", "Monitor Arm", "Furniture", 3, 34.99, "US-West"),
                ("Frank Nguyen", "Webcam HD", "Electronics", 2, 59.99, "US-East"),
                ("Grace Kim", "Desk Lamp", "Lighting", 1, 24.99, "APAC"),
                ("Hank Brown", "Ergonomic Chair", "Furniture", 1, 549.00, "EU-West"),
            ]
        )
    ]
    print(f"Created {len(records)} sample order records\n")

    # ----- 2. Profile the dataset -----------------------------------------
    profiler = DataProfiler()
    report = profiler.profile(records, dataset_name="ecommerce_orders")
    print(f"Profile: {report.record_count} records, {report.column_count} columns")
    print(f"  Completeness: {report.completeness:.2%}")
    print(f"  Duration: {report.duration_ms:.1f} ms")

    for col in report.columns:
        extra = ""
        if col.dtype == "numeric" and col.min_value is not None:
            extra = f", min={col.min_value}, max={col.max_value}"
        elif col.dtype == "string" and col.unique_count:
            extra = f", unique={col.unique_count}"
        print(f"  Column '{col.name}': type={col.dtype}, nulls={col.null_count}{extra}")

    # ----- 3. Inspect medallion layer configs -----------------------------
    print("\nMedallion layers:")
    for layer_cfg in MedallionArchitecture.get_all_layers():
        print(
            f"  {layer_cfg.layer_name}: "
            f"threshold={layer_cfg.quality_threshold}, "
            f"retention={layer_cfg.retention_days} days"
        )

    # ----- 4. Check a specific layer config --------------------------------
    silver = MedallionArchitecture.get_layer_config(DataLayer.SILVER)
    if silver:
        print("\nSilver layer details:")
        print(f"  Purpose: {silver.purpose}")
        print(f"  Format: {silver.storage_format}")

    print("\nDone! ✓")


if __name__ == "__main__":
    main()
