# dataenginex.core

Foundation layer — interfaces, medallion architecture, quality gates, registries, exceptions, and shared schemas.

## Quick import

```python
from dataenginex.core import (
    MedallionConfig, Layer,
    QualityGate, QualityCheck, QualityResult, Severity,
    BaseConnector, BaseTransform, BaseRunner,
    NotFoundError, ValidationError, PipelineError,
    ComponentRegistry,
)
```

______________________________________________________________________

## Medallion Architecture

`dataenginex.core.medallion_architecture`

Defines the Bronze → Silver → Gold layer model and per-layer configuration.

::: dataenginex.core.medallion_architecture

**Key classes:** `MedallionConfig`, `Layer`, `LayerConfig`, `MedallionPipeline`

```python
from dataenginex.core.medallion_architecture import Layer, MedallionConfig, LayerConfig

cfg = MedallionConfig(
    bronze=LayerConfig(path="data/bronze"),
    silver=LayerConfig(path="data/silver", quality_threshold=0.95),
    gold=LayerConfig(path="data/gold", quality_threshold=0.99),
)
```

______________________________________________________________________

## Quality Gates

`dataenginex.core.quality`

Declarative data quality checks that run at layer promotion boundaries.

::: dataenginex.core.quality

**Key classes:** `QualityCheck`, `QualityGate`, `QualityResult`, `Severity`

```python
from dataenginex.core.quality import QualityCheck, QualityGate, Severity

gate = QualityGate(
    checks=[
        QualityCheck(name="no_nulls", column="user_id", check_type="not_null"),
        QualityCheck(
            name="email_format",
            column="email",
            check_type="regex",
            pattern=r"^[^@]+@[^@]+\.[^@]+$",
            severity=Severity.ERROR,
        ),
    ]
)
result = gate.run(df)
assert result.passed
```

______________________________________________________________________

## Interfaces

`dataenginex.core.interfaces`

Abstract base classes for connectors, transforms, runners, and storage backends. Implement these to extend DEX with custom components.

::: dataenginex.core.interfaces

**Key classes:** `BaseConnector`, `BaseTransform`, `BaseRunner`, `BaseStorage`, `BaseProfiler`

______________________________________________________________________

## Registry

`dataenginex.core.registry`

Generic component registry used by connectors, transforms, models, and agents.

::: dataenginex.core.registry

**Key class:** `ComponentRegistry`

```python
from dataenginex.core.registry import ComponentRegistry

registry: ComponentRegistry[MyPlugin] = ComponentRegistry()
registry.register("my_plugin", MyPlugin)
plugin = registry.get("my_plugin")
```

______________________________________________________________________

## Schemas

`dataenginex.core.schemas`

Shared Pydantic response models used across the engine, CLI, and API layers.

::: dataenginex.core.schemas

**Key models:** `HealthResponse`, `RootResponse`, `EchoRequest`, `EchoResponse`, `ErrorResponse`, `ComponentStatus`

______________________________________________________________________

## Validators

`dataenginex.core.validators`

Reusable Pydantic validators and field helpers for config schema enforcement.

::: dataenginex.core.validators

______________________________________________________________________

## Exceptions

`dataenginex.core.exceptions`

Typed exception hierarchy for pipeline, validation, and resource errors.

::: dataenginex.core.exceptions

**Key exceptions:** `DexError`, `NotFoundError`, `ValidationError`, `PipelineError`, `RegistryError`, `ConfigError`

```python
from dataenginex.core.exceptions import NotFoundError, PipelineError

try:
    engine.run_pipeline("missing")
except NotFoundError as e:
    print(e.detail)
```
