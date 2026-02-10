"""Gateway commands — status, info, backup, restore, modules, logs."""

from __future__ import annotations

from typing import Annotated, Optional

import typer
from rich.console import Console

from ignition_cli.client.errors import error_handler
from ignition_cli.client.gateway import GatewayClient
from ignition_cli.config.manager import ConfigManager
from ignition_cli.output.formatter import output

app = typer.Typer(name="gateway", help="Gateway status, backups, modules, and logs.")
console = Console()


def _client(gateway: str | None, url: str | None, token: str | None) -> GatewayClient:
    mgr = ConfigManager()
    profile = mgr.resolve_gateway(profile_name=gateway, url=url, token=token)
    return GatewayClient(profile)


@app.command()
@error_handler
def status(
    gateway: Annotated[Optional[str], typer.Option("--gateway", "-g", help="Gateway profile")] = None,
    url: Annotated[Optional[str], typer.Option("--url", help="Gateway URL override")] = None,
    token: Annotated[Optional[str], typer.Option("--token", help="API token override")] = None,
    fmt: Annotated[str, typer.Option("--format", "-f", help="Output format")] = "table",
) -> None:
    """Show gateway status and system info."""
    with _client(gateway, url, token) as client:
        data = client.get_json("/gateway-info")
        output(data, fmt, kv=True, title="Gateway Status")


@app.command()
@error_handler
def info(
    gateway: Annotated[Optional[str], typer.Option("--gateway", "-g", help="Gateway profile")] = None,
    url: Annotated[Optional[str], typer.Option("--url", help="Gateway URL override")] = None,
    token: Annotated[Optional[str], typer.Option("--token", help="API token override")] = None,
    fmt: Annotated[str, typer.Option("--format", "-f", help="Output format")] = "table",
) -> None:
    """Show gateway version, edition, and OS details."""
    with _client(gateway, url, token) as client:
        data = client.get_json("/gateway-info")
        output(data, fmt, kv=True, title="Gateway Info")


@app.command()
@error_handler
def backup(
    output_file: Annotated[Optional[str], typer.Option("--output", "-o", help="Output file path")] = None,
    gateway: Annotated[Optional[str], typer.Option("--gateway", "-g", help="Gateway profile")] = None,
    url: Annotated[Optional[str], typer.Option("--url", help="Gateway URL override")] = None,
    token: Annotated[Optional[str], typer.Option("--token", help="API token override")] = None,
) -> None:
    """Download a gateway backup (.gwbk)."""
    from pathlib import Path

    with _client(gateway, url, token) as client:
        resp = client.get("/backup")
        dest = Path(output_file) if output_file else Path("gateway-backup.gwbk")
        dest.write_bytes(resp.content)
        console.print(f"[green]Backup saved to {dest}[/] ({len(resp.content):,} bytes)")


@app.command()
@error_handler
def restore(
    file: Annotated[str, typer.Argument(help="Backup file path (.gwbk)")],
    gateway: Annotated[Optional[str], typer.Option("--gateway", "-g", help="Gateway profile")] = None,
    url: Annotated[Optional[str], typer.Option("--url", help="Gateway URL override")] = None,
    token: Annotated[Optional[str], typer.Option("--token", help="API token override")] = None,
) -> None:
    """Restore a gateway backup."""
    from pathlib import Path

    backup_path = Path(file)
    if not backup_path.exists():
        console.print(f"[red]File not found: {file}[/]")
        raise typer.Exit(1)

    with _client(gateway, url, token) as client:
        client.post("/backup", content=backup_path.read_bytes())
        console.print("[green]Backup restore initiated.[/]")


@app.command()
@error_handler
def modules(
    quarantined: Annotated[bool, typer.Option("--quarantined", "-q", help="Show quarantined modules instead")] = False,
    gateway: Annotated[Optional[str], typer.Option("--gateway", "-g", help="Gateway profile")] = None,
    url: Annotated[Optional[str], typer.Option("--url", help="Gateway URL override")] = None,
    token: Annotated[Optional[str], typer.Option("--token", help="API token override")] = None,
    fmt: Annotated[str, typer.Option("--format", "-f", help="Output format")] = "table",
) -> None:
    """List installed gateway modules."""
    with _client(gateway, url, token) as client:
        endpoint = "/modules/quarantined" if quarantined else "/modules/healthy"
        data = client.get_json(endpoint)
        items = data if isinstance(data, list) else data.get("modules", data.get("items", []))
        columns = ["Name", "ID", "Version", "State"]
        rows = [[m.get("name", ""), m.get("id", ""), m.get("version", ""), m.get("state", "")] for m in items]
        title = "Quarantined Modules" if quarantined else "Installed Modules"
        output(data, fmt, columns=columns, rows=rows, title=title)


@app.command()
@error_handler
def logs(
    lines: Annotated[int, typer.Option("--lines", "-n", help="Number of log lines")] = 50,
    level: Annotated[Optional[str], typer.Option("--level", "-l", help="Minimum log level")] = None,
    gateway: Annotated[Optional[str], typer.Option("--gateway", "-g", help="Gateway profile")] = None,
    url: Annotated[Optional[str], typer.Option("--url", help="Gateway URL override")] = None,
    token: Annotated[Optional[str], typer.Option("--token", help="API token override")] = None,
    fmt: Annotated[str, typer.Option("--format", "-f", help="Output format")] = "table",
) -> None:
    """View gateway logs."""
    with _client(gateway, url, token) as client:
        params: dict[str, str | int] = {"limit": lines}
        if level:
            params["level"] = level
        data = client.get_json("/logs", params=params)
        items = data if isinstance(data, list) else data.get("logs", data.get("items", []))
        columns = ["Timestamp", "Level", "Logger", "Message"]
        rows = [
            [e.get("timestamp", ""), e.get("level", ""), e.get("logger", ""), e.get("message", "")]
            for e in items
        ]
        output(data, fmt, columns=columns, rows=rows, title="Gateway Logs")
