# CareerDEX Example — Full-Stack DataEngineX Demo

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix critical dex/dex-studio bugs and create a comprehensive careerdex example project that demonstrates all DataEngineX features — sources, lakehouse layers, pipeline history, lineage, ML, and AI — all visible and functional in dex-studio.

**Architecture:** Three parallel tracks: (1) dex bug fixes + pipeline run history feature; (2) dex-studio field name fixes + history UI + AI guide messages; (3) careerdex data files + config. Tracks 1 and 3 can execute in parallel; track 2 depends on track 1 for the new API endpoint shape.

**Tech Stack:** Python 3.13 · FastAPI · DuckDB · structlog · Pydantic · NiceGUI · pytest · uv

---

## Pre-flight: Confirmed Bugs (from code inspection)

**Bug 1 — Lakehouse path mismatch (BLOCKING)**
`runner.py:73` defaults `_data_dir` to `Path(".dex/data")`. `data.py:55` reads `Path(".dex/lakehouse")`. Pipelines write to `.dex/data/<layer>/` but warehouse API reads `.dex/lakehouse/<layer>/`. Fix: change runner default to `Path(".dex/lakehouse")`.

**Bug 2 — Lineage never recorded**
`factory.py:35-36` creates `PipelineRunner(config)` and `PersistentLineage(...)` independently. `PipelineRunner._extract()` and `_load()` never call `lineage.record()`. Fix: add optional `lineage` param to runner and pass it from factory.

**Bug 3 — Sources page field mismatch**
`data.py:23` returns `{"name", "type", "path"}`. `sources.py:71` maps `src.get("connector_type")` — always "—". Fix: `connector_type` → `type`.

**Bug 4 — Lineage page field mismatches (3 issues)**
`LineageEvent.to_dict()` (via `asdict()`) returns `event_id`, `destination`, `layer`. `lineage.py` page maps `id`, `target`, and has no `layer` column. Fix: align column names, fix `row_key`.

**Bug 5 — `deduplicate` uses `key:` not `columns:`**
`DeduplicateTransform.__init__` takes `key`, not `columns`. `_build_transform_kwargs` maps them separately. Using `columns:` with `deduplicate` silently fails. Fix: careerdex config must use `key: [...]`.

**Bug 6 — No `sql` transform type registered**
Only `filter`, `derive`, `cast`, `deduplicate` are registered. Using `type: sql` raises `KeyError` at runtime. Fix: careerdex gold-layer pipeline uses `filter` passthrough instead.

**Pending uncommitted changes in working tree:**
- `dex/src/dataenginex/api/routers/ai.py` — `ConnectionError` → 503 fix
- `dex-studio/src/dex_studio/components/app_shell.py` — project switcher dropdown
- `dex-studio/src/dex_studio/pages/data/warehouse.py` — `layer.get("name", ...)` dict fix
- `dex-studio/src/dex_studio/pages/project_hub.py` — import/new-project dialogs

---

## File Map

### dex repo
| File | Action | What changes |
|------|--------|--------------|
| `src/dataenginex/data/pipeline/runner.py` | Modify | Default path `.dex/data` → `.dex/lakehouse`; add `lineage` param; call `lineage.record()` in `_extract` and `_load` |
| `src/dataenginex/data/pipeline/run_history.py` | **Create** | `PipelineRunRecord` dataclass + `PipelineRunHistory` JSON-backed store |
| `src/dataenginex/api/schemas.py` | Modify | Add `PipelineRunRecordModel`, `PipelineRunHistoryResponse` Pydantic models |
| `src/dataenginex/api/factory.py` | Modify | Create `lineage` first; pass `lineage=` to `PipelineRunner`; init `PipelineRunHistory` |
| `src/dataenginex/api/routers/pipelines.py` | Modify | Record run after execution; add `GET /{name}/runs` endpoint |

### dex-studio repo
| File | Action | What changes |
|------|--------|--------------|
| `src/dex_studio/pages/data/sources.py` | Modify | Fix `connector_type` → `type` in columns and row mapping |
| `src/dex_studio/pages/data/lineage.py` | Modify | Fix `id`→`event_id`, `target`→`destination`; add `layer` column; fix `row_key` |
| `src/dex_studio/client.py` | Modify | Add `pipeline_runs(name)` method |
| `src/dex_studio/pages/data/pipelines.py` | Modify | Add `_RUN_COLUMNS`, `_render_run_history()`, history expansion section |
| `src/dex_studio/pages/ai/agents.py` | Modify | Handle 503 with Ollama setup guide message |

### careerdex repo
| File | Action | What changes |
|------|--------|--------------|
| `careerdex.yaml` | **Create** | Full-stack config: 4 sources, 5 pipelines, ML experiment, 2 AI agents, port 17003 |
| `data/jobs.csv` | **Create** | 20 job listings (18 active, 2 expired) |
| `data/candidates.csv` | **Create** | 15 candidate profiles (13 active, 2 inactive) |
| `data/skills.csv` | **Create** | 12 tech skills with categories and demand scores |
| `data/companies.csv` | **Create** | 8 companies with tiers |

---

## Task 0: Commit Pending Session Changes

**Branch:** `feature/session-fixes-2026-03-22`
**Repos:** dex (first — it's upstream), then dex-studio

- [ ] **0.1 — Commit dex pending change**

  ```bash
  cd /home/jay/workspace/DataEngineX/dex
  git checkout -b feature/session-fixes-2026-03-22
  git add src/dataenginex/api/routers/ai.py README.md uv.lock
  git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" \
    -m "fix: wrap agent.run() in try/except — ConnectionError → 503, Exception → 500"
  ```

  Expected: commit succeeds, `git status` shows only untracked `.dex/` and `.superpowers/`.

- [ ] **0.2 — Commit dex-studio pending changes**

  ```bash
  cd /home/jay/workspace/DataEngineX/dex-studio
  git checkout -b feature/session-fixes-2026-03-22
  git add src/dex_studio/components/app_shell.py \
           src/dex_studio/pages/data/warehouse.py \
           src/dex_studio/pages/project_hub.py
  git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" \
    -m "fix: project switcher dropdown, warehouse layer dict fix, project import dialog"
  ```

  Expected: commit succeeds, `git status` clean.

- [ ] **0.3 — Verify lint passes on both repos**

  ```bash
  cd /home/jay/workspace/DataEngineX/dex && uv run poe lint
  cd /home/jay/workspace/DataEngineX/dex-studio && uv run poe lint
  ```

  Expected: both exit 0.

---

## Task 1: Fix dex — Path Bug + Lineage Wiring + Run History

**Branch:** `feature/pipeline-run-history`
**Repo:** dex only
**Parallel with:** Task 3

- [ ] **1.1 — Create branch**

  ```bash
  cd /home/jay/workspace/DataEngineX/dex
  git checkout dev
  git checkout -b feature/pipeline-run-history
  ```

- [ ] **1.2 — Fix Bug 1: lakehouse path in `runner.py`**

  File: `src/dataenginex/data/pipeline/runner.py`, line 73

  ```python
  # Before:
  self._data_dir = data_dir or Path(".dex/data")

  # After:
  self._data_dir = data_dir or Path(".dex/lakehouse")
  ```

- [ ] **1.3 — Fix Bug 2: wire lineage into `PipelineRunner`**

  File: `src/dataenginex/data/pipeline/runner.py`

  Add import after existing imports:
  ```python
  from dataenginex.warehouse.lineage import PersistentLineage
  ```

  Update `__init__` signature and body:
  ```python
  def __init__(
      self,
      config: DexConfig,
      data_dir: Path | None = None,
      lineage: PersistentLineage | None = None,
  ) -> None:
      self._config = config
      self._data_dir = data_dir or Path(".dex/lakehouse")
      self._data_dir.mkdir(parents=True, exist_ok=True)
      self._lineage = lineage
  ```

  At end of `_extract`, before `return len(raw_data)`:
  ```python
  if self._lineage is not None:
      self._lineage.record(
          operation="ingest",
          layer="bronze",
          source=cfg.source,
          destination=f"bronze/{name}",
          input_count=len(raw_data),
          output_count=len(raw_data),
          pipeline_name=name,
          step_name="extract",
      )
  ```

  At end of `_load`, before `return rows`:
  ```python
  if self._lineage is not None:
      self._lineage.record(
          operation="load",
          layer=target_layer,
          source=f"bronze/{name}",
          destination=str(output_path),
          input_count=rows,
          output_count=rows,
          pipeline_name=name,
          step_name="load",
      )
  ```

- [ ] **1.4 — Create `run_history.py`**

  File: `src/dataenginex/data/pipeline/run_history.py` (new)

  ```python
  """JSON-backed pipeline run history store."""

  from __future__ import annotations

  import json
  import secrets
  from dataclasses import asdict, dataclass, field
  from datetime import UTC, datetime
  from pathlib import Path
  from typing import Any

  import structlog

  from dataenginex.data.pipeline.runner import PipelineResult

  logger = structlog.get_logger()

  __all__ = ["PipelineRunHistory", "PipelineRunRecord"]


  @dataclass
  class PipelineRunRecord:
      """A persisted record of a single pipeline execution."""

      run_id: str = field(default_factory=lambda: secrets.token_hex(6))
      pipeline_name: str = ""
      timestamp: str = field(
          default_factory=lambda: datetime.now(tz=UTC).isoformat()
      )
      success: bool = False
      rows_input: int = 0
      rows_output: int = 0
      steps_completed: int = 0
      duration_ms: float = 0.0
      error: str | None = None

      def to_dict(self) -> dict[str, Any]:
          """Serialize to plain dict."""
          return asdict(self)


  class PipelineRunHistory:
      """JSON-file-backed store for pipeline run records.

      Args:
          persist_path: Path to the JSON file. Parent dirs are created on first write.
      """

      def __init__(self, persist_path: str | Path) -> None:
          self._persist_path = Path(persist_path)
          self._records: list[PipelineRunRecord] = []
          if self._persist_path.exists():
              self._load()

      def record(self, result: PipelineResult, duration_ms: float) -> PipelineRunRecord:
          """Create and persist a run record from a PipelineResult."""
          rec = PipelineRunRecord(
              pipeline_name=result.pipeline,
              success=result.success,
              rows_input=result.rows_input,
              rows_output=result.rows_output,
              steps_completed=result.steps_completed,
              duration_ms=round(duration_ms, 2),
              error=result.error,
          )
          self._records.append(rec)
          self._save()
          logger.info(
              "run recorded",
              pipeline=result.pipeline,
              run_id=rec.run_id,
              success=result.success,
          )
          return rec

      def get_runs(self, pipeline_name: str) -> list[PipelineRunRecord]:
          """Return all runs for a specific pipeline, newest first."""
          return [r for r in reversed(self._records) if r.pipeline_name == pipeline_name]

      @property
      def all_runs(self) -> list[PipelineRunRecord]:
          """All run records, newest first."""
          return list(reversed(self._records))

      def _save(self) -> None:
          self._persist_path.parent.mkdir(parents=True, exist_ok=True)
          data = [r.to_dict() for r in self._records]
          self._persist_path.write_text(json.dumps(data, indent=2, default=str))

      def _load(self) -> None:
          raw = json.loads(self._persist_path.read_text())
          for item in raw:
              self._records.append(PipelineRunRecord(**item))
          logger.info(
              "run history loaded",
              count=len(self._records),
              path=str(self._persist_path),
          )
  ```

- [ ] **1.5 — Add Pydantic models to `schemas.py`**

  File: `src/dataenginex/api/schemas.py`

  Add after `PipelineResultResponse` (after line 29):
  ```python
  class PipelineRunRecordModel(BaseModel):
      run_id: str
      pipeline_name: str
      timestamp: str
      success: bool
      rows_input: int = 0
      rows_output: int = 0
      steps_completed: int = 0
      duration_ms: float = 0.0
      error: str | None = None


  class PipelineRunHistoryResponse(BaseModel):
      pipeline: str
      runs: list[PipelineRunRecordModel]
      count: int
  ```

  Note: named `PipelineRunRecordModel` to avoid collision with the `PipelineRunRecord` dataclass.

- [ ] **1.6 — Update `factory.py`**

  File: `src/dataenginex/api/factory.py`

  Replace lines 32-36 (the `PipelineRunner` + `PersistentLineage` block):
  ```python
  # Before:
  from dataenginex.data.pipeline.runner import PipelineRunner
  from dataenginex.warehouse.lineage import PersistentLineage

  app.state.pipeline_runner = PipelineRunner(config)
  app.state.lineage = PersistentLineage(".dex/lineage.json")

  # After:
  from dataenginex.data.pipeline.run_history import PipelineRunHistory
  from dataenginex.data.pipeline.runner import PipelineRunner
  from dataenginex.warehouse.lineage import PersistentLineage

  app.state.lineage = PersistentLineage(".dex/lineage.json")
  app.state.pipeline_runner = PipelineRunner(config, lineage=app.state.lineage)
  app.state.run_history = PipelineRunHistory(".dex/pipeline_runs.json")
  ```

  Order matters: `lineage` must be created before `PipelineRunner`.

- [ ] **1.7 — Update `routers/pipelines.py`**

  File: `src/dataenginex/api/routers/pipelines.py`

  Update imports:
  ```python
  from dataenginex.api.schemas import (
      PipelineResultResponse,
      PipelineRunHistoryResponse,
      PipelineRunRecordModel,
  )
  ```

  In `run_pipeline`, add after `result = runner.run(pipeline_name)` and before the return:
  ```python
  request.app.state.run_history.record(result, duration_ms)
  ```

  Add new endpoint after `run_pipeline`:
  ```python
  @router.get("/{pipeline_name}/runs", response_model=PipelineRunHistoryResponse)
  def get_pipeline_runs(
      pipeline_name: str, request: Request
  ) -> PipelineRunHistoryResponse:
      """Return run history for a pipeline."""
      config = request.app.state.config
      if pipeline_name not in config.data.pipelines:
          raise HTTPException(
              status_code=404,
              detail=f"Pipeline '{pipeline_name}' not found",
          )
      run_history = request.app.state.run_history
      records = run_history.get_runs(pipeline_name)
      return PipelineRunHistoryResponse(
          pipeline=pipeline_name,
          runs=[PipelineRunRecordModel(**r.to_dict()) for r in records],
          count=len(records),
      )
  ```

- [ ] **1.8 — Run validation**

  ```bash
  cd /home/jay/workspace/DataEngineX/dex
  uv run poe lint && uv run poe typecheck && uv run poe test
  ```

  Expected: all pass.

- [ ] **1.9 — Commit**

  ```bash
  git add src/dataenginex/data/pipeline/runner.py \
          src/dataenginex/data/pipeline/run_history.py \
          src/dataenginex/api/schemas.py \
          src/dataenginex/api/factory.py \
          src/dataenginex/api/routers/pipelines.py
  git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" \
    -m "feat: pipeline run history store + GET /{name}/runs endpoint; fix lakehouse path mismatch and wire lineage into runner"
  ```

---

## Task 2: Fix dex-studio — Field Bugs + History UI + AI Guide

**Branch:** `feature/studio-pipeline-history`
**Repo:** dex-studio only
**Depends on:** Task 1 committed (for the new API endpoint shape)

- [ ] **2.1 — Create branch**

  ```bash
  cd /home/jay/workspace/DataEngineX/dex-studio
  git checkout dev
  git checkout -b feature/studio-pipeline-history
  ```

- [ ] **2.2 — Fix Bug 3: sources page `connector_type` → `type`**

  File: `src/dex_studio/pages/data/sources.py`

  Update `_SOURCE_COLUMNS`:
  ```python
  _SOURCE_COLUMNS: list[dict[str, Any]] = [
      {"name": "name", "label": "Name", "field": "name", "align": "left"},
      {
          "name": "type",
          "label": "Connector Type",
          "field": "type",
          "align": "left",
      },
  ]
  ```

  Update the row mapping in `for src in sources:`:
  ```python
  rows.append(
      {
          "name": src.get("name", "—"),
          "type": src.get("type", "—"),
      }
  )
  ```

- [ ] **2.3 — Fix Bug 4: lineage page field mismatches**

  File: `src/dex_studio/pages/data/lineage.py`

  Replace `_LINEAGE_COLUMNS`:
  ```python
  _LINEAGE_COLUMNS: list[dict[str, Any]] = [
      {"name": "event_id", "label": "ID", "field": "event_id", "align": "left"},
      {"name": "layer", "label": "Layer", "field": "layer", "align": "left"},
      {"name": "source", "label": "Source", "field": "source", "align": "left"},
      {"name": "destination", "label": "Destination", "field": "destination", "align": "left"},
      {"name": "operation", "label": "Operation", "field": "operation", "align": "left"},
      {"name": "timestamp", "label": "Timestamp", "field": "timestamp", "align": "left"},
  ]
  ```

  Replace `_event_to_row` body:
  ```python
  def _event_to_row(evt: Any) -> dict[str, Any] | None:
      if not isinstance(evt, dict):
          return None
      return {
          "event_id": evt.get("event_id", "—"),
          "layer": evt.get("layer", "—"),
          "source": evt.get("source", "—"),
          "destination": evt.get("destination", "—"),
          "operation": evt.get("operation", "—"),
          "timestamp": evt.get("timestamp", "—"),
      }
  ```

  Fix `data_table` call: `row_key="event_id"` (was `"id"`).

  Fix `_on_row_click`: `e.args.get("event_id", "")` (was `"id"`).

- [ ] **2.4 — Add `pipeline_runs` to `client.py`**

  File: `src/dex_studio/client.py`

  Add after `run_pipeline` method:
  ```python
  async def pipeline_runs(self, name: str) -> dict[str, Any]:
      return await self._get(f"/api/v1/pipelines/{name}/runs")
  ```

- [ ] **2.5 — Add run history section to `pipelines.py`**

  File: `src/dex_studio/pages/data/pipelines.py`

  Add after `_PIPELINE_COLUMNS` definition:
  ```python
  _RUN_COLUMNS: list[dict[str, Any]] = [
      {"name": "run_id", "label": "Run ID", "field": "run_id", "align": "left"},
      {"name": "timestamp", "label": "Timestamp", "field": "timestamp", "align": "left"},
      {"name": "success", "label": "Status", "field": "success", "align": "left"},
      {"name": "rows_input", "label": "Rows In", "field": "rows_input", "align": "right"},
      {"name": "rows_output", "label": "Rows Out", "field": "rows_output", "align": "right"},
      {"name": "duration_ms", "label": "ms", "field": "duration_ms", "align": "right"},
  ]
  ```

  Add helper function before `_run_buttons`:
  ```python
  async def _render_run_history(client: DexClient, pipeline_name: str) -> None:
      """Render recent runs for a pipeline inside an expansion."""
      try:
          resp = await client.pipeline_runs(pipeline_name)
      except DexAPIError as exc:
          _log.warning("Failed to fetch run history for %s: %s", pipeline_name, exc)
          ui.label("Run history unavailable.").style(f"color: {COLORS['text_dim']}")
          return

      runs: list[dict[str, Any]] = resp.get("runs", [])
      if not runs:
          ui.label("No runs yet.").style(f"color: {COLORS['text_dim']}")
          return

      rows: list[dict[str, Any]] = [
          {
              "run_id": r.get("run_id", "—"),
              "timestamp": r.get("timestamp", "—")[:19].replace("T", " "),
              "success": "passed" if r.get("success") else "failed",
              "rows_input": r.get("rows_input", 0),
              "rows_output": r.get("rows_output", 0),
              "duration_ms": r.get("duration_ms", 0.0),
          }
          for r in runs
      ]
      data_table(_RUN_COLUMNS, rows, row_key="run_id")
  ```

  In `data_pipelines_page`, after `_run_buttons(client, rows)`, add:
  ```python
  ui.separator().classes("my-4")
  ui.label("Recent Runs").classes("text-lg font-semibold").style(
      f"color: {COLORS['text_primary']}"
  )
  for row in rows:
      with ui.expansion(row["name"], icon="history").classes("w-full"):
          await _render_run_history(client, row["name"])
  ```

- [ ] **2.6 — Handle 503 in `agents.py` with Ollama guide**

  File: `src/dex_studio/pages/ai/agents.py`

  In `send_message`, find the `except DexAPIError` block and replace its body:
  ```python
  except DexAPIError as exc:
      if exc.status_code == 503:
          response_text = (
              "LLM provider unavailable.\n\n"
              "To enable AI agents, start Ollama:\n"
              "  ollama serve\n"
              "  ollama pull qwen3:8b\n\n"
              "Then restart the DEX engine (dex serve --config ...)."
          )
      else:
          response_text = f"[Error {exc.status_code}: {exc}]"
      tool_calls = []
  ```

- [ ] **2.7 — Run validation**

  ```bash
  cd /home/jay/workspace/DataEngineX/dex-studio
  uv run poe lint && uv run poe typecheck && uv run poe test
  ```

  Expected: all pass.

- [ ] **2.8 — Commit**

  ```bash
  git add src/dex_studio/pages/data/sources.py \
          src/dex_studio/pages/data/lineage.py \
          src/dex_studio/client.py \
          src/dex_studio/pages/data/pipelines.py \
          src/dex_studio/pages/ai/agents.py
  git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" \
    -m "fix: sources connector_type→type, lineage event_id/destination/layer fields; feat: pipeline run history UI, 503 Ollama guide in agent chat"
  ```

---

## Task 3: Create careerdex Data Files + Config

**Branch:** `feature/careerdex-example`
**Repo:** careerdex
**Parallel with:** Task 1

Key corrections applied vs requirement spec:
- `deduplicate` uses `key:` not `columns:`
- No `type: sql` transform exists — gold layer uses `filter` passthrough

- [ ] **3.1 — Create branch**

  ```bash
  cd /home/jay/workspace/DataEngineX/careerdex
  git checkout dev
  git checkout -b feature/careerdex-example
  ```

- [ ] **3.2 — Create `data/jobs.csv`**

  File: `data/jobs.csv`

  ```csv
  id,title,company_id,location,salary_min,salary_max,experience_years,required_skills,posted_date,status
  J001,Senior Data Engineer,C001,San Francisco CA,140000,180000,5,Python;Spark;dbt;SQL,2024-01-15,active
  J002,ML Engineer,C002,New York NY,130000,170000,4,Python;PyTorch;MLflow;Kubernetes,2024-01-18,active
  J003,Data Scientist,C003,Austin TX,110000,145000,3,Python;R;Statistics;SQL;Tableau,2024-01-20,active
  J004,Analytics Engineer,C001,Remote,105000,135000,2,dbt;SQL;Looker;BigQuery,2024-01-22,active
  J005,Staff Data Engineer,C004,Seattle WA,160000,210000,8,Python;Spark;Kafka;Airflow;Terraform,2024-01-25,active
  J006,Junior Data Analyst,C005,Chicago IL,65000,85000,1,SQL;Excel;Tableau;Python,2024-01-28,active
  J007,AI/ML Research Scientist,C002,San Francisco CA,170000,230000,6,Python;PyTorch;Research;LLMs,2024-02-01,active
  J008,Data Platform Engineer,C003,Remote,125000,160000,4,Python;Spark;Kafka;AWS;Terraform,2024-02-03,active
  J009,Business Intelligence Developer,C006,Denver CO,90000,115000,3,SQL;Power BI;Azure;DAX,2024-02-05,active
  J010,Senior ML Engineer,C004,Seattle WA,155000,200000,6,Python;TensorFlow;Kubernetes;MLflow,2024-02-08,active
  J011,Data Engineer,C007,Miami FL,95000,125000,3,Python;SQL;Airflow;PostgreSQL,2024-02-10,active
  J012,Principal Data Scientist,C001,San Francisco CA,185000,240000,10,Python;Statistics;ML;Leadership,2024-02-12,active
  J013,MLOps Engineer,C002,Remote,135000,175000,4,Python;Docker;Kubernetes;MLflow;CI/CD,2024-02-14,active
  J014,Data Architect,C008,Boston MA,150000,195000,8,SQL;NoSQL;Architecture;Cloud;Spark,2024-02-16,active
  J015,Analytics Manager,C005,Chicago IL,130000,165000,6,SQL;Analytics;Leadership;Tableau,2024-02-18,active
  J016,Feature Engineer,C003,Austin TX,115000,148000,3,Python;Feature Store;ML;SQL,2024-02-20,expired
  J017,Data Quality Engineer,C006,Denver CO,100000,128000,3,Python;Great Expectations;dbt;SQL,2024-02-22,active
  J018,Streaming Data Engineer,C004,Seattle WA,140000,178000,5,Python;Kafka;Flink;Spark Streaming,2024-02-24,active
  J019,AI Product Manager,C001,San Francisco CA,160000,205000,5,AI;Product;Strategy;Data,2024-02-26,expired
  J020,Graph Data Engineer,C007,Miami FL,118000,152000,4,Python;Neo4j;Graph Algorithms;SQL,2024-02-28,active
  ```

- [ ] **3.3 — Create `data/candidates.csv`**

  File: `data/candidates.csv`

  ```csv
  id,name,email,location,experience_years,skills,desired_salary,status,applied_date
  K001,Alice Chen,alice.chen@email.com,San Francisco CA,6,Python;Spark;SQL;dbt;Airflow,155000,active,2024-02-01
  K002,Bob Martinez,bob.m@email.com,New York NY,4,Python;PyTorch;MLflow;Docker,135000,active,2024-02-03
  K003,Carol Johnson,carol.j@email.com,Remote,3,Python;SQL;Tableau;Statistics,108000,active,2024-02-05
  K004,David Kim,david.k@email.com,Seattle WA,8,Python;Spark;Kafka;Terraform;Kubernetes,168000,active,2024-02-07
  K005,Emma Osei,emma.o@email.com,Austin TX,2,SQL;Python;dbt;Looker,95000,active,2024-02-09
  K006,Frank Lee,frank.l@email.com,Chicago IL,5,SQL;Power BI;Azure;Analytics;DAX,118000,active,2024-02-11
  K007,Grace Wu,grace.w@email.com,Remote,7,Python;TensorFlow;MLflow;Kubernetes;Research,162000,active,2024-02-13
  K008,Henry Park,henry.p@email.com,Boston MA,9,Architecture;SQL;NoSQL;Cloud;Spark;Leadership,188000,active,2024-02-15
  K009,Iris Sharma,iris.s@email.com,Denver CO,3,SQL;Python;PostgreSQL;Airflow,102000,active,2024-02-17
  K010,James Brown,james.b@email.com,Miami FL,4,Python;Neo4j;Graph;SQL,120000,active,2024-02-19
  K011,Kate Wilson,kate.w@email.com,San Francisco CA,1,Python;SQL;Excel;Analytics,72000,active,2024-02-21
  K012,Liam Patel,liam.p@email.com,Remote,5,Python;Kafka;Flink;Spark;Docker,142000,inactive,2024-02-23
  K013,Maya Rodriguez,maya.r@email.com,New York NY,3,Python;PyTorch;Statistics;Research,125000,active,2024-02-25
  K014,Noah Thompson,noah.t@email.com,Seattle WA,6,Python;MLOps;Docker;Kubernetes;CI/CD,150000,active,2024-02-27
  K015,Olivia Green,olivia.g@email.com,Chicago IL,10,Leadership;Analytics;SQL;Strategy;Tableau,0,inactive,2024-02-28
  ```

- [ ] **3.4 — Create `data/skills.csv`**

  File: `data/skills.csv`

  ```csv
  id,name,category,demand_score
  S001,Python,Programming,98
  S002,SQL,Database,95
  S003,Apache Spark,Data Engineering,88
  S004,Apache Kafka,Data Engineering,82
  S005,dbt,Data Engineering,79
  S006,PyTorch,Machine Learning,85
  S007,TensorFlow,Machine Learning,81
  S008,MLflow,MLOps,74
  S009,Kubernetes,Infrastructure,86
  S010,Apache Airflow,Orchestration,80
  S011,Tableau,Visualization,71
  S012,Power BI,Visualization,68
  ```

- [ ] **3.5 — Create `data/companies.csv`**

  File: `data/companies.csv`

  ```csv
  id,name,industry,size_tier,location,founded_year
  C001,DataFirst Corp,Data & Analytics,enterprise,San Francisco CA,2012
  C002,NeuralTech AI,Artificial Intelligence,startup,San Francisco CA,2019
  C003,StreamScale Inc,Data Infrastructure,mid-market,Austin TX,2015
  C004,CloudData Systems,Cloud Services,enterprise,Seattle WA,2010
  C005,InsightEdge LLC,Business Intelligence,mid-market,Chicago IL,2014
  C006,AzureAnalytics,Cloud Services,mid-market,Denver CO,2016
  C007,DataBridge Solutions,Data Engineering,startup,Miami FL,2020
  C008,CoreArchitect Partners,Data Architecture,mid-market,Boston MA,2008
  ```

- [ ] **3.6 — Create `careerdex.yaml`**

  File: `careerdex.yaml`

  ```yaml
  project:
    name: careerdex
    version: "1.0.0"
    description: "AI-powered career intelligence platform"

  data:
    engine: duckdb
    sources:
      raw_jobs:
        type: csv
        path: data/jobs.csv
      raw_candidates:
        type: csv
        path: data/candidates.csv
      raw_skills:
        type: csv
        path: data/skills.csv
      raw_companies:
        type: csv
        path: data/companies.csv

    pipelines:
      ingest_jobs:
        source: raw_jobs
        transforms:
          - type: filter
            condition: "status = 'active'"
          - type: deduplicate
            key: [id]
        quality:
          completeness: 0.90
          uniqueness: [id]
        target:
          layer: bronze

      clean_jobs:
        source: raw_jobs
        depends_on: [ingest_jobs]
        transforms:
          - type: filter
            condition: "salary_min > 0 AND experience_years >= 0"
          - type: deduplicate
            key: [id]
        quality:
          completeness: 0.95
          uniqueness: [id]
        target:
          layer: silver

      job_analytics:
        source: raw_jobs
        depends_on: [clean_jobs]
        transforms:
          - type: filter
            condition: "salary_min > 0"
        target:
          layer: gold

      ingest_candidates:
        source: raw_candidates
        transforms:
          - type: filter
            condition: "status = 'active'"
          - type: deduplicate
            key: [email]
        quality:
          completeness: 0.90
          uniqueness: [email]
        target:
          layer: bronze

      clean_candidates:
        source: raw_candidates
        depends_on: [ingest_candidates]
        transforms:
          - type: filter
            condition: "desired_salary > 0 AND experience_years >= 0"
          - type: deduplicate
            key: [email]
        quality:
          completeness: 0.95
          uniqueness: [email]
        target:
          layer: silver

  ml:
    tracker: builtin
    experiments:
      salary_predictor:
        model_type: sklearn
        target: salary_max
        features: [experience_years, desired_salary]
        params:
          n_estimators: 100
          max_depth: 5
    drift:
      monitor: [experience_years, desired_salary]
      method: psi
      threshold: 0.2

  ai:
    llm:
      provider: ollama
      model: ${LLM_MODEL:-qwen3:8b}
    retrieval:
      strategy: hybrid
      top_k: 10
      reranker: true
    vectorstore:
      backend: builtin
      embedding_model: all-MiniLM-L6-v2
    collections:
      career_docs:
        chunk_size: 512
        chunk_overlap: 50
    agents:
      career_advisor:
        system_prompt: "You are an expert career advisor. Help users find jobs, prepare for interviews, and advance their careers using the data available in the CareerDEX system."
        tools: [query, pipeline_status]
        max_iterations: 10
      job_matcher:
        system_prompt: "You are a job matching specialist. Analyze candidate profiles and job requirements to find the best matches. Use the available pipeline and data tools to query the CareerDEX data."
        tools: [query, pipeline_status]
        max_iterations: 8

  server:
    host: "0.0.0.0"
    port: 17003
    auth:
      enabled: false

  observability:
    metrics: true
    tracing: false
    log_level: INFO
  ```

- [ ] **3.7 — Commit**

  ```bash
  cd /home/jay/workspace/DataEngineX/careerdex
  git add careerdex.yaml data/jobs.csv data/candidates.csv data/skills.csv data/companies.csv
  git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" \
    -m "feat: careerdex example — careerdex.yaml full-stack config + CSV data files for jobs, candidates, skills, companies"
  ```

---

## Task 4: Smoke Test + Validation

**Requires:** Task 1 committed, Task 3 committed, dex installed in careerdex env.

- [ ] **4.1 — Full validation on dex and dex-studio**

  ```bash
  cd /home/jay/workspace/DataEngineX/dex && uv run poe lint && uv run poe typecheck && uv run poe test
  cd /home/jay/workspace/DataEngineX/dex-studio && uv run poe lint && uv run poe typecheck
  ```

  Expected: exit 0 on all.

- [ ] **4.2 — Validate careerdex config**

  ```bash
  cd /home/jay/workspace/DataEngineX/careerdex
  dex validate careerdex.yaml
  ```

  Expected: `careerdex.yaml is valid`.

- [ ] **4.3 — Start server and health check**

  ```bash
  cd /home/jay/workspace/DataEngineX/careerdex
  dex serve --config careerdex.yaml &
  sleep 3
  curl -s http://localhost:17003/api/v1/health | python3 -m json.tool
  ```

  Expected: `{"status": "alive"}`. LLM 503 in logs is acceptable — server must start.

- [ ] **4.4 — Verify all 4 sources**

  ```bash
  curl -s http://localhost:17003/api/v1/data/sources | python3 -m json.tool
  ```

  Expected: 4 sources with `type: csv`, not "—".

- [ ] **4.5 — Run ingest_jobs and verify lakehouse + lineage**

  ```bash
  curl -s -X POST http://localhost:17003/api/v1/pipelines/ingest_jobs/run | python3 -m json.tool
  # Expected: success: true, rows_input: 20, rows_output: 18

  curl -s http://localhost:17003/api/v1/data/warehouse/layers | python3 -m json.tool
  # Expected: bronze layer table_count: 1 (Bug 1 fixed)

  curl -s http://localhost:17003/api/v1/data/lineage | python3 -m json.tool
  # Expected: count: 2, events with event_id, layer, source, destination (Bug 2 fixed)

  curl -s http://localhost:17003/api/v1/pipelines/ingest_jobs/runs | python3 -m json.tool
  # Expected: count: 1 with run_id, timestamp, success: true
  ```

- [ ] **4.6 — Run all 5 pipelines and verify full medallion stack**

  ```bash
  curl -s -X POST http://localhost:17003/api/v1/pipelines/ingest_candidates/run | python3 -m json.tool
  curl -s -X POST http://localhost:17003/api/v1/pipelines/clean_jobs/run | python3 -m json.tool
  curl -s -X POST http://localhost:17003/api/v1/pipelines/clean_candidates/run | python3 -m json.tool
  curl -s -X POST http://localhost:17003/api/v1/pipelines/job_analytics/run | python3 -m json.tool

  curl -s http://localhost:17003/api/v1/data/warehouse/layers | python3 -m json.tool
  # Expected: bronze table_count: 2, silver table_count: 2, gold table_count: 1
  ```

- [ ] **4.7 — Stop server and create PRs**

  ```bash
  pkill -f "dex serve"

  # dex PR
  cd /home/jay/workspace/DataEngineX/dex
  git push --set-upstream origin feature/pipeline-run-history
  gh pr create --title "feat: pipeline run history + lakehouse path fix + lineage wiring" \
    --base dev --head feature/pipeline-run-history \
    --body "$(cat <<'EOF'
  ## Summary
  - Fixes lakehouse path mismatch (`.dex/data` → `.dex/lakehouse`) so warehouse shows data
  - Wires `PersistentLineage` into `PipelineRunner` so lineage events are recorded on every run
  - Adds `PipelineRunHistory` JSON-backed store + `GET /api/v1/pipelines/{name}/runs` endpoint

  ## Test plan
  - [ ] `uv run poe lint && uv run poe typecheck && uv run poe test` passes
  - [ ] `dex serve --config careerdex/careerdex.yaml` starts successfully
  - [ ] POST pipeline run → warehouse layers show data
  - [ ] GET lineage → events present with event_id, layer, source, destination
  - [ ] GET pipeline runs → run history with run_id, timestamp, success
  EOF
  )"

  # dex-studio PR
  cd /home/jay/workspace/DataEngineX/dex-studio
  git push --set-upstream origin feature/studio-pipeline-history
  gh pr create --title "fix: lineage/sources field names; feat: pipeline run history UI + 503 guide" \
    --base dev --head feature/studio-pipeline-history \
    --body "$(cat <<'EOF'
  ## Summary
  - Fixes sources page: `connector_type` → `type` (sources always showed "—")
  - Fixes lineage page: `id`→`event_id`, `target`→`destination`, adds `layer` column
  - Adds pipeline run history expandable section per pipeline
  - Shows Ollama setup guide when agent chat returns 503

  ## Test plan
  - [ ] `uv run poe lint && uv run poe typecheck` passes
  - [ ] Sources page shows connector type column populated
  - [ ] Lineage page shows event IDs, layer, source, destination
  - [ ] Pipelines page shows "Recent Runs" section with expandable history
  - [ ] Agent chat 503 → shows "ollama serve / ollama pull" guide
  EOF
  )"

  # careerdex PR
  cd /home/jay/workspace/DataEngineX/careerdex
  git push --set-upstream origin feature/careerdex-example
  gh pr create --title "feat: careerdex example — CSV data + full-stack careerdex.yaml config" \
    --base dev --head feature/careerdex-example \
    --body "$(cat <<'EOF'
  ## Summary
  - Adds careerdex.yaml demonstrating all DataEngineX features: 4 CSV sources, 5 pipelines (bronze→silver→gold), ML experiment, 2 AI agents, port 17003
  - Adds data/jobs.csv (20 rows), data/candidates.csv (15 rows), data/skills.csv (12 rows), data/companies.csv (8 rows)

  ## Starting the server
  ```bash
  dex serve --config careerdex.yaml
  # Then in DEX Studio: add project at http://localhost:17003
  ```

  ## Test plan
  - [ ] `dex validate careerdex.yaml` passes
  - [ ] All 5 pipelines run successfully
  - [ ] Warehouse shows bronze (2), silver (2), gold (1) tables
  - [ ] Lineage events recorded for all runs
  EOF
  )"
  ```

---

## Known Limitations / Follow-up

**`type: sql` transform not registered** — `job_analytics` uses `filter` passthrough instead of aggregation SQL. To add real analytics, implement `SqlTransform` in `dex/src/dataenginex/data/transforms/sql.py` and register as `@transform_registry.decorator("sql")`.

**`ingest_candidates` filter** — `status = 'active'` excludes K012 and K015 (inactive). `clean_candidates` filter `desired_salary > 0` additionally excludes K015. 13 candidates reach silver.

**ML experiments need manual trigger** — The `salary_predictor` experiment is configured but training runs require calling `POST /api/v1/ml/experiments/salary_predictor` and a separate training step. The config only defines the experiment; no auto-training on startup.

**AI agents require Ollama** — Server starts without Ollama (LLM graceful degradation), but agent chat returns 503. DEX Studio now shows the setup guide in this case.
