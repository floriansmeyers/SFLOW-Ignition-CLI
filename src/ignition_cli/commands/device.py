"""Device commands — list, show, status, restart.

Devices are managed through the Ignition resource API under the
com.inductiveautomation.opcua module.
"""

from __future__ import annotations

from typing import Annotated

import typer
from rich.console import Console

from ignition_cli.client.errors import error_handler
from ignition_cli.commands._common import (
    FormatOpt,
    GatewayOpt,
    TokenOpt,
    UrlOpt,
    extract_items,
    make_client,
)
from ignition_cli.output.formatter import output

app = typer.Typer(name="device", help="Manage device connections.")
console = Console()

# Ignition resource path for OPC-UA devices
_DEVICE_MODULE = "com.inductiveautomation.opcua"
_DEVICE_TYPE = "device"


@app.command("list")
@error_handler
def list_devices(
    status_filter: Annotated[
        str | None,
        typer.Option("--status", help="Filter by status"),
    ] = None,
    module: Annotated[
        str, typer.Option("--module", help="Resource module"),
    ] = _DEVICE_MODULE,
    device_type: Annotated[
        str, typer.Option("--type", help="Resource type"),
    ] = _DEVICE_TYPE,
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
    fmt: FormatOpt = "table",
) -> None:
    """List device connections."""
    with make_client(gateway, url, token) as client:
        data = client.get_json(f"/resources/list/{module}/{device_type}")
        items = extract_items(data, "resources")
        if status_filter:
            items = [
                d for d in items
                if status_filter.lower() in d.get("state", "").lower()
            ]
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
    module: Annotated[
        str, typer.Option("--module", help="Resource module"),
    ] = _DEVICE_MODULE,
    device_type: Annotated[
        str, typer.Option("--type", help="Resource type"),
    ] = _DEVICE_TYPE,
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
    fmt: FormatOpt = "table",
) -> None:
    """Show device connection details."""
    with make_client(gateway, url, token) as client:
        data = client.get_json(f"/resources/find/{module}/{device_type}/{name}")
        output(data, fmt, kv=True, title=f"Device: {name}")


@app.command(deprecated=True, hidden=True)
@error_handler
def status(
    name: Annotated[str, typer.Argument(help="Device name")],
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
    fmt: FormatOpt = "table",
) -> None:
    """Show device configuration (use 'device show' instead)."""
    show(name=name, gateway=gateway, url=url, token=token, fmt=fmt)


@app.command()
@error_handler
def restart(
    name: Annotated[str, typer.Argument(help="Device name")],
    module: Annotated[
        str, typer.Option("--module", help="Resource module"),
    ] = _DEVICE_MODULE,
    device_type: Annotated[
        str, typer.Option("--type", help="Resource type"),
    ] = _DEVICE_TYPE,
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
) -> None:
    """Restart a device connection by toggling its enabled state.

    Disables the device, then re-enables it, causing Ignition to
    re-establish the connection.
    """
    import time

    with make_client(gateway, url, token) as client:
        data = client.get_json(f"/resources/find/{module}/{device_type}/{name}")
        if not isinstance(data, dict):
            console.print(f"[red]Unexpected response for device '{name}'.[/]")
            raise typer.Exit(1)

        # Disable
        body = {**data, "enabled": False}
        client.put(f"/resources/{module}/{device_type}", json=body)
        console.print(f"[dim]Disabled '{name}'...[/]")
        time.sleep(1)

        # Re-enable
        body["enabled"] = True
        client.put(f"/resources/{module}/{device_type}", json=body)
        console.print(f"[green]Device '{name}' restarted (toggled enabled state).[/]")
