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

app = typer.Typer(
    name="resource",
    help="Generic CRUD for gateway resources (use module/type format).",
)
console = Console()


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
    resource_type: Annotated[
        str,
        typer.Argument(
            help="Resource type (e.g. ignition/database-connection)"
        ),
    ],
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
    fmt: FormatOpt = "table",
) -> None:
    """List resources of a given type."""
    module, rtype = _validate_resource_type(resource_type)
    with make_client(gateway, url, token) as client:
        data = client.get_json(f"/resources/list/{module}/{rtype}")
        items = extract_items(data, "resources")
        columns = ["Name", "Type", "State"]
        rows = [
            [
                r.get("name", ""),
                r.get("type", resource_type),
                r.get("state", ""),
            ]
            for r in items
        ]
        output(
            data, fmt,
            columns=columns, rows=rows,
            title=f"Resources: {resource_type}",
        )


@app.command()
@error_handler
def show(
    resource_type: Annotated[
        str,
        typer.Argument(
            help="Resource type (e.g. ignition/database-connection)"
        ),
    ],
    name: Annotated[str, typer.Argument(help="Resource name")],
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
    fmt: FormatOpt = "table",
) -> None:
    """Show resource configuration."""
    module, rtype = _validate_resource_type(resource_type)
    with make_client(gateway, url, token) as client:
        data = client.get_json(f"/resources/find/{module}/{rtype}/{name}")
        # Format files/data list for readability in table mode
        if fmt == "table" and isinstance(data, dict):
            for key in ("files", "data"):
                if key in data and isinstance(data[key], list):
                    items = data[key]
                    data = {**data, key: ", ".join(items) if items else "(none)"}
        output(data, fmt, kv=True, title=f"{resource_type}/{name}")


@app.command()
@error_handler
def create(
    resource_type: Annotated[
        str,
        typer.Argument(
            help="Resource type (e.g. ignition/database-connection)"
        ),
    ],
    name: Annotated[
        str,
        typer.Option("--name", "-n", help="Resource name"),
    ],
    config: Annotated[
        str | None,
        typer.Option(
            "--config", "-c",
            help="JSON config string or @file path",
        ),
    ] = None,
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
) -> None:
    """Create a new resource."""
    module, rtype = _validate_resource_type(resource_type)
    body = _parse_config(config, name)
    with make_client(gateway, url, token) as client:
        client.post(f"/resources/{module}/{rtype}", json=[body])
        console.print(f"[green]Resource '{name}' ({resource_type}) created.[/]")


@app.command()
@error_handler
def update(
    resource_type: Annotated[
        str,
        typer.Argument(
            help="Resource type (e.g. ignition/database-connection)"
        ),
    ],
    name: Annotated[str, typer.Argument(help="Resource name")],
    config: Annotated[
        str,
        typer.Option(
            "--config", "-c",
            help="JSON config string or @file path",
        ),
    ],
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
) -> None:
    """Update an existing resource."""
    module, rtype = _validate_resource_type(resource_type)
    body = _parse_config(config, name)
    with make_client(gateway, url, token) as client:
        # Auto-fetch signature if not provided in config
        if "signature" not in body:
            data = client.get_json(f"/resources/find/{module}/{rtype}/{name}")
            sig = data.get("signature")
            if not sig:
                console.print(
                    f"[red]No signature found on resource '{name}'. "
                    "Include 'signature' in config.[/]"
                )
                raise typer.Exit(1)
            body["signature"] = sig
        client.put(f"/resources/{module}/{rtype}", json=[body])
        console.print(f"[green]Resource '{name}' ({resource_type}) updated.[/]")


@app.command()
@error_handler
def delete(
    resource_type: Annotated[
        str,
        typer.Argument(
            help="Resource type (e.g. ignition/database-connection)"
        ),
    ],
    name: Annotated[str, typer.Argument(help="Resource name")],
    force: Annotated[
        bool,
        typer.Option("--force", help="Skip confirmation"),
    ] = False,
    signature: Annotated[
        str | None,
        typer.Option(
            "--signature", "-s",
            help="Resource signature (auto-fetched if omitted)",
        ),
    ] = None,
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
) -> None:
    """Delete a resource."""
    if not force:
        from rich.prompt import Confirm

        if not Confirm.ask(f"Delete {resource_type}/{name}?"):
            console.print("Cancelled.")
            return
    module, rtype = _validate_resource_type(resource_type)
    with make_client(gateway, url, token) as client:
        if not signature:
            data = client.get_json(f"/resources/find/{module}/{rtype}/{name}")
            signature = data.get("signature")
            if not signature:
                console.print(
                    f"[red]No signature found on resource '{name}'. "
                    "Provide one with --signature.[/]"
                )
                raise typer.Exit(1)
        client.delete(f"/resources/{module}/{rtype}/{name}/{signature}")
        console.print(f"[green]Resource '{name}' ({resource_type}) deleted.[/]")


@app.command()
@error_handler
def names(
    resource_type: Annotated[
        str,
        typer.Argument(
            help="Resource type (e.g. ignition/database-connection)"
        ),
    ],
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
    fmt: FormatOpt = "table",
) -> None:
    """List resource names for a given type."""
    module, rtype = _validate_resource_type(resource_type)
    with make_client(gateway, url, token) as client:
        data = client.get_json(f"/resources/names/{module}/{rtype}")
        items = extract_items(data, "names")
        output(items, fmt, title=f"Resource Names: {resource_type}")


@app.command()
@error_handler
def upload(
    resource_type: Annotated[
        str,
        typer.Argument(
            help="Resource type"
            " (e.g. com.inductiveautomation.perspective/themes)"
        ),
    ],
    name: Annotated[str, typer.Argument(help="Resource name")],
    file_path: Annotated[Path, typer.Argument(help="Local file to upload")],
    signature: Annotated[str | None, typer.Option(
        "--signature", "-s", help="Resource signature (auto-fetched if omitted)",
    )] = None,
    filename: Annotated[str | None, typer.Option(
        "--filename", help="Remote filename (defaults to local basename)",
    )] = None,
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
) -> None:
    """Upload a binary datafile to a resource."""
    if not file_path.exists():
        console.print(f"[red]File not found: {file_path}[/]")
        raise typer.Exit(1)
    module, rtype = _validate_resource_type(resource_type)
    remote_name = filename or file_path.name
    with make_client(gateway, url, token) as client:
        if not signature:
            # Auto-fetch signature from resource metadata
            data = client.get_json(
                f"/resources/find/{module}/{rtype}/{name}",
            )
            signature = data.get("signature")
            if not signature:
                console.print(
                    f"[red]No signature found on resource "
                    f"'{name}'. Provide one with --signature.[/]"
                )
                raise typer.Exit(1)
        path = f"/resources/datafile/{module}/{rtype}/{name}/{remote_name}"
        client.put(
            path,
            content=file_path.read_bytes(),
            params={"signature": signature},
        )
        console.print(f"[green]Uploaded '{remote_name}' to {resource_type}/{name}.[/]")


@app.command()
@error_handler
def download(
    resource_type: Annotated[
        str,
        typer.Argument(
            help="Resource type"
            " (e.g. com.inductiveautomation.perspective/themes)"
        ),
    ],
    name: Annotated[str, typer.Argument(help="Resource name")],
    filename: Annotated[str, typer.Argument(help="Remote filename to download")],
    output_path: Annotated[Path | None, typer.Option(
        "--output", "-o", help="Output file path",
    )] = None,
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
) -> None:
    """Download a binary datafile from a resource."""
    module, rtype = _validate_resource_type(resource_type)
    dest = output_path or Path(filename)
    with make_client(gateway, url, token) as client:
        path = f"/resources/datafile/{module}/{rtype}/{name}/{filename}"
        resp = client.get(path)
        dest.write_bytes(resp.content)
        size = len(resp.content)
        console.print(
            f"[green]Downloaded '{filename}' to {dest}"
            f" ({size:,} bytes).[/]"
        )


@app.command()
@error_handler
def types(
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
) -> None:
    """List available resource types from the OpenAPI spec."""
    with make_client(gateway, url, token) as client:
        spec = client.get_openapi_spec()
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
            raise typer.Exit(1) from None
    data.setdefault("name", name)
    return data
