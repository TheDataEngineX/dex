"""Entry point for the ``dex`` CLI.

Usage::

    dex --help
    dex validate dex.yaml
    dex version
"""

from __future__ import annotations

from pathlib import Path

import click
import structlog
from rich.console import Console
from rich.table import Table

from dataenginex.config.loader import load_config, validate_config
from dataenginex.core.exceptions import ConfigError

logger = structlog.get_logger()
console = Console()


@click.group()
@click.version_option(package_name="dataenginex")
def dex() -> None:
    """DataEngineX — unified Data + ML + AI framework."""


@dex.command()
@click.argument("config_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--overlay",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Overlay config file (e.g. dex.prod.yaml).",
)
def validate(config_path: Path, overlay: Path | None) -> None:
    """Validate a dex.yaml config file."""
    try:
        cfg = load_config(config_path, overlay=overlay)
    except ConfigError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise SystemExit(1) from exc

    issues = validate_config(cfg)
    warnings = [i for i in issues if i.startswith("Warning:")]
    hard_errors = [i for i in issues if not i.startswith("Warning:")]

    if warnings:
        console.print(f"[yellow]{len(warnings)} warning(s):[/yellow]")
        for w in warnings:
            console.print(f"  [yellow]![/yellow] {w}")

    if hard_errors:
        console.print(f"[red]{len(hard_errors)} error(s):[/red]")
        for err in hard_errors:
            console.print(f"  [red]✗[/red] {err}")
        raise SystemExit(1)

    # Summary table
    table = Table(title=f"Config: {cfg.project.name} v{cfg.project.version}")
    table.add_column("Section", style="cyan")
    table.add_column("Summary", style="green")

    table.add_row("Data Sources", str(len(cfg.data.sources)))
    table.add_row("Data Pipelines", str(len(cfg.data.pipelines)))
    table.add_row("ML Experiments", str(len(cfg.ml.experiments)))
    table.add_row("AI Agents", str(len(cfg.ai.agents)))
    table.add_row("AI Collections", str(len(cfg.ai.collections)))
    table.add_row("Server", f"{cfg.server.host}:{cfg.server.port}")

    console.print(table)
    console.print("[green]Config is valid.[/green]")


@dex.command()
def version() -> None:
    """Show DataEngineX version and environment info."""
    import importlib.metadata
    import platform
    import sys

    ver = importlib.metadata.version("dataenginex")
    console.print(f"[bold]DataEngineX[/bold] {ver}")
    console.print(f"Python {sys.version}")
    console.print(f"Platform {platform.platform()}")


from dataenginex.cli.run import run  # noqa: E402
from dataenginex.cli.serve import serve  # noqa: E402
from dataenginex.cli.train import train  # noqa: E402

dex.add_command(run)
dex.add_command(serve)
dex.add_command(train)

if __name__ == "__main__":
    dex()
