"""Tag commands — browse, read, write, export, import, providers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.tree import Tree

from ignition_cli.client.errors import error_handler
from ignition_cli.client.gateway import GatewayClient
from ignition_cli.config.manager import ConfigManager
from ignition_cli.output.formatter import output

app = typer.Typer(name="tag", help="Browse, read, write, and manage tags.")
console = Console()


def _client(gateway: str | None, url: str | None, token: str | None) -> GatewayClient:
    mgr = ConfigManager()
    profile = mgr.resolve_gateway(profile_name=gateway, url=url, token=token)
    return GatewayClient(profile)


def _build_tree(node_data: dict | list, tree: Tree, recursive: bool = False) -> None:
    """Build a Rich tree from tag browse data."""
    items = node_data if isinstance(node_data, list) else node_data.get("tags", node_data.get("items", []))
    for item in items:
        name = item.get("name", "?")
        tag_type = item.get("tagType", item.get("tag_type", ""))
        data_type = item.get("dataType", item.get("data_type", ""))
        label = f"[bold]{name}[/]"
        if tag_type == "Folder" or tag_type == "UdtInstance":
            label = f"[bold cyan]{name}/[/]"
        elif data_type:
            label = f"{name} [dim]({data_type})[/]"
        child = tree.add(label)
        if recursive and "tags" in item:
            _build_tree(item["tags"], child, recursive=True)


@app.command()
@error_handler
def browse(
    path: Annotated[Optional[str], typer.Argument(help="Tag path to browse")] = None,
    recursive: Annotated[bool, typer.Option("--recursive", "-r", help="Browse recursively")] = False,
    provider: Annotated[str, typer.Option("--provider", "-p", help="Tag provider")] = "default",
    gateway: Annotated[Optional[str], typer.Option("--gateway", "-g")] = None,
    url: Annotated[Optional[str], typer.Option("--url")] = None,
    token: Annotated[Optional[str], typer.Option("--token")] = None,
    fmt: Annotated[str, typer.Option("--format", "-f")] = "table",
) -> None:
    """Browse the tag tree.

    Note: Tag browsing is not part of the standard Ignition REST API.
    This uses the tag export endpoint to retrieve tag structure.
    """
    with _client(gateway, url, token) as client:
        params: dict[str, str] = {"provider": provider}
        if path:
            params["path"] = path
        if recursive:
            params["recursive"] = "true"
        data = client.get_json("/tags/export", params=params)

        if fmt != "table":
            output(data, fmt)
            return

        tree_title = f"[{provider}]" + (f"/{path}" if path else "")
        tree = Tree(f"[bold]{tree_title}[/]")
        _build_tree(data, tree, recursive=recursive)
        console.print(tree)


@app.command()
@error_handler
def read(
    paths: Annotated[list[str], typer.Argument(help="Tag paths to read")],
    provider: Annotated[str, typer.Option("--provider", "-p")] = "default",
    gateway: Annotated[Optional[str], typer.Option("--gateway", "-g")] = None,
    url: Annotated[Optional[str], typer.Option("--url")] = None,
    token: Annotated[Optional[str], typer.Option("--token")] = None,
    fmt: Annotated[str, typer.Option("--format", "-f")] = "table",
) -> None:
    """Read one or more tag values.

    Note: Tag reading is not part of the standard Ignition REST API.
    This requires a gateway with a WebDev endpoint or custom module providing this capability.
    """
    with _client(gateway, url, token) as client:
        data = client.post("/tags/read", json=paths, params={"provider": provider})
        items = data.json() if hasattr(data, "json") else data
        if not isinstance(items, list):
            items = items.get("values", items.get("items", [items]))

        if fmt != "table":
            output(items, fmt)
            return

        columns = ["Path", "Value", "Quality", "Timestamp"]
        rows = []
        for item in items:
            rows.append([
                item.get("path", ""),
                str(item.get("value", "")),
                item.get("quality", ""),
                item.get("timestamp", ""),
            ])
        output(items, fmt, columns=columns, rows=rows, title="Tag Values")


@app.command()
@error_handler
def write(
    path: Annotated[str, typer.Argument(help="Tag path")],
    value: Annotated[str, typer.Argument(help="Value to write")],
    provider: Annotated[str, typer.Option("--provider", "-p")] = "default",
    gateway: Annotated[Optional[str], typer.Option("--gateway", "-g")] = None,
    url: Annotated[Optional[str], typer.Option("--url")] = None,
    token: Annotated[Optional[str], typer.Option("--token")] = None,
) -> None:
    """Write a value to a tag.

    Note: Tag writing is not part of the standard Ignition REST API.
    This requires a gateway with a WebDev endpoint or custom module providing this capability.
    """
    # Try to parse as JSON for numeric/boolean values
    try:
        parsed = json.loads(value)
    except (json.JSONDecodeError, ValueError):
        parsed = value

    with _client(gateway, url, token) as client:
        client.post("/tags/write", json=[{"path": path, "value": parsed}], params={"provider": provider})
        console.print(f"[green]Wrote {parsed!r} to {path}[/]")


@app.command("export")
@error_handler
def export_tags(
    path: Annotated[Optional[str], typer.Argument(help="Tag path to export (root if omitted)")] = None,
    output_file: Annotated[Optional[str], typer.Option("--output", "-o", help="Output file")] = None,
    provider: Annotated[str, typer.Option("--provider", "-p")] = "default",
    gateway: Annotated[Optional[str], typer.Option("--gateway", "-g")] = None,
    url: Annotated[Optional[str], typer.Option("--url")] = None,
    token: Annotated[Optional[str], typer.Option("--token")] = None,
) -> None:
    """Export tag configuration as JSON."""
    with _client(gateway, url, token) as client:
        params: dict[str, str] = {"provider": provider}
        if path:
            params["path"] = path
        api_path = "/tags/export"
        data = client.get_json(api_path, params=params)

        if output_file:
            Path(output_file).write_text(json.dumps(data, indent=2))
            console.print(f"[green]Tags exported to {output_file}[/]")
        else:
            console.print_json(json.dumps(data, indent=2))


@app.command("import")
@error_handler
def import_tags(
    file: Annotated[str, typer.Argument(help="JSON file to import")],
    mode: Annotated[str, typer.Option("--mode", "-m", help="Import mode: merge or replace")] = "merge",
    provider: Annotated[str, typer.Option("--provider", "-p")] = "default",
    gateway: Annotated[Optional[str], typer.Option("--gateway", "-g")] = None,
    url: Annotated[Optional[str], typer.Option("--url")] = None,
    token: Annotated[Optional[str], typer.Option("--token")] = None,
) -> None:
    """Import tag configuration from a JSON file."""
    file_path = Path(file)
    if not file_path.exists():
        console.print(f"[red]File not found: {file}[/]")
        raise typer.Exit(1)

    tag_data = json.loads(file_path.read_text())
    with _client(gateway, url, token) as client:
        client.post("/tags/import", json=tag_data, params={"provider": provider, "mode": mode})
        console.print(f"[green]Tags imported from {file} (mode: {mode}).[/]")


@app.command()
@error_handler
def providers(
    gateway: Annotated[Optional[str], typer.Option("--gateway", "-g")] = None,
    url: Annotated[Optional[str], typer.Option("--url")] = None,
    token: Annotated[Optional[str], typer.Option("--token")] = None,
    fmt: Annotated[str, typer.Option("--format", "-f")] = "table",
) -> None:
    """List tag providers."""
    with _client(gateway, url, token) as client:
        data = client.get_json("/resources/list/ignition/tag-provider")
        items = data if isinstance(data, list) else data.get("resources", data.get("items", []))
        columns = ["Name", "Type", "State"]
        rows = [[p.get("name", ""), p.get("type", ""), p.get("state", "")] for p in items]
        output(data, fmt, columns=columns, rows=rows, title="Tag Providers")
