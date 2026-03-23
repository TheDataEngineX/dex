"""`dex run` — execute data pipelines."""

from __future__ import annotations

from pathlib import Path

import click
import structlog
from rich.console import Console
from rich.table import Table

from dataenginex.config import load_config
from dataenginex.data.pipeline.runner import PipelineRunner

logger = structlog.get_logger()
console = Console()


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

    # Display results
    table = Table(title="Pipeline Results")
    table.add_column("Pipeline", style="cyan")
    table.add_column("Status")
    table.add_column("Rows In")
    table.add_column("Rows Out")
    table.add_column("Steps")

    all_ok = True
    for name, result in results.items():
        status = "[green]OK[/green]" if result.success else "[red]FAIL[/red]"
        if result.dry_run:
            status = "[yellow]DRY RUN[/yellow]"
        if not result.success:
            all_ok = False
        table.add_row(
            name,
            status,
            str(result.rows_input),
            str(result.rows_output),
            str(result.steps_completed),
        )

    console.print(table)

    if not all_ok:
        raise SystemExit(1)
