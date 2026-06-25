# dataenginex.orchestration

Pipeline and job scheduling — cron-based scheduler, built-in triggers, and run management.

## Quick import

```python
from dataenginex.orchestration import Scheduler, ScheduledJob
```

______________________________________________________________________

## Scheduler

`dataenginex.orchestration.scheduler`

Cron-based pipeline scheduler built on `croniter`. Manages job registration, next-run calculation, and async execution dispatch.

::: dataenginex.orchestration.scheduler

**Key class:** `Scheduler`

```python
from dataenginex.orchestration.scheduler import Scheduler

scheduler = Scheduler(engine=engine)
scheduler.add_job(
    name="nightly_ingest",
    pipeline="ingest_events",
    cron="0 2 * * *",  # 02:00 UTC daily
)
scheduler.start()  # blocking; runs until KeyboardInterrupt
```

Schedules are also declarative via `dex.yaml`:

```yaml
schedules:
  nightly_ingest:
    pipeline: ingest_events
    cron: "0 2 * * *"
```

______________________________________________________________________

## Built-in Jobs

`dataenginex.orchestration.builtin`

Pre-built job types: `PipelineJob`, `SqlJob`, `PythonJob`. Use in `dex.yaml` or register programmatically.

::: dataenginex.orchestration.builtin

```python
from dataenginex.orchestration.builtin import PipelineJob

job = PipelineJob(pipeline="ingest_events")
scheduler.add_job("nightly", job, cron="0 2 * * *")
```
