"""Raw API commands — direct HTTP access to any gateway endpoint."""

from __future__ import annotations

import json
from typing import Annotated

import typer
from rich.console import Console

from ignition_cli.client.errors import error_handler
from ignition_cli.commands._common import (
    FormatOpt,
    GatewayOpt,
    TokenOpt,
    UrlOpt,
    make_client,
)
from ignition_cli.output.formatter import output

app = typer.Typer(name="api", help="Raw API access and endpoint discovery.")
console = Console()


def _parse_body(data: str | None) -> dict | None:
    if not data:
        return None
    try:
        return json.loads(data)
    except json.JSONDecodeError:
        console.print("[red]Invalid JSON body.[/]")
        raise typer.Exit(1) from None


@app.command("get")
@error_handler
def api_get(
    path: Annotated[str, typer.Argument(help="API path (e.g. /status)")],
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
    fmt: FormatOpt = "json",
) -> None:
    """Send a GET request to a gateway API endpoint."""
    with make_client(gateway, url, token) as client:
        resp = client.get(path)
        ct = resp.headers.get("content-type", "")
        data = resp.json() if ct.startswith("application/json") else resp.text
        output(data, fmt, kv=isinstance(data, dict))


@app.command("post")
@error_handler
def api_post(
    path: Annotated[str, typer.Argument(help="API path")],
    body: Annotated[str | None, typer.Option("--data", "-d", help="JSON body")] = None,
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
    fmt: FormatOpt = "json",
) -> None:
    """Send a POST request to a gateway API endpoint."""
    json_body = _parse_body(body)
    with make_client(gateway, url, token) as client:
        resp = client.post(path, json=json_body)
        ct = resp.headers.get("content-type", "")
        data = resp.json() if ct.startswith("application/json") else resp.text
        output(data, fmt, kv=isinstance(data, dict))


@app.command("put")
@error_handler
def api_put(
    path: Annotated[str, typer.Argument(help="API path")],
    body: Annotated[str | None, typer.Option("--data", "-d", help="JSON body")] = None,
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
    fmt: FormatOpt = "json",
) -> None:
    """Send a PUT request to a gateway API endpoint."""
    json_body = _parse_body(body)
    with make_client(gateway, url, token) as client:
        resp = client.put(path, json=json_body)
        ct = resp.headers.get("content-type", "")
        data = resp.json() if ct.startswith("application/json") else resp.text
        output(data, fmt, kv=isinstance(data, dict))


@app.command("delete")
@error_handler
def api_delete(
    path: Annotated[str, typer.Argument(help="API path")],
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
    fmt: FormatOpt = "json",
) -> None:
    """Send a DELETE request to a gateway API endpoint."""
    with make_client(gateway, url, token) as client:
        resp = client.delete(path)
        if resp.status_code == 204:
            console.print("[green]Deleted.[/]")
        else:
            ct = resp.headers.get("content-type", "")
            data = resp.json() if ct.startswith("application/json") else resp.text
            output(data, fmt, kv=isinstance(data, dict))


@app.command("discover")
@error_handler
def api_discover(
    filter_path: Annotated[
        str | None,
        typer.Option("--filter", help="Filter endpoints by path"),
    ] = None,
    method: Annotated[
        str | None,
        typer.Option("--method", "-m", help="Filter by HTTP method"),
    ] = None,
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
) -> None:
    """Browse available API endpoints from the OpenAPI spec."""
    with make_client(gateway, url, token) as client:
        spec = client.get_openapi_spec()
    paths = spec.get("paths", {})

    from ignition_cli.output.tables import make_table

    columns = ["Method", "Path", "Summary"]
    rows = []
    for path_str, methods in sorted(paths.items()):
        if filter_path and filter_path.lower() not in path_str.lower():
            continue
        for http_method, details in methods.items():
            if http_method.startswith("x-"):
                continue
            if method and method.upper() != http_method.upper():
                continue
            summary = details.get("summary", details.get("description", ""))[:80]
            rows.append([http_method.upper(), path_str, summary])

    console.print(make_table("API Endpoints", columns, rows))
    console.print(f"\n[dim]{len(rows)} endpoints found[/]")


@app.command("spec")
@error_handler
def api_spec(
    output_file: Annotated[
        str | None,
        typer.Option("--output", "-o", help="Save spec to file"),
    ] = None,
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
) -> None:
    """Download the OpenAPI spec from the gateway."""
    from pathlib import Path

    with make_client(gateway, url, token) as client:
        spec = client.get_openapi_spec()

    if output_file:
        Path(output_file).write_text(json.dumps(spec, indent=2))
        console.print(f"[green]OpenAPI spec saved to {output_file}[/]")
    else:
        console.print_json(json.dumps(spec, indent=2))
