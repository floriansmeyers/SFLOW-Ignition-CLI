"""Root Typer app — global options and command group registration."""

from __future__ import annotations

from typing import Optional

import typer

from ignition_cli import __version__
from ignition_cli.commands import (
    api,
    config_cmd,
    device,
    gateway,
    modes,
    project,
    resource,
    tag,
)

app = typer.Typer(
    name="ignition-cli",
    help="CLI tool for Ignition SCADA 8.3+ REST API.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)


def version_callback(value: bool) -> None:
    if value:
        print(f"ignition-cli {__version__}")
        raise typer.Exit()


@app.callback()
def main_callback(
    version: Optional[bool] = typer.Option(
        None, "--version", "-V", callback=version_callback, is_eager=True, help="Show version and exit."
    ),
) -> None:
    """Ignition SCADA CLI — manage gateways, projects, tags, and more."""


# Register command groups
app.add_typer(config_cmd.app, name="config")
app.add_typer(gateway.app, name="gateway")
app.add_typer(project.app, name="project")
app.add_typer(tag.app, name="tag")
app.add_typer(device.app, name="device")
app.add_typer(resource.app, name="resource")
app.add_typer(modes.app, name="mode")
app.add_typer(api.app, name="api")


def main() -> None:
    app()
