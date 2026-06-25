# dataenginex.plugins

Plugin system for extending DEX with custom connectors, transforms, trainers, and serving engines.

## Quick import

```python
from dataenginex.plugins import PluginRegistry, plugin_registry
```

______________________________________________________________________

## Plugin Registry

`dataenginex.plugins.registry`

Central plugin registry. Plugins self-register via `@plugin_registry.decorator(name)` or explicit `register()` calls.

::: dataenginex.plugins.registry

**Key class:** `PluginRegistry`

```python
from dataenginex.plugins.registry import plugin_registry
from dataenginex.core.interfaces import BaseConnector

@plugin_registry.decorator("my_connector")
class MyConnector(BaseConnector):
    def fetch(self) -> list[dict]:
        ...

# Look up
cls = plugin_registry.get("my_connector")

# List all
for name, cls in plugin_registry.all():
    print(name, cls)
```

______________________________________________________________________

## Writing a Plugin

Plugins implement one of the base interfaces from `dataenginex.core.interfaces`:

| Interface | Use for |
|-----------|---------|
| `BaseConnector` | Data sources / sinks |
| `BaseTransform` | DataFrame transformations |
| `BaseTrainer` | ML training backends |
| `BaseServingEngine` | Model serving backends |

Register with `@plugin_registry.decorator("name")` or `plugin_registry.register("name", MyClass)`. Registered names are available in `dex.yaml` config under the relevant `type:` field.
