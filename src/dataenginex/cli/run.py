"""`dex run` — execute data pipelines."""

from __future__ import annotations

from pathlib import Path

import click
import structlog

from dataenginex.config import load_config
from dataenginex.data.pipeline.runner import PipelineRunner

logger = structlog.get_logger()

_COLS = (24, 10, 10, 10, 8)
_HDR = ("Pipeline", "Status", "Rows In", "Rows Out", "Steps")


@click.command()
@click.argument("pipeline", required=False)
@click.option("--all", "run_all", is_flag=True, help="Run all pipelines in dependency order")
@click.option("--config", "config_path", default="dex.yaml", help="Config file path")
@click.option("--data-dir", default=None, help="Data directory for lakehouse layers")
@click.option("--dry-run", is_flag=True, help="Validate without executing")
def run(
    pipeline: str | None,
    run_all: bool,
    config_path: str,
    data_dir: str | None,
    dry_run: bool,
) -> None:
    """Run data pipelines defined in dex.yaml."""
    config = load_config(Path(config_path))
    runner = PipelineRunner(
        config,
        data_dir=Path(data_dir) if data_dir else None,
    )

    if run_all:
        results = runner.run_all()
    elif pipeline:
        results = {pipeline: runner.run(pipeline, dry_run=dry_run)}
    else:
        raise click.UsageError("Specify a pipeline name or use --all")

    click.echo("\nPipeline Results")
    click.echo("  ".join(h.ljust(w) for h, w in zip(_HDR, _COLS, strict=True)))
    click.echo("-" * (sum(_COLS) + 2 * len(_COLS)))

    all_ok = True
    for name, result in results.items():
        if result.dry_run:
            status = "DRY RUN"
        elif result.success:
            status = "OK"
        else:
            status = "FAIL"
            all_ok = False
        row_vals = [
            name,
            status,
            str(result.rows_input),
            str(result.rows_output),
            str(result.steps_completed),
        ]
        click.echo("  ".join(v.ljust(w) for v, w in zip(row_vals, _COLS, strict=True)))

    if not all_ok:
        raise SystemExit(1)
