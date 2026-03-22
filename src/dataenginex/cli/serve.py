"""``dex serve`` — start the DEX API server.

Usage::

    dex serve --config dex.yaml --port 17000
"""

from __future__ import annotations

from pathlib import Path

import click
import structlog

logger = structlog.get_logger()


@click.command("serve")
@click.option(
    "--config",
    "config_path",
    default="dex.yaml",
    show_default=True,
    help="Path to dex.yaml config.",
)
@click.option("--host", default=None, help="Override server host.")
@click.option("--port", default=None, type=int, help="Override server port.")
@click.option("--reload", "do_reload", is_flag=True, help="Enable auto-reload.")
def serve(
    config_path: str,
    host: str | None,
    port: int | None,
    do_reload: bool,
) -> None:
    """Start the DEX API server."""
    import uvicorn

    from dataenginex.api.factory import create_app
    from dataenginex.config.loader import load_config

    config = load_config(Path(config_path))
    app = create_app(config)

    final_host = host or config.server.host
    final_port = port or config.server.port

    logger.info("starting server", host=final_host, port=final_port)
    uvicorn.run(app, host=final_host, port=final_port, reload=do_reload)
