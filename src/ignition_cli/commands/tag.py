"""Tag commands — browse, read, write, export, import, providers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.tree import Tree

from ignition_cli.client.errors import NotFoundError, error_handler
from ignition_cli.commands._common import (
    FormatOpt,
    GatewayOpt,
    TokenOpt,
    UrlOpt,
    extract_items,
    make_client,
)
from ignition_cli.output.formatter import output

app = typer.Typer(name="tag", help="Browse, read, write, and manage tags.")
console = Console()


def _build_tree(
    node_data: dict[str, Any] | list[Any], tree: Tree, recursive: bool = False,
) -> None:
    """Build a Rich tree from tag browse data."""
    items = extract_items(node_data, "tags")
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
    path: Annotated[str | None, typer.Argument(help="Tag path to browse")] = None,
    recursive: Annotated[
        bool,
        typer.Option("--recursive", "-r", help="Browse recursively"),
    ] = False,
    provider: Annotated[
        str,
        typer.Option("--provider", "-p", help="Tag provider"),
    ] = "default",
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
    fmt: FormatOpt = "table",
) -> None:
    """Browse the tag tree.

    Note: Tag browsing is not part of the standard Ignition REST API.
    This uses the tag export endpoint to retrieve tag structure.
    """
    with make_client(gateway, url, token) as client:
        params: dict[str, str] = {"provider": provider, "type": "json"}
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
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
    fmt: FormatOpt = "table",
) -> None:
    """Read one or more tag values.

    Note: Tag reading is not part of the standard Ignition
    REST API. This requires a gateway with a WebDev endpoint
    or custom module providing this capability.
    """
    console.print(
        "[yellow]Warning: /tags/read is not a standard"
        " Ignition REST API endpoint. This requires a"
        " WebDev module or custom endpoint.[/]"
    )
    with make_client(gateway, url, token) as client:
        try:
            resp = client.post("/tags/read", json=paths, params={"provider": provider})
        except NotFoundError:
            console.print(
                "[red]Endpoint /tags/read not found."
                " This gateway does not support tag"
                " reading via the REST API. Install"
                " the WebDev module or configure a"
                " custom endpoint.[/]"
            )
            raise typer.Exit(1) from None
        items = resp.json()
        if not isinstance(items, list):
            items = extract_items(items, "values")

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
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
) -> None:
    """Write a value to a tag.

    Note: Tag writing is not part of the standard Ignition
    REST API. This requires a gateway with a WebDev endpoint
    or custom module providing this capability.
    """
    console.print(
        "[yellow]Warning: /tags/write is not a standard"
        " Ignition REST API endpoint. This requires a"
        " WebDev module or custom endpoint.[/]"
    )
    # Try to parse as JSON for numeric/boolean values
    try:
        parsed = json.loads(value)
    except (json.JSONDecodeError, ValueError):
        parsed = value

    with make_client(gateway, url, token) as client:
        try:
            client.post(
                "/tags/write",
                json=[{"path": path, "value": parsed}],
                params={"provider": provider},
            )
        except NotFoundError:
            console.print(
                "[red]Endpoint /tags/write not found."
                " This gateway does not support tag"
                " writing via the REST API. Install"
                " the WebDev module or configure a"
                " custom endpoint.[/]"
            )
            raise typer.Exit(1) from None
        console.print(f"[green]Wrote {parsed!r} to {path}[/]")


@app.command("export")
@error_handler
def export_tags(
    path: Annotated[
        str | None,
        typer.Argument(help="Tag path to export (root if omitted)"),
    ] = None,
    output_file: Annotated[
        str | None,
        typer.Option("--output", "-o", help="Output file"),
    ] = None,
    provider: Annotated[str, typer.Option("--provider", "-p")] = "default",
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
) -> None:
    """Export tag configuration as JSON."""
    with make_client(gateway, url, token) as client:
        params: dict[str, str] = {"provider": provider, "type": "json"}
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
    file: Annotated[str, typer.Argument(help="Tag file to import (JSON, XML, or CSV)")],
    collision_policy: Annotated[str, typer.Option(
        "--collision-policy", "-c",
        help="Collision policy: Abort, Overwrite, Rename, Ignore, MergeOverwrite",
    )] = "MergeOverwrite",
    path: Annotated[
        str | None,
        typer.Option("--path", help="Target path for import"),
    ] = None,
    provider: Annotated[str, typer.Option("--provider", "-p")] = "default",
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
) -> None:
    """Import tag configuration from a file (JSON, XML, or CSV)."""
    file_path = Path(file)
    if not file_path.exists():
        console.print(f"[red]File not found: {file}[/]")
        raise typer.Exit(1)

    suffix = file_path.suffix.lower()
    type_map = {".json": "json", ".xml": "xml", ".csv": "csv"}
    file_type = type_map.get(suffix, "json")

    tag_data = file_path.read_bytes()
    content_type = (
        "application/json"
        if file_type == "json"
        else "application/octet-stream"
    )

    with make_client(gateway, url, token) as client:
        params: dict[str, str] = {
            "provider": provider,
            "type": file_type,
            "collisionPolicy": collision_policy,
        }
        if path:
            params["path"] = path
        client.post(
            "/tags/import",
            content=tag_data,
            params=params,
            headers={"Content-Type": content_type},
        )
        console.print(
            f"[green]Tags imported from {file}"
            f" (policy: {collision_policy}).[/]"
        )


@app.command()
@error_handler
def providers(
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
    fmt: FormatOpt = "table",
) -> None:
    """List tag providers."""
    with make_client(gateway, url, token) as client:
        data = client.get_json("/resources/list/ignition/tag-provider")
        items = extract_items(data, "resources")
        columns = ["Name", "Profile", "Tags", "Status"]
        rows = []
        for p in items:
            profile_type = ""
            cfg = p.get("config")
            if isinstance(cfg, dict):
                profile = cfg.get("profile")
                if isinstance(profile, dict):
                    profile_type = profile.get("type", "")
            tag_count = ""
            metrics = p.get("metrics")
            if isinstance(metrics, dict):
                tc = metrics.get("tagCount")
                if isinstance(tc, dict):
                    m = tc.get("metric")
                    if isinstance(m, dict):
                        tag_count = str(m.get("value", ""))
            status = ""
            hc = p.get("healthchecks")
            if isinstance(hc, dict):
                s = hc.get("status")
                if isinstance(s, dict):
                    r = s.get("result")
                    if isinstance(r, dict):
                        status = r.get("message", "")
            rows.append([p.get("name", ""), profile_type, tag_count, status])
        output(data, fmt, columns=columns, rows=rows, title="Tag Providers")
