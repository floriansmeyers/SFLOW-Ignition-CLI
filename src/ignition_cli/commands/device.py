"""Device commands — list, show, status, restart.

Devices are managed through the Ignition resource API under the
com.inductiveautomation.opcua module.
"""

from __future__ import annotations

from typing import Annotated, Optional

import typer
from rich.console import Console

from ignition_cli.client.errors import error_handler
from ignition_cli.client.gateway import GatewayClient
from ignition_cli.config.manager import ConfigManager
from ignition_cli.output.formatter import output

app = typer.Typer(name="device", help="Manage device connections.")
console = Console()

# Ignition resource path for OPC-UA devices
_DEVICE_MODULE = "com.inductiveautomation.opcua"
_DEVICE_TYPE = "device"


def _client(gateway: str | None, url: str | None, token: str | None) -> GatewayClient:
    mgr = ConfigManager()
    profile = mgr.resolve_gateway(profile_name=gateway, url=url, token=token)
    return GatewayClient(profile)


@app.command("list")
@error_handler
def list_devices(
    status_filter: Annotated[Optional[str], typer.Option("--status", help="Filter by status")] = None,
    gateway: Annotated[Optional[str], typer.Option("--gateway", "-g")] = None,
    url: Annotated[Optional[str], typer.Option("--url")] = None,
    token: Annotated[Optional[str], typer.Option("--token")] = None,
    fmt: Annotated[str, typer.Option("--format", "-f")] = "table",
) -> None:
    """List device connections."""
    with _client(gateway, url, token) as client:
        data = client.get_json(f"/resources/list/{_DEVICE_MODULE}/{_DEVICE_TYPE}")
        items = data if isinstance(data, list) else data.get("resources", data.get("items", []))
        if status_filter:
            items = [d for d in items if status_filter.lower() in d.get("state", "").lower()]
        columns = ["Name", "Type", "Enabled", "State", "Hostname"]
        rows = [
            [
                d.get("name", ""),
                d.get("type", ""),
                str(d.get("enabled", "")),
                d.get("state", ""),
                d.get("hostname", ""),
            ]
            for d in items
        ]
        output(data, fmt, columns=columns, rows=rows, title="Device Connections")


@app.command()
@error_handler
def show(
    name: Annotated[str, typer.Argument(help="Device name")],
    gateway: Annotated[Optional[str], typer.Option("--gateway", "-g")] = None,
    url: Annotated[Optional[str], typer.Option("--url")] = None,
    token: Annotated[Optional[str], typer.Option("--token")] = None,
    fmt: Annotated[str, typer.Option("--format", "-f")] = "table",
) -> None:
    """Show device connection details."""
    with _client(gateway, url, token) as client:
        data = client.get_json(f"/resources/find/{_DEVICE_MODULE}/{_DEVICE_TYPE}/{name}")
        output(data, fmt, kv=True, title=f"Device: {name}")


@app.command()
@error_handler
def status(
    name: Annotated[str, typer.Argument(help="Device name")],
    gateway: Annotated[Optional[str], typer.Option("--gateway", "-g")] = None,
    url: Annotated[Optional[str], typer.Option("--url")] = None,
    token: Annotated[Optional[str], typer.Option("--token")] = None,
    fmt: Annotated[str, typer.Option("--format", "-f")] = "table",
) -> None:
    """Show device configuration (retrieved via resource find)."""
    with _client(gateway, url, token) as client:
        data = client.get_json(f"/resources/find/{_DEVICE_MODULE}/{_DEVICE_TYPE}/{name}")
        output(data, fmt, kv=True, title=f"Device Status: {name}")


@app.command()
@error_handler
def restart(
    name: Annotated[str, typer.Argument(help="Device name")],
    gateway: Annotated[Optional[str], typer.Option("--gateway", "-g")] = None,
    url: Annotated[Optional[str], typer.Option("--url")] = None,
    token: Annotated[Optional[str], typer.Option("--token")] = None,
) -> None:
    """Restart a device connection by toggling its enabled state."""
    console.print(
        "[yellow]Note: The Ignition REST API does not have a direct device restart endpoint. "
        "Use the gateway web UI or the 'resource update' command to toggle the device.[/]"
    )
