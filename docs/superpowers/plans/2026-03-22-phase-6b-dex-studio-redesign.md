# Phase 6B: DEX Studio Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign DEX Studio from scratch as a unified Data + ML + AI + System platform with 4-domain navigation, project management, and 20+ pages connected to the DEX engine API.

**Architecture:** Replace flat sidebar + 6 pages with a two-level domain shell (top bar tabs + section sidebar). Add project hub for multi-project management. Expand DexClient with all Phase 6A endpoints. Build 12 reusable components and 20+ domain-specific pages.

**Tech Stack:** Python 3.13 · NiceGUI · pywebview · httpx · Pydantic · pytest · mypy --strict

**Spec:** `docs/superpowers/specs/2026-03-22-phase-6-integration-design.md` (Part 2)

**Depends on:** Phase 6A (DEX Engine Integration) — all API endpoints must exist before Studio can connect.

**Repo:** `/home/jay/workspace/DataEngineX/dex-studio`

---

## File Structure

### Delete (replaced by new components/pages)

| File | Replaced By |
|------|------------|
| `src/dex_studio/components/sidebar.py` | `components/app_shell.py` + `components/domain_sidebar.py` |
| `src/dex_studio/components/page_layout.py` | `components/app_shell.py` |
| `src/dex_studio/pages/overview.py` | `pages/data/dashboard.py` |
| `src/dex_studio/pages/health.py` | `pages/system/status.py` |
| `src/dex_studio/pages/data_quality.py` | `pages/data/quality.py` |
| `src/dex_studio/pages/lineage.py` | `pages/data/lineage.py` |
| `src/dex_studio/pages/ml_models.py` | `pages/ml/models.py` |
| `src/dex_studio/pages/settings.py` | `pages/system/settings.py` |

### Create/Rewrite

| Action | File | Responsibility |
|--------|------|---------------|
| Rewrite | `src/dex_studio/config.py` | Multi-project config (`~/.dex-studio/projects.yaml`) |
| Rewrite | `src/dex_studio/theme.py` | Refined CSS custom properties matching spec |
| Rewrite | `src/dex_studio/client.py` | DexClient with all Phase 6A endpoints |
| Rewrite | `src/dex_studio/app.py` | New bootstrap with domain routing |
| Rewrite | `src/dex_studio/cli.py` | Updated CLI options |
| Create | `src/dex_studio/components/app_shell.py` | Top bar + domain tabs + project switcher + command palette |
| Create | `src/dex_studio/components/domain_sidebar.py` | Per-domain section sidebar |
| Create | `src/dex_studio/components/breadcrumb.py` | Context breadcrumb bar |
| Create | `src/dex_studio/components/data_table.py` | Sortable, filterable table |
| Create | `src/dex_studio/components/chat_message.py` | Chat bubble + tool call rendering |
| Create | `src/dex_studio/components/tool_call_block.py` | Expandable tool call display |
| Create | `src/dex_studio/components/inspector_panel.py` | Collapsible right panel |
| Deferred | `src/dex_studio/components/command_palette.py` | Ctrl+K search/jump overlay (future — needs JS interop) |
| Create | `src/dex_studio/components/project_card.py` | Project card for hub/switcher |
| Create | `src/dex_studio/components/empty_state.py` | No-data placeholder |
| Rewrite | `src/dex_studio/components/metric_card.py` | Updated metric display |
| Rewrite | `src/dex_studio/components/status_card.py` | Renamed: `status_badge.py` |
| Create | `src/dex_studio/pages/project_hub.py` | Launch screen with project list |
| Create | `src/dex_studio/pages/data/dashboard.py` | Data overview |
| Create | `src/dex_studio/pages/data/pipelines.py` | Pipeline operations |
| Create | `src/dex_studio/pages/data/sources.py` | Source browser |
| Create | `src/dex_studio/pages/data/warehouse.py` | Medallion layer browser |
| Create | `src/dex_studio/pages/data/quality.py` | Quality gates |
| Create | `src/dex_studio/pages/data/lineage.py` | Lineage graph |
| Create | `src/dex_studio/pages/ml/dashboard.py` | ML overview |
| Create | `src/dex_studio/pages/ml/experiments.py` | Experiment tracking |
| Create | `src/dex_studio/pages/ml/models.py` | Model registry |
| Create | `src/dex_studio/pages/ml/predictions.py` | Prediction playground |
| Create | `src/dex_studio/pages/ml/features.py` | Feature store browser |
| Create | `src/dex_studio/pages/ml/drift.py` | Drift monitor |
| Create | `src/dex_studio/pages/ai/dashboard.py` | AI overview |
| Create | `src/dex_studio/pages/ai/agents.py` | Agent chat interface |
| Create | `src/dex_studio/pages/ai/tools.py` | Tool registry browser |
| Create | `src/dex_studio/pages/ai/collections.py` | Vector collection manager |
| Create | `src/dex_studio/pages/ai/retrieval.py` | Search playground |
| Create | `src/dex_studio/pages/system/status.py` | Overall health |
| Create | `src/dex_studio/pages/system/components.py` | Component health |
| Create | `src/dex_studio/pages/system/metrics.py` | Prometheus viewer |
| Create | `src/dex_studio/pages/system/logs.py` | Log viewer |
| Create | `src/dex_studio/pages/system/traces.py` | Trace viewer |
| Create | `src/dex_studio/pages/system/settings.py` | Connection config |
| Create | `src/dex_studio/pages/system/connection.py` | Multi-project connections |

### Tests

| Action | File | Responsibility |
|--------|------|---------------|
| Rewrite | `tests/unit/test_client.py` | All new DexClient methods |
| Rewrite | `tests/unit/test_config.py` | Multi-project config |
| Create | `tests/unit/test_components.py` | Component render tests |
| Create | `tests/integration/test_app.py` | Full app startup with mock engine |

---

## Task 1: Theme Refinement

**Files:**
- Rewrite: `src/dex_studio/theme.py`
- Test: `tests/unit/test_theme.py`

- [ ] **Step 1: Write test for theme constants**

```python
# tests/unit/test_theme.py
from __future__ import annotations

from dex_studio.theme import COLORS, apply_global_styles


class TestTheme:
    def test_colors_has_required_keys(self) -> None:
        required = [
            "bg_primary", "bg_secondary", "bg_sidebar", "bg_hover",
            "accent", "accent_light", "text_primary", "text_muted",
            "text_dim", "text_faint", "border", "success", "warning", "error",
        ]
        for key in required:
            assert key in COLORS, f"Missing color: {key}"

    def test_colors_are_hex(self) -> None:
        for key, val in COLORS.items():
            assert val.startswith("#"), f"{key} is not hex: {val}"
            assert len(val) == 7, f"{key} is not 6-digit hex: {val}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_theme.py -v`
Expected: FAIL — missing keys (`bg_sidebar`, `text_dim`, `text_faint`)

- [ ] **Step 3: Rewrite theme.py**

```python
# src/dex_studio/theme.py
"""DEX Studio theme — dark-first palette with CSS custom properties."""

from __future__ import annotations

__all__ = ["COLORS", "apply_global_styles"]

COLORS: dict[str, str] = {
    # Backgrounds
    "bg_primary": "#0f1117",
    "bg_secondary": "#1a1d27",
    "bg_sidebar": "#13151f",
    "bg_hover": "#1e2235",
    "bg_card": "#1e2130",
    # Accent
    "accent": "#6366f1",
    "accent_light": "#a5b4fc",
    "accent_muted": "#4f46e5",
    # Text
    "text_primary": "#f1f5f9",
    "text_muted": "#94a3b8",
    "text_dim": "#64748b",
    "text_faint": "#475569",
    # Borders
    "border": "#2d3348",
    "divider": "#1e2235",
    # Status
    "success": "#22c55e",
    "warning": "#f59e0b",
    "error": "#ef4444",
}


def apply_global_styles() -> None:
    """Inject global CSS with theme custom properties."""
    from nicegui import ui

    css_vars = "\n".join(f"  --{k.replace('_', '-')}: {v};" for k, v in COLORS.items())
    ui.add_css(f"""
        :root {{
            {css_vars}
        }}
        body {{
            background: var(--bg-primary);
            color: var(--text-primary);
            font-family: system-ui, -apple-system, sans-serif;
        }}
        .nicegui-content {{
            padding: 0;
        }}
        .dex-card {{
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 8px;
        }}
        .dex-card:hover {{
            border-color: var(--accent);
        }}
        .section-title {{
            font-size: 10px;
            text-transform: uppercase;
            color: var(--text-faint);
            letter-spacing: 0.05em;
        }}
    """)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_theme.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/dex_studio/theme.py tests/unit/test_theme.py
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "feat: refine theme with spec-aligned color tokens and CSS custom properties"
```

---

## Task 2: Multi-Project Config

**Files:**
- Rewrite: `src/dex_studio/config.py`
- Rewrite: `tests/unit/test_config.py`

- [ ] **Step 1: Write tests for multi-project config**

```python
# tests/unit/test_config.py
from __future__ import annotations

from pathlib import Path

import pytest

from dex_studio.config import ProjectEntry, StudioConfig, load_config


class TestStudioConfig:
    def test_defaults(self) -> None:
        config = StudioConfig()
        assert config.api_url == "http://localhost:17000"
        assert config.theme == "dark"
        assert config.port == 8080

    def test_custom_values(self) -> None:
        config = StudioConfig(api_url="http://prod:17000", theme="light")
        assert config.api_url == "http://prod:17000"

    def test_immutable(self) -> None:
        config = StudioConfig()
        with pytest.raises(AttributeError):
            config.api_url = "http://other"  # type: ignore[misc]


class TestProjectEntry:
    def test_project_entry(self) -> None:
        entry = ProjectEntry(
            name="movie-analytics",
            url="http://localhost:17000",
            icon="movie",
        )
        assert entry.name == "movie-analytics"
        assert entry.token is None


class TestLoadConfig:
    def test_loads_from_file(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text("api_url: http://custom:17000\ntheme: light\n")
        config = load_config(path=cfg_file)
        assert config.api_url == "http://custom:17000"
        assert config.theme == "light"

    def test_env_overrides(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DEX_STUDIO_API_URL", "http://env:9999")
        config = load_config()
        assert config.api_url == "http://env:9999"

    def test_missing_file_returns_defaults(self) -> None:
        config = load_config(path=Path("/nonexistent/config.yaml"))
        assert config.api_url == "http://localhost:17000"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_config.py -v`
Expected: FAIL — `ImportError: cannot import name 'ProjectEntry'`

- [ ] **Step 3: Rewrite config.py**

```python
# src/dex_studio/config.py
"""Configuration for DEX Studio — supports multi-project setup."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

__all__ = ["ProjectEntry", "StudioConfig", "load_config", "load_projects"]

_USER_CONFIG = Path.home() / ".dex-studio" / "config.yaml"
_PROJECTS_FILE = Path.home() / ".dex-studio" / "projects.yaml"
_LOCAL_CONFIG = Path(".dex-studio.yaml")


@dataclass(frozen=True, slots=True)
class ProjectEntry:
    """A single project in the multi-project config."""

    name: str
    url: str = "http://localhost:17000"
    token: str | None = None
    icon: str = "folder"


@dataclass(frozen=True, slots=True)
class StudioConfig:
    """DEX Studio configuration."""

    api_url: str = "http://localhost:17000"
    api_token: str | None = None
    timeout: float = 10.0
    window_width: int = 1400
    window_height: int = 900
    theme: str = "dark"
    poll_interval: float = 5.0
    native_mode: bool = True
    host: str = "127.0.0.1"
    port: int = 8080


def load_config(
    path: Path | None = None,
    *,
    env_prefix: str = "DEX_STUDIO_",
) -> StudioConfig:
    """Load config from YAML file(s) + env vars.

    Priority (highest wins): env vars > explicit path > local > user-level > defaults.
    """
    merged: dict[str, Any] = {}

    # User-level config
    if _USER_CONFIG.exists():
        merged.update(_load_yaml(_USER_CONFIG))

    # Project-local config
    if _LOCAL_CONFIG.exists():
        merged.update(_load_yaml(_LOCAL_CONFIG))

    # Explicit path
    if path and path.exists():
        merged.update(_load_yaml(path))

    # Env var overrides
    field_names = {f.name for f in StudioConfig.__dataclass_fields__.values()}
    for key in field_names:
        env_key = f"{env_prefix}{key.upper()}"
        env_val = os.environ.get(env_key)
        if env_val is not None:
            merged[key] = env_val

    # Filter unknown keys
    valid = {k: v for k, v in merged.items() if k in field_names}
    return StudioConfig(**valid)


def load_projects() -> list[ProjectEntry]:
    """Load project list from ~/.dex-studio/projects.yaml."""
    if not _PROJECTS_FILE.exists():
        return []
    data = _load_yaml(_PROJECTS_FILE)
    projects = data.get("projects", {})
    return [
        ProjectEntry(name=name, **{k: v for k, v in cfg.items() if k in ("url", "token", "icon")})
        for name, cfg in projects.items()
    ]


def save_projects(projects: list[ProjectEntry]) -> None:
    """Save project list to ~/.dex-studio/projects.yaml."""
    _PROJECTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "projects": {
            p.name: {"url": p.url, "token": p.token, "icon": p.icon}
            for p in projects
        }
    }
    _PROJECTS_FILE.write_text(yaml.safe_dump(data, default_flow_style=False))


def _load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML file, returning empty dict on error."""
    try:
        with path.open() as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_config.py -v`
Expected: PASS

- [ ] **Step 5: Typecheck**

Run: `uv run poe typecheck`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/dex_studio/config.py tests/unit/test_config.py
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "feat: multi-project config with projects.yaml support"
```

---

## Task 3: DexClient Expansion

**Files:**
- Rewrite: `src/dex_studio/client.py`
- Rewrite: `tests/unit/test_client.py`

- [ ] **Step 1: Write tests for new DexClient methods**

```python
# tests/unit/test_client.py
from __future__ import annotations

import httpx
import pytest

from dex_studio.client import DexAPIError, DexClient
from dex_studio.config import StudioConfig


@pytest.fixture()
def config() -> StudioConfig:
    return StudioConfig(api_url="http://localhost:9999", timeout=2.0)


class TestDexClientLifecycle:
    async def test_connect_creates_client(self, config: StudioConfig) -> None:
        client = DexClient(config)
        await client.connect()
        assert client.is_connected
        await client.close()

    async def test_ping_returns_true(self, config: StudioConfig) -> None:
        client = DexClient(config)
        transport = httpx.MockTransport(
            lambda req: httpx.Response(200, json={"status": "alive"})
        )
        client._client = httpx.AsyncClient(transport=transport)
        assert await client.ping() is True
        await client.close()


class TestDataEndpoints:
    async def test_list_sources(self, config: StudioConfig) -> None:
        client = DexClient(config)
        transport = httpx.MockTransport(
            lambda req: httpx.Response(200, json={"sources": [], "count": 0})
        )
        client._client = httpx.AsyncClient(transport=transport, base_url=config.api_url)
        result = await client.list_sources()
        assert "sources" in result
        await client.close()

    async def test_run_pipeline(self, config: StudioConfig) -> None:
        client = DexClient(config)
        transport = httpx.MockTransport(
            lambda req: httpx.Response(200, json={"pipeline": "ingest", "success": True})
        )
        client._client = httpx.AsyncClient(transport=transport, base_url=config.api_url)
        result = await client.run_pipeline("ingest")
        assert result["success"] is True
        await client.close()


class TestMLEndpoints:
    async def test_list_experiments(self, config: StudioConfig) -> None:
        client = DexClient(config)
        transport = httpx.MockTransport(
            lambda req: httpx.Response(200, json={"experiments": [], "count": 0})
        )
        client._client = httpx.AsyncClient(transport=transport, base_url=config.api_url)
        result = await client.list_experiments()
        assert "experiments" in result
        await client.close()

    async def test_predict(self, config: StudioConfig) -> None:
        client = DexClient(config)
        transport = httpx.MockTransport(
            lambda req: httpx.Response(200, json={"model_name": "m", "prediction": 42})
        )
        client._client = httpx.AsyncClient(transport=transport, base_url=config.api_url)
        result = await client.predict("m", {"x": 1.0})
        assert result["prediction"] == 42
        await client.close()


class TestAIEndpoints:
    async def test_list_agents(self, config: StudioConfig) -> None:
        client = DexClient(config)
        transport = httpx.MockTransport(
            lambda req: httpx.Response(200, json={"agents": [], "count": 0})
        )
        client._client = httpx.AsyncClient(transport=transport, base_url=config.api_url)
        result = await client.list_agents()
        assert "agents" in result
        await client.close()

    async def test_agent_chat(self, config: StudioConfig) -> None:
        client = DexClient(config)
        transport = httpx.MockTransport(
            lambda req: httpx.Response(200, json={
                "agent": "bot", "response": "Hi", "iterations": 1, "tool_calls": 0,
            })
        )
        client._client = httpx.AsyncClient(transport=transport, base_url=config.api_url)
        result = await client.agent_chat("bot", "Hello")
        assert result["response"] == "Hi"
        await client.close()


class TestSystemEndpoints:
    async def test_components(self, config: StudioConfig) -> None:
        client = DexClient(config)
        transport = httpx.MockTransport(
            lambda req: httpx.Response(200, json={"components": []})
        )
        client._client = httpx.AsyncClient(transport=transport, base_url=config.api_url)
        result = await client.components()
        assert "components" in result
        await client.close()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_client.py -v`
Expected: FAIL — missing methods (`list_sources`, `run_pipeline`, `list_experiments`, etc.)

- [ ] **Step 3: Rewrite client.py**

```python
# src/dex_studio/client.py
"""HTTP client wrapper for DEX engine API."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import logging

import httpx

from dex_studio.config import StudioConfig

logger = logging.getLogger(__name__)

__all__ = ["DexAPIError", "DexClient"]


class DexAPIError(Exception):
    """Raised when the DEX engine returns an error response."""

    def __init__(self, status_code: int, message: str, url: str) -> None:
        self.status_code = status_code
        self.url = url
        super().__init__(f"HTTP {status_code} from {url}: {message}")


@dataclass(slots=True)
class DexClient:
    """Async HTTP client for the DEX engine API."""

    config: StudioConfig
    _client: httpx.AsyncClient | None = field(default=None, init=False, repr=False)

    async def connect(self) -> None:
        """Create the HTTP client."""
        headers: dict[str, str] = {}
        if self.config.api_token:
            headers["Authorization"] = f"Bearer {self.config.api_token}"
        self._client = httpx.AsyncClient(
            base_url=self.config.api_url,
            timeout=self.config.timeout,
            headers=headers,
        )

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    @property
    def is_connected(self) -> bool:
        return self._client is not None and not self._client.is_closed

    # --- Internal ---

    async def _get(self, path: str, **params: Any) -> dict[str, Any]:
        if self._client is None:
            raise RuntimeError("Client not connected -- call connect() first")
        resp = await self._client.get(path, params={k: v for k, v in params.items() if v is not None})
        if resp.status_code >= 400:
            raise DexAPIError(resp.status_code, resp.text, str(resp.url))
        return resp.json()

    async def _post(self, path: str, json: Any = None) -> dict[str, Any]:
        if self._client is None:
            raise RuntimeError("Client not connected -- call connect() first")
        resp = await self._client.post(path, json=json)
        if resp.status_code >= 400:
            raise DexAPIError(resp.status_code, resp.text, str(resp.url))
        return resp.json()

    # --- Health ---

    async def ping(self) -> bool:
        try:
            data = await self._get("/health")
            return data.get("status") == "alive"
        except Exception:
            return False

    async def health(self) -> dict[str, Any]:
        return await self._get("/api/v1/health")

    async def root(self) -> dict[str, Any]:
        return await self._get("/")

    # --- Data ---

    async def list_sources(self) -> dict[str, Any]:
        return await self._get("/api/v1/data/sources")

    async def get_source(self, name: str) -> dict[str, Any]:
        return await self._get(f"/api/v1/data/sources/{name}")

    async def list_pipelines(self) -> dict[str, Any]:
        return await self._get("/api/v1/pipelines/")

    async def get_pipeline(self, name: str) -> dict[str, Any]:
        return await self._get(f"/api/v1/pipelines/{name}")

    async def run_pipeline(self, name: str) -> dict[str, Any]:
        return await self._post(f"/api/v1/pipelines/{name}/run")

    async def warehouse_layers(self) -> dict[str, Any]:
        return await self._get("/api/v1/data/warehouse/layers")

    async def warehouse_tables(self, layer: str) -> dict[str, Any]:
        return await self._get(f"/api/v1/data/warehouse/layers/{layer}/tables")

    async def list_lineage(self) -> dict[str, Any]:
        return await self._get("/api/v1/data/lineage")

    async def get_lineage_event(self, event_id: str) -> dict[str, Any]:
        return await self._get(f"/api/v1/data/lineage/{event_id}")

    async def data_quality_summary(self) -> dict[str, Any]:
        return await self._get("/api/v1/data/quality/summary")

    async def data_quality_pipeline(self, pipeline: str) -> dict[str, Any]:
        return await self._get(f"/api/v1/data/quality/{pipeline}")

    # --- ML ---

    async def list_experiments(self) -> dict[str, Any]:
        return await self._get("/api/v1/ml/experiments")

    async def create_experiment(self, name: str) -> dict[str, Any]:
        return await self._post(f"/api/v1/ml/experiments/{name}")

    async def list_runs(self, experiment: str) -> dict[str, Any]:
        return await self._get(f"/api/v1/ml/experiments/{experiment}/runs")

    async def list_models(self) -> dict[str, Any]:
        return await self._get("/api/v1/ml/models")

    async def get_model(self, name: str) -> dict[str, Any]:
        return await self._get(f"/api/v1/ml/models/{name}")

    async def promote_model(self, name: str, stage: str) -> dict[str, Any]:
        return await self._post(f"/api/v1/ml/models/{name}/promote", json={"stage": stage})

    async def predict(self, model_name: str, features: dict[str, Any]) -> dict[str, Any]:
        return await self._post("/api/v1/ml/predictions", json={"model_name": model_name, "features": features})

    async def list_feature_groups(self) -> dict[str, Any]:
        return await self._get("/api/v1/ml/features")

    async def get_features(self, group: str, entity_ids: list[str] | None = None) -> dict[str, Any]:
        ids = ",".join(entity_ids) if entity_ids else ""
        return await self._get(f"/api/v1/ml/features/{group}", entity_ids=ids)

    async def save_features(self, group: str, data: list[dict[str, Any]], entity_key: str) -> dict[str, Any]:
        return await self._post(f"/api/v1/ml/features/{group}", json={"entity_key": entity_key, "data": data})

    async def check_drift(self, pipeline: str) -> dict[str, Any]:
        return await self._get(f"/api/v1/ml/drift/{pipeline}")

    # --- AI ---

    async def list_agents(self) -> dict[str, Any]:
        return await self._get("/api/v1/ai/agents")

    async def get_agent(self, name: str) -> dict[str, Any]:
        return await self._get(f"/api/v1/ai/agents/{name}")

    async def agent_chat(self, name: str, message: str) -> dict[str, Any]:
        return await self._post(f"/api/v1/ai/agents/{name}/chat", json={"message": message})

    async def list_tools(self) -> dict[str, Any]:
        return await self._get("/api/v1/ai/tools")

    async def get_tool(self, name: str) -> dict[str, Any]:
        return await self._get(f"/api/v1/ai/tools/{name}")

    # --- System ---

    async def components(self) -> dict[str, Any]:
        return await self._get("/api/v1/system/components")

    async def logs(self, level: str | None = None, limit: int = 100) -> dict[str, Any]:
        return await self._get("/api/v1/system/logs", level=level, limit=limit)

    async def traces(self, limit: int = 50) -> dict[str, Any]:
        return await self._get("/api/v1/system/traces", limit=limit)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_client.py -v`
Expected: All PASS

- [ ] **Step 5: Typecheck**

Run: `uv run poe typecheck`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/dex_studio/client.py tests/unit/test_client.py
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "feat: expand DexClient with all Phase 6A API endpoints"
```

---

## Task 4: Reusable Components — Core Set

**Files:**
- Create: `src/dex_studio/components/status_badge.py`
- Create: `src/dex_studio/components/empty_state.py`
- Create: `src/dex_studio/components/breadcrumb.py`
- Create: `src/dex_studio/components/data_table.py`
- Rewrite: `src/dex_studio/components/metric_card.py`
- Delete: `src/dex_studio/components/status_card.py`
- Test: `tests/unit/test_components.py`

- [ ] **Step 1: Write component tests**

```python
# tests/unit/test_components.py
"""Tests for reusable UI components — verify they render without errors."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


class TestStatusBadge:
    def test_import(self) -> None:
        from dex_studio.components.status_badge import status_badge
        assert callable(status_badge)


class TestEmptyState:
    def test_import(self) -> None:
        from dex_studio.components.empty_state import empty_state
        assert callable(empty_state)


class TestBreadcrumb:
    def test_import(self) -> None:
        from dex_studio.components.breadcrumb import breadcrumb
        assert callable(breadcrumb)


class TestDataTable:
    def test_import(self) -> None:
        from dex_studio.components.data_table import data_table
        assert callable(data_table)


class TestMetricCard:
    def test_import(self) -> None:
        from dex_studio.components.metric_card import metric_card
        assert callable(metric_card)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_components.py -v`
Expected: FAIL — missing modules

- [ ] **Step 3: Create status_badge.py**

```python
# src/dex_studio/components/status_badge.py
"""Status badge — colored pill for health/status display."""

from __future__ import annotations

from typing import Any

from nicegui import ui

from dex_studio.theme import COLORS

__all__ = ["status_badge"]

_STATUS_COLORS: dict[str, str] = {
    "healthy": COLORS["success"],
    "passing": COLORS["success"],
    "degraded": COLORS["warning"],
    "stale": COLORS["warning"],
    "unhealthy": COLORS["error"],
    "failed": COLORS["error"],
    "unavailable": COLORS["text_dim"],
    "unknown": COLORS["text_dim"],
    "none_configured": COLORS["text_dim"],
}


def status_badge(status: str) -> Any:
    """Render a colored status pill."""
    color = _STATUS_COLORS.get(status, COLORS["text_dim"])
    return ui.badge(status).props(f'color="{color}" outline')
```

- [ ] **Step 4: Create empty_state.py**

```python
# src/dex_studio/components/empty_state.py
"""Empty state — placeholder for pages with no data."""

from __future__ import annotations

from typing import Any

from nicegui import ui

from dex_studio.theme import COLORS

__all__ = ["empty_state"]


def empty_state(
    message: str = "No data yet",
    icon: str = "inbox",
    action_label: str | None = None,
    on_action: Any = None,
) -> None:
    """Render a centered empty-state placeholder."""
    with ui.column().classes("items-center justify-center w-full py-16"):
        ui.icon(icon).classes("text-6xl").style(f"color: {COLORS['text_dim']}")
        ui.label(message).style(f"color: {COLORS['text_muted']}; font-size: 14px; margin-top: 8px")
        if action_label and on_action:
            ui.button(action_label, on_click=on_action).classes("mt-4")
```

- [ ] **Step 5: Create breadcrumb.py**

```python
# src/dex_studio/components/breadcrumb.py
"""Breadcrumb — context navigation bar."""

from __future__ import annotations

from nicegui import ui

from dex_studio.theme import COLORS

__all__ = ["breadcrumb"]


def breadcrumb(*parts: str) -> None:
    """Render breadcrumb from path parts. Last part is active (white), rest are dim."""
    with ui.row().classes("items-center gap-1").style(
        f"padding: 10px 24px; border-bottom: 1px solid {COLORS['divider']}; font-size: 12px;"
    ):
        for i, part in enumerate(parts):
            if i > 0:
                ui.label("›").style(f"color: {COLORS['text_dim']}; margin: 0 6px")
            is_last = i == len(parts) - 1
            color = COLORS["text_primary"] if is_last else COLORS["text_dim"]
            ui.label(part).style(f"color: {color}")
```

- [ ] **Step 6: Create data_table.py**

```python
# src/dex_studio/components/data_table.py
"""Data table — sortable, filterable table with row actions."""

from __future__ import annotations

from typing import Any

from nicegui import ui

from dex_studio.theme import COLORS

__all__ = ["data_table"]


def data_table(
    columns: list[dict[str, Any]],
    rows: list[dict[str, Any]],
    *,
    title: str | None = None,
    row_key: str = "name",
) -> ui.table:
    """Render a styled data table.

    Args:
        columns: List of column defs, each with 'name', 'label', 'field'.
        rows: List of row dicts.
        title: Optional table title.
        row_key: Row identifier field.
    """
    table = ui.table(
        columns=columns,
        rows=rows,
        row_key=row_key,
        title=title,
    ).classes("w-full")
    table.style(
        f"background: {COLORS['bg_secondary']}; "
        f"color: {COLORS['text_primary']}; "
        f"border: 1px solid {COLORS['border']}; "
        f"border-radius: 8px;"
    )
    return table
```

- [ ] **Step 7: Rewrite metric_card.py**

```python
# src/dex_studio/components/metric_card.py
"""Metric card — large KPI display with label and optional trend."""

from __future__ import annotations

from typing import Any

from nicegui import ui

from dex_studio.theme import COLORS

__all__ = ["metric_card"]


def metric_card(
    label: str,
    value: str | int | float,
    *,
    unit: str = "",
    color: str | None = None,
) -> ui.card:
    """Render a metric card with large value and label."""
    value_color = color or COLORS["text_primary"]
    card = ui.card().classes("dex-card").style("padding: 16px; min-width: 140px;")
    with card:
        ui.label(label.upper()).classes("section-title")
        display = f"{value}{unit}" if unit else str(value)
        ui.label(display).style(
            f"font-size: 28px; font-weight: 700; color: {value_color}; margin-top: 4px;"
        )
    return card
```

- [ ] **Step 8: Delete old status_card.py and update __init__.py**

Delete `src/dex_studio/components/status_card.py`.

Update `src/dex_studio/components/__init__.py`:

```python
from __future__ import annotations

from dex_studio.components.breadcrumb import breadcrumb
from dex_studio.components.data_table import data_table
from dex_studio.components.empty_state import empty_state
from dex_studio.components.metric_card import metric_card
from dex_studio.components.status_badge import status_badge

__all__ = [
    "breadcrumb",
    "data_table",
    "empty_state",
    "metric_card",
    "status_badge",
]
```

- [ ] **Step 9: Run tests**

Run: `uv run pytest tests/unit/test_components.py -v`
Expected: All PASS

- [ ] **Step 10: Commit**

```bash
git add src/dex_studio/components/ tests/unit/test_components.py
git rm src/dex_studio/components/status_card.py src/dex_studio/components/page_layout.py src/dex_studio/components/sidebar.py
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "feat: core component library — status badge, empty state, breadcrumb, data table, metric card"
```

---

## Task 5: App Shell — Domain Tabs + Sidebar

**Files:**
- Create: `src/dex_studio/components/app_shell.py`
- Create: `src/dex_studio/components/domain_sidebar.py`
- Create: `src/dex_studio/components/project_card.py`

- [ ] **Step 1: Create domain sidebar definitions**

```python
# src/dex_studio/components/domain_sidebar.py
"""Per-domain section sidebar — changes based on active domain tab."""

from __future__ import annotations

from typing import Any

from nicegui import ui

from dex_studio.theme import COLORS

__all__ = ["domain_sidebar"]

# Sidebar definitions per domain
DOMAIN_SECTIONS: dict[str, list[dict[str, Any]]] = {
    "data": [
        {"section": "Overview", "items": [
            {"label": "Dashboard", "route": "/data", "icon": "dashboard"},
        ]},
        {"section": "Operations", "items": [
            {"label": "Pipelines", "route": "/data/pipelines", "icon": "account_tree"},
            {"label": "Sources", "route": "/data/sources", "icon": "storage"},
            {"label": "Warehouse", "route": "/data/warehouse", "icon": "warehouse"},
        ]},
        {"section": "Observability", "items": [
            {"label": "Quality Gates", "route": "/data/quality", "icon": "verified"},
            {"label": "Lineage", "route": "/data/lineage", "icon": "timeline"},
        ]},
    ],
    "ml": [
        {"section": "Overview", "items": [
            {"label": "Dashboard", "route": "/ml", "icon": "dashboard"},
        ]},
        {"section": "Lifecycle", "items": [
            {"label": "Experiments", "route": "/ml/experiments", "icon": "science"},
            {"label": "Models", "route": "/ml/models", "icon": "model_training"},
            {"label": "Predictions", "route": "/ml/predictions", "icon": "psychology"},
        ]},
        {"section": "Features", "items": [
            {"label": "Feature Store", "route": "/ml/features", "icon": "dataset"},
            {"label": "Drift Monitor", "route": "/ml/drift", "icon": "trending_up"},
        ]},
    ],
    "ai": [
        {"section": "Overview", "items": [
            {"label": "Dashboard", "route": "/ai", "icon": "dashboard"},
        ]},
        {"section": "Agents", "items": [
            {"label": "Agent Chat", "route": "/ai/agents", "icon": "smart_toy"},
            {"label": "Tools", "route": "/ai/tools", "icon": "build"},
        ]},
        {"section": "Knowledge", "items": [
            {"label": "Collections", "route": "/ai/collections", "icon": "collections_bookmark"},
            {"label": "Retrieval", "route": "/ai/retrieval", "icon": "search"},
        ]},
    ],
    "system": [
        {"section": "Health", "items": [
            {"label": "Status", "route": "/system", "icon": "monitor_heart"},
            {"label": "Components", "route": "/system/components", "icon": "developer_board"},
        ]},
        {"section": "Observability", "items": [
            {"label": "Metrics", "route": "/system/metrics", "icon": "bar_chart"},
            {"label": "Logs", "route": "/system/logs", "icon": "article"},
            {"label": "Traces", "route": "/system/traces", "icon": "timeline"},
        ]},
        {"section": "Config", "items": [
            {"label": "Settings", "route": "/system/settings", "icon": "settings"},
            {"label": "Connection", "route": "/system/connection", "icon": "lan"},
        ]},
    ],
}


def domain_sidebar(domain: str, active_route: str = "") -> None:
    """Render the section sidebar for a given domain."""
    sections = DOMAIN_SECTIONS.get(domain, [])
    with ui.column().classes("w-full").style(
        f"width: 200px; background: {COLORS['bg_sidebar']}; "
        f"border-right: 1px solid {COLORS['border']}; padding: 12px 0; min-height: 100vh;"
    ):
        for section in sections:
            ui.label(section["section"]).classes("section-title").style("padding: 4px 16px; margin-top: 12px;")
            for item in section["items"]:
                is_active = active_route == item["route"]
                style = (
                    f"padding: 8px 16px; font-size: 13px; cursor: pointer; "
                    f"color: {COLORS['text_primary'] if is_active else COLORS['text_muted']}; "
                    f"{'background: ' + COLORS['bg_hover'] + '; border-left: 2px solid ' + COLORS['accent'] + ';' if is_active else ''}"
                )
                with ui.link(target=item["route"]).style("text-decoration: none;"):
                    with ui.row().classes("items-center gap-2").style(style):
                        ui.icon(item["icon"]).style("font-size: 16px;")
                        ui.label(item["label"])
```

- [ ] **Step 2: Create app shell**

```python
# src/dex_studio/components/app_shell.py
"""App shell — top bar with domain tabs, project switcher, command palette trigger."""

from __future__ import annotations

from nicegui import ui

from dex_studio.theme import COLORS

__all__ = ["app_shell"]

DOMAINS = [
    {"name": "Data", "key": "data", "route": "/data"},
    {"name": "ML", "key": "ml", "route": "/ml"},
    {"name": "AI", "key": "ai", "route": "/ai"},
    {"name": "System", "key": "system", "route": "/system"},
]


def app_shell(active_domain: str = "data", project_name: str = "default") -> None:
    """Render the top navigation bar."""
    with ui.row().classes("w-full items-center justify-between").style(
        f"padding: 8px 16px; background: {COLORS['bg_secondary']}; "
        f"border-bottom: 1px solid {COLORS['border']};"
    ):
        # Left: Logo + Domain Tabs
        with ui.row().classes("items-center gap-6"):
            ui.label("⬡ DEX Studio").style(
                f"font-weight: 700; font-size: 15px; color: {COLORS['accent']};"
            )

            # Project switcher
            with ui.row().classes("items-center gap-2").style(
                f"padding: 5px 12px; background: {COLORS['border']}; border-radius: 6px; cursor: pointer;"
            ):
                ui.label(project_name).style("font-weight: 500; font-size: 13px;")
                ui.label("▾").style(f"color: {COLORS['text_dim']};")

            # Separator
            ui.element("div").style(f"width: 1px; height: 20px; background: {COLORS['border']};")

            # Domain tabs
            with ui.row().classes("gap-1"):
                for domain in DOMAINS:
                    is_active = domain["key"] == active_domain
                    style = (
                        f"padding: 6px 14px; border-radius: 6px; font-size: 12px; cursor: pointer; "
                        f"text-decoration: none; "
                    )
                    if is_active:
                        style += f"background: {COLORS['accent']}; color: white; font-weight: 600;"
                    else:
                        style += f"color: {COLORS['text_muted']};"
                    ui.link(domain["name"], target=domain["route"]).style(style)

        # Right: Search + Status
        with ui.row().classes("items-center gap-3"):
            with ui.row().classes("items-center gap-2").style(
                f"padding: 5px 12px; background: {COLORS['border']}; border-radius: 6px; "
                f"color: {COLORS['text_dim']}; font-size: 12px; min-width: 180px;"
            ):
                ui.label("⌘ Search...").style(f"color: {COLORS['text_dim']};")
                ui.label("Ctrl+K").style(
                    f"margin-left: auto; background: {COLORS['bg_hover']}; "
                    f"padding: 1px 6px; border-radius: 3px; font-size: 10px;"
                )
```

- [ ] **Step 3: Create project_card.py**

```python
# src/dex_studio/components/project_card.py
"""Project card — used in project hub and switcher dropdown."""

from __future__ import annotations

from typing import Any

from nicegui import ui

from dex_studio.config import ProjectEntry
from dex_studio.theme import COLORS

__all__ = ["project_card"]


def project_card(project: ProjectEntry, *, on_click: Any = None) -> None:
    """Render a project card for the hub."""
    with ui.card().classes("dex-card w-full cursor-pointer").style("padding: 16px;").on("click", on_click):
        with ui.row().classes("items-center gap-4 w-full"):
            ui.icon(project.icon or "folder").style(
                f"font-size: 24px; color: {COLORS['accent']};"
            )
            with ui.column().classes("flex-1"):
                ui.label(project.name).style("font-weight: 600; font-size: 14px;")
                ui.label(project.url).style(f"font-size: 12px; color: {COLORS['text_dim']};")
```

- [ ] **Step 4: Update components __init__.py**

Add new exports to `src/dex_studio/components/__init__.py`:

```python
from dex_studio.components.app_shell import app_shell
from dex_studio.components.domain_sidebar import domain_sidebar
from dex_studio.components.project_card import project_card
```

- [ ] **Step 5: Commit**

```bash
git add src/dex_studio/components/app_shell.py src/dex_studio/components/domain_sidebar.py src/dex_studio/components/project_card.py src/dex_studio/components/__init__.py
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "feat: app shell with domain tabs, section sidebar, and project card"
```

---

## Task 6: Agent Chat Components

**Files:**
- Create: `src/dex_studio/components/chat_message.py`
- Create: `src/dex_studio/components/tool_call_block.py`
- Create: `src/dex_studio/components/inspector_panel.py`

- [ ] **Step 1: Create chat_message.py**

```python
# src/dex_studio/components/chat_message.py
"""Chat message bubble — user or agent with tool call rendering."""

from __future__ import annotations

from typing import Any

from nicegui import ui

from dex_studio.theme import COLORS

__all__ = ["chat_message"]


def chat_message(
    role: str,
    content: str,
    *,
    tool_calls: list[dict[str, Any]] | None = None,
) -> None:
    """Render a chat message bubble."""
    is_user = role == "user"
    avatar_bg = COLORS["border"] if is_user else COLORS["accent"]
    avatar_text = "U" if is_user else "A"

    with ui.row().classes("gap-3 w-full").style("margin-bottom: 20px;"):
        # Avatar
        ui.label(avatar_text).style(
            f"width: 28px; height: 28px; background: {avatar_bg}; border-radius: 50%; "
            f"display: flex; align-items: center; justify-content: center; font-size: 12px; "
            f"flex-shrink: 0; color: white;"
        )

        with ui.column().classes("flex-1"):
            # Tool calls (if any)
            if tool_calls:
                for tc in tool_calls:
                    from dex_studio.components.tool_call_block import tool_call_block
                    tool_call_block(
                        name=tc.get("name", "unknown"),
                        args=tc.get("args", ""),
                        duration=tc.get("duration"),
                        status=tc.get("status", "done"),
                    )

            # Message content
            ui.label(content).style(
                f"background: {COLORS['bg_secondary']}; padding: 12px 16px; "
                f"border-radius: 12px; border-top-left-radius: {'12px' if is_user else '4px'}; "
                f"max-width: 80%;"
            )
```

- [ ] **Step 2: Create tool_call_block.py**

```python
# src/dex_studio/components/tool_call_block.py
"""Tool call block — expandable display of tool invocations in agent chat."""

from __future__ import annotations

from nicegui import ui

from dex_studio.theme import COLORS

__all__ = ["tool_call_block"]


def tool_call_block(
    name: str,
    args: str = "",
    *,
    duration: float | None = None,
    status: str = "done",
) -> None:
    """Render an expandable tool call block."""
    status_icon = "✓" if status == "done" else "⏳"
    status_color = COLORS["success"] if status == "done" else COLORS["warning"]
    duration_text = f"{duration:.1f}s" if duration else ""

    with ui.expansion().classes("w-full").style(
        f"background: {COLORS['bg_hover']}; border: 1px solid {COLORS['border']}; "
        f"border-radius: 8px; margin-bottom: 8px;"
    ):
        with ui.row().classes("items-center gap-2").style("font-size: 12px;"):
            ui.label("⚡").style(f"color: {COLORS['accent']};")
            ui.label(name).style(f"color: {COLORS['accent_light']}; font-family: monospace;")
            if args:
                ui.label("→").style(f"color: {COLORS['text_faint']};")
                ui.label(args).style(
                    f"color: {COLORS['text_dim']}; font-family: monospace; font-size: 11px; "
                    f"overflow: hidden; text-overflow: ellipsis; max-width: 300px;"
                )
            if duration_text:
                ui.label(f"{status_icon} {duration_text}").style(
                    f"margin-left: auto; color: {status_color}; font-size: 10px;"
                )
```

- [ ] **Step 3: Create inspector_panel.py**

```python
# src/dex_studio/components/inspector_panel.py
"""Inspector panel — collapsible right panel for detail views."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Generator

from nicegui import ui

from dex_studio.theme import COLORS

__all__ = ["inspector_panel"]


@contextmanager
def inspector_panel(
    title: str = "Inspector",
    width: int = 280,
) -> Generator[ui.column, None, None]:
    """Render a collapsible right inspector panel. Yields a column for content."""
    with ui.column().style(
        f"width: {width}px; background: {COLORS['bg_sidebar']}; "
        f"border-left: 1px solid {COLORS['border']}; overflow-y: auto;"
    ) as panel:
        ui.label(title).style(
            f"padding: 12px 16px; border-bottom: 1px solid {COLORS['border']}; "
            f"font-size: 12px; font-weight: 600;"
        )
        content = ui.column().classes("w-full")
        yield content
```

- [ ] **Step 4: Commit**

```bash
git add src/dex_studio/components/chat_message.py src/dex_studio/components/tool_call_block.py src/dex_studio/components/inspector_panel.py
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "feat: agent chat components — chat message, tool call block, inspector panel"
```

---

## Task 7: App Bootstrap Rewrite

**Files:**
- Rewrite: `src/dex_studio/app.py`
- Create: `src/dex_studio/pages/__init__.py` (update)
- Create: `src/dex_studio/pages/project_hub.py`

- [ ] **Step 1: Create project hub page**

```python
# src/dex_studio/pages/project_hub.py
"""Project Hub — launch screen with project list."""

from __future__ import annotations

from nicegui import app, ui

from dex_studio.components.project_card import project_card
from dex_studio.config import ProjectEntry, load_projects
from dex_studio.theme import COLORS

__all__ = ["project_hub_page"]


@ui.page("/")
async def project_hub_page() -> None:
    """Render the project hub landing page."""
    from dex_studio.theme import apply_global_styles

    apply_global_styles()

    projects = load_projects()

    with ui.column().classes("items-center justify-center w-full").style("padding: 40px;"):
        # Header
        ui.label("⬡ DEX Studio").style(
            f"font-size: 28px; font-weight: 700; color: {COLORS['accent']};"
        )
        ui.label("Unified Data + ML + AI Platform").style(
            f"font-size: 14px; color: {COLORS['text_dim']}; margin-top: 4px;"
        )

        # Actions
        with ui.row().classes("gap-3 mt-8"):
            ui.button("+ New Project").style(
                f"background: {COLORS['accent']}; color: white; border-radius: 8px;"
            )
            ui.button("Import dex.yaml").props("outline").style("border-radius: 8px;")

        # Project list
        if projects:
            ui.label("RECENT PROJECTS").classes("section-title mt-8 mb-3")
            with ui.column().classes("w-full gap-2").style("max-width: 720px;"):
                for proj in projects:
                    project_card(proj, on_click=lambda p=proj: ui.navigate.to(f"/data?project={p.name}"))
        else:
            from dex_studio.components.empty_state import empty_state

            empty_state(
                message="No projects configured yet",
                icon="folder_open",
                action_label="+ New Project",
            )
```

- [ ] **Step 2: Rewrite app.py**

```python
# src/dex_studio/app.py
"""DEX Studio application bootstrap."""

from __future__ import annotations

from typing import Any

import logging

from nicegui import app, ui

from dex_studio.client import DexClient
from dex_studio.config import StudioConfig

logger = logging.getLogger(__name__)

__all__ = ["start"]


def _register_pages() -> None:
    """Import all page modules to register their routes."""
    from dex_studio.pages import project_hub  # noqa: F401
    from dex_studio.pages.data import dashboard, lineage, pipelines, quality, sources, warehouse  # noqa: F401
    from dex_studio.pages.ml import dashboard as ml_dash, drift, experiments, features, models, predictions  # noqa: F401
    from dex_studio.pages.ai import agents, collections, dashboard as ai_dash, retrieval, tools  # noqa: F401
    from dex_studio.pages.system import components, connection, logs, metrics, settings, status  # noqa: F401


def start(config: StudioConfig | None = None) -> None:
    """Launch DEX Studio."""
    if config is None:
        from dex_studio.config import load_config
        config = load_config()

    client = DexClient(config)
    app.storage.general["config"] = config
    app.storage.general["client"] = client

    async def on_startup() -> None:
        await client.connect()

    async def on_shutdown() -> None:
        await client.close()

    app.on_startup(on_startup)
    app.on_shutdown(on_shutdown)

    _register_pages()

    native = config.native_mode
    ui.run(
        title="DEX Studio",
        host=config.host,
        port=config.port,
        dark=config.theme == "dark",
        native=native,
        window_size=(config.window_width, config.window_height) if native else None,
        storage_secret="dex-studio-secret",
        reload=False,
    )
```

- [ ] **Step 3: Create page directory structure**

Create `__init__.py` files for page subdirectories:

```bash
mkdir -p src/dex_studio/pages/data
mkdir -p src/dex_studio/pages/ml
mkdir -p src/dex_studio/pages/ai
mkdir -p src/dex_studio/pages/system
touch src/dex_studio/pages/data/__init__.py
touch src/dex_studio/pages/ml/__init__.py
touch src/dex_studio/pages/ai/__init__.py
touch src/dex_studio/pages/system/__init__.py
```

- [ ] **Step 4: Commit**

```bash
git add src/dex_studio/app.py src/dex_studio/pages/
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "feat: rewrite app bootstrap with domain routing and project hub"
```

---

## Task 8: Data Domain Pages

**Files:**
- Create: `src/dex_studio/pages/data/dashboard.py`
- Create: `src/dex_studio/pages/data/pipelines.py`
- Create: `src/dex_studio/pages/data/sources.py`
- Create: `src/dex_studio/pages/data/warehouse.py`
- Create: `src/dex_studio/pages/data/quality.py`
- Create: `src/dex_studio/pages/data/lineage.py`

Each page follows the same pattern:
1. Apply global styles
2. Render app_shell with `active_domain="data"`
3. Render domain_sidebar with `domain="data"` and active_route
4. Render breadcrumb
5. Fetch data from DexClient
6. Render page content

- [ ] **Step 1: Create data dashboard page**

```python
# src/dex_studio/pages/data/dashboard.py
"""Data Dashboard — overview of pipelines, sources, and quality."""

from __future__ import annotations

from nicegui import app, ui

from dex_studio.client import DexClient
from dex_studio.components.app_shell import app_shell
from dex_studio.components.breadcrumb import breadcrumb
from dex_studio.components.domain_sidebar import domain_sidebar
from dex_studio.components.metric_card import metric_card
from dex_studio.theme import COLORS, apply_global_styles


@ui.page("/data")
async def data_dashboard() -> None:
    apply_global_styles()
    client: DexClient = app.storage.general["client"]

    app_shell(active_domain="data")
    with ui.row().classes("w-full flex-1").style("min-height: calc(100vh - 50px);"):
        domain_sidebar("data", active_route="/data")
        with ui.column().classes("flex-1"):
            breadcrumb("Data", "Dashboard")
            with ui.column().classes("p-6 gap-4 w-full"):
                # Metrics row
                with ui.row().classes("gap-3"):
                    try:
                        pipelines = await client.list_pipelines()
                        metric_card("Pipelines", pipelines.get("count", 0))
                    except Exception:
                        metric_card("Pipelines", "—")

                    try:
                        sources = await client.list_sources()
                        metric_card("Sources", sources.get("count", 0))
                    except Exception:
                        metric_card("Sources", "—")

                    try:
                        quality = await client.data_quality_summary()
                        pass_rate = quality.get("overall_pass_rate", 0)
                        metric_card("Quality", f"{pass_rate}%", color=COLORS["success"])
                    except Exception:
                        metric_card("Quality", "—")
```

- [ ] **Step 2: Create pipelines page**

```python
# src/dex_studio/pages/data/pipelines.py
"""Data Pipelines — list, inspect, and run pipelines."""

from __future__ import annotations

from nicegui import app, ui

from dex_studio.client import DexClient
from dex_studio.components.app_shell import app_shell
from dex_studio.components.breadcrumb import breadcrumb
from dex_studio.components.data_table import data_table
from dex_studio.components.domain_sidebar import domain_sidebar
from dex_studio.components.empty_state import empty_state
from dex_studio.theme import apply_global_styles


@ui.page("/data/pipelines")
async def data_pipelines() -> None:
    apply_global_styles()
    client: DexClient = app.storage.general["client"]

    app_shell(active_domain="data")
    with ui.row().classes("w-full flex-1").style("min-height: calc(100vh - 50px);"):
        domain_sidebar("data", active_route="/data/pipelines")
        with ui.column().classes("flex-1"):
            breadcrumb("Data", "Pipelines")
            with ui.column().classes("p-6 gap-4 w-full"):
                ui.label("Pipelines").style("font-size: 20px; font-weight: 600;")

                try:
                    result = await client.list_pipelines()
                    pipeline_names = result.get("pipelines", [])
                    if not pipeline_names:
                        empty_state("No pipelines configured")
                        return

                    rows = []
                    for name in pipeline_names:
                        detail = await client.get_pipeline(name)
                        rows.append({
                            "name": name,
                            "source": detail.get("source", "—"),
                            "transforms": detail.get("transforms", 0),
                            "schedule": detail.get("schedule") or "—",
                        })

                    columns = [
                        {"name": "name", "label": "Pipeline", "field": "name"},
                        {"name": "source", "label": "Source", "field": "source"},
                        {"name": "transforms", "label": "Transforms", "field": "transforms"},
                        {"name": "schedule", "label": "Schedule", "field": "schedule"},
                    ]
                    data_table(columns=columns, rows=rows, title="Configured Pipelines")

                except Exception as exc:
                    ui.label(f"Error loading pipelines: {exc}").style("color: red;")
```

- [ ] **Step 3: Create sources, warehouse, quality, lineage pages**

Each follows the same pattern as pipelines. Create stub pages that:
- Render shell + sidebar + breadcrumb
- Fetch from DexClient
- Show data_table or empty_state

Files to create:
- `src/dex_studio/pages/data/sources.py` — lists sources from `client.list_sources()`
- `src/dex_studio/pages/data/warehouse.py` — lists medallion layers from `client.warehouse_layers()`
- `src/dex_studio/pages/data/quality.py` — shows quality summary from `client.data_quality_summary()`
- `src/dex_studio/pages/data/lineage.py` — lists lineage events from `client.list_lineage()`

Each page: `@ui.page("/data/<name>")`, same shell/sidebar/breadcrumb pattern. See pipelines page for the exact template to follow.

- [ ] **Step 4: Commit**

```bash
git add src/dex_studio/pages/data/
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "feat: data domain pages — dashboard, pipelines, sources, warehouse, quality, lineage"
```

---

## Task 9: ML Domain Pages

**Files:**
- Create: `src/dex_studio/pages/ml/dashboard.py`
- Create: `src/dex_studio/pages/ml/experiments.py`
- Create: `src/dex_studio/pages/ml/models.py`
- Create: `src/dex_studio/pages/ml/predictions.py`
- Create: `src/dex_studio/pages/ml/features.py`
- Create: `src/dex_studio/pages/ml/drift.py`

All pages follow the same shell + sidebar + breadcrumb pattern with `active_domain="ml"`.

- [ ] **Step 1: Create ML dashboard**

Route: `/ml`. Shows metric cards for experiments count, models count, drift alerts. Fetches from `client.list_experiments()`, `client.list_models()`.

- [ ] **Step 2: Create experiments page**

Route: `/ml/experiments`. Lists experiments with `client.list_experiments()`. Shows data_table with columns: name, id.

- [ ] **Step 3: Create models page**

Route: `/ml/models`. Lists models with `client.list_models()`. Includes promote action button.

- [ ] **Step 4: Create predictions page**

Route: `/ml/predictions`. Prediction playground with model name input, features JSON textarea, submit button. Calls `client.predict(model_name, features)`.

- [ ] **Step 5: Create features page**

Route: `/ml/features`. Lists feature groups with `client.list_feature_groups()`. Entity key lookup.

- [ ] **Step 6: Create drift page**

Route: `/ml/drift`. Drift check per pipeline with `client.check_drift(pipeline)`. Shows PSI scores.

- [ ] **Step 7: Commit**

```bash
git add src/dex_studio/pages/ml/
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "feat: ML domain pages — dashboard, experiments, models, predictions, features, drift"
```

---

## Task 10: AI Domain Pages

**Files:**
- Create: `src/dex_studio/pages/ai/dashboard.py`
- Create: `src/dex_studio/pages/ai/agents.py`
- Create: `src/dex_studio/pages/ai/tools.py`
- Create: `src/dex_studio/pages/ai/collections.py`
- Create: `src/dex_studio/pages/ai/retrieval.py`

- [ ] **Step 1: Create AI dashboard**

Route: `/ai`. Shows metric cards for agents count, tools count. Fetches from `client.list_agents()`, `client.list_tools()`.

- [ ] **Step 2: Create agent chat page (most complex)**

Route: `/ai/agents`. This is the most interactive page.

Layout:
- Left panel (~65%): Chat message list + input bar
- Right panel (~35%): Inspector panel with agent config, tools, session stats

Key implementation:
```python
@ui.page("/ai/agents")
async def ai_agents() -> None:
    apply_global_styles()
    client: DexClient = app.storage.general["client"]

    app_shell(active_domain="ai")
    with ui.row().classes("w-full flex-1").style("min-height: calc(100vh - 50px);"):
        domain_sidebar("ai", active_route="/ai/agents")

        # Main content area
        with ui.row().classes("flex-1"):
            # Chat area
            with ui.column().classes("flex-1").style(
                f"border-right: 1px solid {COLORS['border']};"
            ):
                # Agent selector
                agents_data = await client.list_agents()
                agent_names = [a["name"] for a in agents_data.get("agents", [])]
                selected_agent = ui.select(agent_names, label="Agent").classes("w-48")

                # Messages container
                messages_container = ui.column().classes("flex-1 p-4 overflow-y-auto")

                # Input
                with ui.row().classes("w-full p-4 gap-2 items-end").style(
                    f"border-top: 1px solid {COLORS['border']};"
                ):
                    message_input = ui.textarea(placeholder="Ask the agent anything...").classes("flex-1")

                    async def send_message() -> None:
                        msg = message_input.value
                        if not msg or not selected_agent.value:
                            return
                        message_input.value = ""
                        with messages_container:
                            chat_message("user", msg)
                        result = await client.agent_chat(selected_agent.value, msg)
                        with messages_container:
                            chat_message("agent", result["response"])

                    ui.button("Send", on_click=send_message)

            # Inspector panel
            with inspector_panel("Inspector") as panel:
                # Agent config, tools, session stats rendered here
                pass
```

- [ ] **Step 3: Create tools page**

Route: `/ai/tools`. Lists tools from `client.list_tools()`. Shows data_table with name, description.

- [ ] **Step 4: Create collections and retrieval pages**

Route: `/ai/collections` and `/ai/retrieval`. Placeholder pages (these depend on vector store endpoints that may not be fully wired in Phase 6A).

- [ ] **Step 5: Commit**

```bash
git add src/dex_studio/pages/ai/
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "feat: AI domain pages — dashboard, agent chat, tools, collections, retrieval"
```

---

## Task 11: System Domain Pages

**Files:**
- Create: `src/dex_studio/pages/system/status.py`
- Create: `src/dex_studio/pages/system/components.py`
- Create: `src/dex_studio/pages/system/metrics.py`
- Create: `src/dex_studio/pages/system/logs.py`
- Create: `src/dex_studio/pages/system/settings.py`
- Create: `src/dex_studio/pages/system/connection.py`

- [ ] **Step 1: Create system status page**

Route: `/system`. Shows overall health from `client.health()` and component summary from `client.components()`.

- [ ] **Step 2: Create components page**

Route: `/system/components`. Data table of component health from `client.components()`. Columns: name, status, details.

- [ ] **Step 3: Create metrics page**

Route: `/system/metrics`. Displays Prometheus metrics. Fetches raw metrics text from `GET /metrics`.

- [ ] **Step 4: Create logs page**

Route: `/system/logs`. Structured log viewer from `client.logs()`. Filter by level.

- [ ] **Step 4b: Create traces page**

Route: `/system/traces`. OpenTelemetry trace viewer. Shows placeholder if tracing disabled. Fetches from `client.traces()`.

- [ ] **Step 5: Create settings page**

Route: `/system/settings`. Connection config (URL, token, timeout), test connection button, save to `~/.dex-studio/config.yaml`.

- [ ] **Step 6: Create connection page**

Route: `/system/connection`. Multi-project connection manager. Lists projects from `load_projects()`, add/remove/edit.

- [ ] **Step 7: Commit**

```bash
git add src/dex_studio/pages/system/
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "feat: system domain pages — status, components, metrics, logs, settings, connection"
```

---

## Task 12: Delete Old Pages + Cleanup

**Files:**
- Delete: `src/dex_studio/pages/overview.py`
- Delete: `src/dex_studio/pages/health.py`
- Delete: `src/dex_studio/pages/data_quality.py`
- Delete: `src/dex_studio/pages/lineage.py`
- Delete: `src/dex_studio/pages/ml_models.py`
- Delete: `src/dex_studio/pages/settings.py`
- Update: `src/dex_studio/pages/__init__.py`

- [ ] **Step 1: Delete old page files**

```bash
git rm src/dex_studio/pages/overview.py
git rm src/dex_studio/pages/health.py
git rm src/dex_studio/pages/data_quality.py
git rm src/dex_studio/pages/lineage.py
git rm src/dex_studio/pages/ml_models.py
git rm src/dex_studio/pages/settings.py
```

- [ ] **Step 2: Update pages __init__.py**

```python
# src/dex_studio/pages/__init__.py
"""DEX Studio pages — organized by domain."""

from __future__ import annotations
```

- [ ] **Step 3: Commit**

```bash
git add -A src/dex_studio/pages/
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "chore: remove old flat pages, replaced by domain-organized pages"
```

---

## Task 13: CLI Update

**Files:**
- Rewrite: `src/dex_studio/cli.py`

- [ ] **Step 1: Update CLI with project flag**

Add `--project` flag to select a project from `projects.yaml`:

```python
parser.add_argument("--project", type=str, help="Project name from projects.yaml")
```

When `--project` is specified, load that project's URL/token and override the config.

- [ ] **Step 2: Run CLI tests**

Run: `uv run pytest tests/unit/test_cli.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add src/dex_studio/cli.py tests/unit/test_cli.py
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "feat: CLI supports --project flag for multi-project switching"
```

---

## Task 14: Integration Test

**Files:**
- Create: `tests/integration/test_app.py`

- [ ] **Step 1: Write integration test**

```python
# tests/integration/test_app.py
"""Integration test — verify app bootstraps and pages register."""

from __future__ import annotations

from dex_studio.config import StudioConfig


class TestAppBootstrap:
    def test_page_imports(self) -> None:
        """All page modules should import without error."""
        # This verifies no circular imports or missing deps
        from dex_studio.pages import project_hub  # noqa: F401
        from dex_studio.pages.data import dashboard, pipelines, sources  # noqa: F401
        from dex_studio.pages.ml import experiments, models  # noqa: F401
        from dex_studio.pages.ai import agents, tools  # noqa: F401
        from dex_studio.pages.system import status, settings  # noqa: F401

    def test_components_import(self) -> None:
        """All components should import without error."""
        from dex_studio.components import (  # noqa: F401
            app_shell, breadcrumb, data_table, domain_sidebar,
            empty_state, metric_card, status_badge,
        )
```

- [ ] **Step 2: Run integration test**

Run: `uv run pytest tests/integration/test_app.py -v`
Expected: All PASS

- [ ] **Step 3: Run full validation**

```bash
uv run poe lint
uv run poe typecheck
uv run poe test
```

- [ ] **Step 4: Commit**

```bash
git add tests/integration/test_app.py
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "test: integration test for app bootstrap and page registration"
```

---

## Task 15: Final Validation

- [ ] **Step 1: Run full validation pipeline**

```bash
uv run poe lint
uv run poe typecheck
uv run poe test
```

- [ ] **Step 2: Visual smoke test**

```bash
# Start DEX engine in background
cd /home/jay/workspace/DataEngineX/dex && uv run poe dev &
sleep 3

# Start DEX Studio
cd /home/jay/workspace/DataEngineX/dex-studio && uv run poe dev
```

Verify:
- Project hub loads at `/`
- Data domain tabs navigate correctly
- Pipelines page shows configured pipelines
- System/Components shows backend health
- Agent chat sends messages and receives responses

- [ ] **Step 3: Commit any fixes**

If any issues found during smoke test, fix and commit.
