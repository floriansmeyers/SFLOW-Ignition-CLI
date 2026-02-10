"""Resource commands — generic CRUD for any resource type.

Resource types use the format ``module/type``, for example:
  - ``ignition/database-connection``
  - ``com.inductiveautomation.opcua/device``
  - ``ignition/tag-provider``

Use ``resource types`` to discover available resource types from the OpenAPI spec.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console

from ignition_cli.client.errors import error_handler
from ignition_cli.client.gateway import GatewayClient
from ignition_cli.config.manager import ConfigManager
from ignition_cli.output.formatter import output

app = typer.Typer(name="resource", help="Generic CRUD for gateway resources (use module/type format).")
console = Console()


def _client(gateway: str | None, url: str | None, token: str | None) -> GatewayClient:
    mgr = ConfigManager()
    profile = mgr.resolve_gateway(profile_name=gateway, url=url, token=token)
    return GatewayClient(profile)


def _validate_resource_type(resource_type: str) -> tuple[str, str]:
    """Validate and split resource_type into (module, type)."""
    if "/" not in resource_type:
        console.print(
            f"[red]Invalid resource type '{resource_type}'. "
            "Use module/type format (e.g. ignition/database-connection).[/]"
        )
        raise typer.Exit(1)
    parts = resource_type.split("/", 1)
    return parts[0], parts[1]


@app.command("list")
@error_handler
def list_resources(
    resource_type: Annotated[str, typer.Argument(help="Resource type (e.g. ignition/database-connection)")],
    gateway: Annotated[Optional[str], typer.Option("--gateway", "-g")] = None,
    url: Annotated[Optional[str], typer.Option("--url")] = None,
    token: Annotated[Optional[str], typer.Option("--token")] = None,
    fmt: Annotated[str, typer.Option("--format", "-f")] = "table",
) -> None:
    """List resources of a given type."""
    module, rtype = _validate_resource_type(resource_type)
    with _client(gateway, url, token) as client:
        data = client.get_json(f"/resources/list/{module}/{rtype}")
        items = data if isinstance(data, list) else data.get("resources", data.get("items", []))
        columns = ["Name", "Type", "State"]
        rows = [[r.get("name", ""), r.get("type", resource_type), r.get("state", "")] for r in items]
        output(data, fmt, columns=columns, rows=rows, title=f"Resources: {resource_type}")


@app.command()
@error_handler
def show(
    resource_type: Annotated[str, typer.Argument(help="Resource type (e.g. ignition/database-connection)")],
    name: Annotated[str, typer.Argument(help="Resource name")],
    gateway: Annotated[Optional[str], typer.Option("--gateway", "-g")] = None,
    url: Annotated[Optional[str], typer.Option("--url")] = None,
    token: Annotated[Optional[str], typer.Option("--token")] = None,
    fmt: Annotated[str, typer.Option("--format", "-f")] = "table",
) -> None:
    """Show resource configuration."""
    module, rtype = _validate_resource_type(resource_type)
    with _client(gateway, url, token) as client:
        data = client.get_json(f"/resources/find/{module}/{rtype}/{name}")
        output(data, fmt, kv=True, title=f"{resource_type}/{name}")


@app.command()
@error_handler
def create(
    resource_type: Annotated[str, typer.Argument(help="Resource type (e.g. ignition/database-connection)")],
    name: Annotated[str, typer.Option("--name", "-n", help="Resource name")],
    config: Annotated[Optional[str], typer.Option("--config", "-c", help="JSON config string or @file path")] = None,
    gateway: Annotated[Optional[str], typer.Option("--gateway", "-g")] = None,
    url: Annotated[Optional[str], typer.Option("--url")] = None,
    token: Annotated[Optional[str], typer.Option("--token")] = None,
) -> None:
    """Create a new resource."""
    module, rtype = _validate_resource_type(resource_type)
    body = _parse_config(config, name)
    with _client(gateway, url, token) as client:
        client.post(f"/resources/{module}/{rtype}", json=body)
        console.print(f"[green]Resource '{name}' ({resource_type}) created.[/]")


@app.command()
@error_handler
def update(
    resource_type: Annotated[str, typer.Argument(help="Resource type (e.g. ignition/database-connection)")],
    name: Annotated[str, typer.Argument(help="Resource name")],
    config: Annotated[str, typer.Option("--config", "-c", help="JSON config string or @file path")],
    gateway: Annotated[Optional[str], typer.Option("--gateway", "-g")] = None,
    url: Annotated[Optional[str], typer.Option("--url")] = None,
    token: Annotated[Optional[str], typer.Option("--token")] = None,
) -> None:
    """Update an existing resource."""
    module, rtype = _validate_resource_type(resource_type)
    body = _parse_config(config, name)
    with _client(gateway, url, token) as client:
        client.put(f"/resources/{module}/{rtype}", json=body)
        console.print(f"[green]Resource '{name}' ({resource_type}) updated.[/]")


@app.command()
@error_handler
def delete(
    resource_type: Annotated[str, typer.Argument(help="Resource type (e.g. ignition/database-connection)")],
    name: Annotated[str, typer.Argument(help="Resource name")],
    force: Annotated[bool, typer.Option("--force", help="Skip confirmation")] = False,
    gateway: Annotated[Optional[str], typer.Option("--gateway", "-g")] = None,
    url: Annotated[Optional[str], typer.Option("--url")] = None,
    token: Annotated[Optional[str], typer.Option("--token")] = None,
) -> None:
    """Delete a resource."""
    if not force:
        from rich.prompt import Confirm

        if not Confirm.ask(f"Delete {resource_type}/{name}?"):
            console.print("Cancelled.")
            return
    module, rtype = _validate_resource_type(resource_type)
    with _client(gateway, url, token) as client:
        client.post(f"/resources/delete/{module}/{rtype}", json=[name])
        console.print(f"[green]Resource '{name}' ({resource_type}) deleted.[/]")


@app.command()
@error_handler
def names(
    resource_type: Annotated[str, typer.Argument(help="Resource type (e.g. ignition/database-connection)")],
    gateway: Annotated[Optional[str], typer.Option("--gateway", "-g")] = None,
    url: Annotated[Optional[str], typer.Option("--url")] = None,
    token: Annotated[Optional[str], typer.Option("--token")] = None,
    fmt: Annotated[str, typer.Option("--format", "-f")] = "table",
) -> None:
    """List resource names for a given type."""
    module, rtype = _validate_resource_type(resource_type)
    with _client(gateway, url, token) as client:
        data = client.get_json(f"/resources/names/{module}/{rtype}")
        items = data if isinstance(data, list) else data.get("names", data.get("items", []))
        output(items, fmt, title=f"Resource Names: {resource_type}")


@app.command()
@error_handler
def types(
    gateway: Annotated[Optional[str], typer.Option("--gateway", "-g")] = None,
    url: Annotated[Optional[str], typer.Option("--url")] = None,
    token: Annotated[Optional[str], typer.Option("--token")] = None,
) -> None:
    """List available resource types from the OpenAPI spec."""
    import httpx

    mgr = ConfigManager()
    profile = mgr.resolve_gateway(profile_name=gateway, url=url, token=token)
    resp = httpx.get(
        f"{profile.url}/openapi.json",
        verify=profile.verify_ssl,
        timeout=profile.timeout,
    )
    spec = resp.json()
    paths = spec.get("paths", {})

    resource_types: set[str] = set()
    prefix = "/data/api/v1/resources/list/"
    for path_str in paths:
        if prefix in path_str:
            remainder = path_str.split(prefix, 1)[-1]
            # remainder is like "ignition/database-connection"
            parts = remainder.split("/")
            if len(parts) >= 2 and not parts[0].startswith("{"):
                resource_types.add(f"{parts[0]}/{parts[1]}")

    if resource_types:
        from ignition_cli.output.tables import make_table

        rows = [[t] for t in sorted(resource_types)]
        console.print(make_table("Resource Types", ["Module/Type"], rows))
    else:
        console.print("[yellow]No resource types found in OpenAPI spec.[/]")


def _parse_config(config: str | None, name: str) -> dict:
    """Parse config from JSON string or @file reference."""
    if not config:
        return {"name": name}
    if config.startswith("@"):
        file_path = Path(config[1:])
        if not file_path.exists():
            console.print(f"[red]Config file not found: {file_path}[/]")
            raise typer.Exit(1)
        data = json.loads(file_path.read_text())
    else:
        try:
            data = json.loads(config)
        except json.JSONDecodeError:
            console.print("[red]Invalid JSON config.[/]")
            raise typer.Exit(1)
    data.setdefault("name", name)
    return data
