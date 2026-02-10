"""Gateway commands — status, info, backup, restore, modules, logs."""

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

app = typer.Typer(name="gateway", help="Gateway status, backups, modules, and logs.")
console = Console()


_STATUS_KEYS = ("state", "version", "edition", "deploymentMode")


@app.command()
@error_handler
def status(
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
    fmt: FormatOpt = "table",
) -> None:
    """Show concise gateway status (state, version, edition, mode)."""
    with make_client(gateway, url, token) as client:
        data = client.get_json("/gateway-info")
        summary = {k: data.get(k) for k in _STATUS_KEYS if data.get(k) is not None}
        output(summary or data, fmt, kv=True, title="Gateway Status")


@app.command()
@error_handler
def info(
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
    fmt: FormatOpt = "table",
) -> None:
    """Show gateway version, edition, and OS details."""
    with make_client(gateway, url, token) as client:
        data = client.get_json("/gateway-info")
        output(data, fmt, kv=True, title="Gateway Info")


@app.command()
@error_handler
def backup(
    output_file: Annotated[
        str | None,
        typer.Option("--output", "-o", help="Output file path"),
    ] = None,
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
) -> None:
    """Download a gateway backup (.gwbk)."""
    from pathlib import Path

    dest = Path(output_file) if output_file else Path("gateway-backup.gwbk")
    with make_client(gateway, url, token) as client:
        size = client.stream_to_file("/backup", dest)
        console.print(f"[green]Backup saved to {dest}[/] ({size:,} bytes)")


@app.command()
@error_handler
def restore(
    file: Annotated[str, typer.Argument(help="Backup file path (.gwbk)")],
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
) -> None:
    """Restore a gateway backup."""
    from pathlib import Path

    backup_path = Path(file)
    if not backup_path.exists():
        console.print(f"[red]File not found: {file}[/]")
        raise typer.Exit(1)

    with make_client(gateway, url, token) as client:
        client.post(
            "/backup",
            content=backup_path.read_bytes(),
            headers={"Content-Type": "application/octet-stream"},
        )
        console.print("[green]Backup restore initiated.[/]")


@app.command()
@error_handler
def modules(
    quarantined: Annotated[
        bool,
        typer.Option(
            "--quarantined", "-q",
            help="Show quarantined modules instead",
        ),
    ] = False,
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
    fmt: FormatOpt = "table",
) -> None:
    """List installed gateway modules."""
    with make_client(gateway, url, token) as client:
        endpoint = "/modules/quarantined" if quarantined else "/modules/healthy"
        data = client.get_json(endpoint)
        items = extract_items(data, "modules")
        columns = ["Name", "ID", "Version", "State"]
        rows = [
            [
                m.get("name", ""),
                m.get("id", ""),
                m.get("version", ""),
                m.get("state", ""),
            ]
            for m in items
        ]
        title = "Quarantined Modules" if quarantined else "Installed Modules"
        output(data, fmt, columns=columns, rows=rows, title=title)


@app.command()
@error_handler
def logs(
    lines: Annotated[
        int,
        typer.Option("--lines", "-n", help="Number of log lines"),
    ] = 50,
    level: Annotated[
        str | None,
        typer.Option("--level", "-l", help="Minimum log level"),
    ] = None,
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
    fmt: FormatOpt = "table",
) -> None:
    """View gateway logs."""
    with make_client(gateway, url, token) as client:
        params: dict[str, str | int] = {"limit": lines}
        if level:
            params["level"] = level
        data = client.get_json("/logs", params=params)
        items = extract_items(data, "logs")
        columns = ["Timestamp", "Level", "Logger", "Message"]
        rows = [
            [
                e.get("timestamp", ""),
                e.get("level", ""),
                e.get("logger", ""),
                e.get("message", ""),
            ]
            for e in items
        ]
        output(data, fmt, columns=columns, rows=rows, title="Gateway Logs")


@app.command("log-download")
@error_handler
def log_download(
    output_file: Annotated[
        str | None,
        typer.Option("--output", "-o", help="Output file path"),
    ] = None,
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
) -> None:
    """Download the gateway log file."""
    from pathlib import Path

    dest = Path(output_file) if output_file else Path("gateway-logs.zip")
    with make_client(gateway, url, token) as client:
        size = client.stream_to_file("/logs/download", dest)
        console.print(f"[green]Logs downloaded to {dest}[/] ({size:,} bytes)")


@app.command()
@error_handler
def loggers(
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
    fmt: FormatOpt = "table",
) -> None:
    """List configured loggers and their levels."""
    with make_client(gateway, url, token) as client:
        data = client.get_json("/logs/loggers")
        items = extract_items(data, "loggers")
        columns = ["Name", "Level"]
        rows = [[lg.get("name", ""), lg.get("level", "")] for lg in items]
        output(data, fmt, columns=columns, rows=rows, title="Loggers")


@app.command("scan-projects")
@error_handler
def scan_projects(
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
) -> None:
    """Trigger the gateway to scan for project changes."""
    with make_client(gateway, url, token) as client:
        client.post("/scan/projects")
        console.print("[green]Project scan triggered.[/]")


@app.command("scan-config")
@error_handler
def scan_config(
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
) -> None:
    """Trigger the gateway to scan for configuration changes."""
    with make_client(gateway, url, token) as client:
        client.post("/scan/config")
        console.print("[green]Config scan triggered.[/]")


@app.command("entity-browse")
@error_handler
def entity_browse(
    path: Annotated[
        str | None,
        typer.Option("--path", "-p", help="Entity path to browse"),
    ] = None,
    depth: Annotated[int, typer.Option("--depth", "-d", help="Browse depth")] = 1,
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
    fmt: FormatOpt = "table",
) -> None:
    """Browse the gateway entity tree (configuration, health, metrics)."""
    with make_client(gateway, url, token) as client:
        params: dict[str, str | int] = {"depth": depth}
        if path:
            params["path"] = path
        data = client.get_json("/entity/browse", params=params)
        output(data, fmt, kv=isinstance(data, dict), title="Entity Browser")
