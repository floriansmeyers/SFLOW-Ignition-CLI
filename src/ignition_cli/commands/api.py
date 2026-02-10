"""Raw API commands — direct HTTP access to any gateway endpoint."""

from __future__ import annotations

import json
from typing import Annotated, Optional

import typer
from rich.console import Console

from ignition_cli.client.errors import error_handler
from ignition_cli.client.gateway import GatewayClient
from ignition_cli.config.manager import ConfigManager
from ignition_cli.output.formatter import output

app = typer.Typer(name="api", help="Raw API access and endpoint discovery.")
console = Console()


def _client(gateway: str | None, url: str | None, token: str | None) -> GatewayClient:
    mgr = ConfigManager()
    profile = mgr.resolve_gateway(profile_name=gateway, url=url, token=token)
    return GatewayClient(profile)


def _parse_body(data: str | None) -> dict | None:
    if not data:
        return None
    try:
        return json.loads(data)
    except json.JSONDecodeError:
        console.print("[red]Invalid JSON body.[/]")
        raise typer.Exit(1)


@app.command("get")
@error_handler
def api_get(
    path: Annotated[str, typer.Argument(help="API path (e.g. /status)")],
    gateway: Annotated[Optional[str], typer.Option("--gateway", "-g")] = None,
    url: Annotated[Optional[str], typer.Option("--url")] = None,
    token: Annotated[Optional[str], typer.Option("--token")] = None,
    fmt: Annotated[str, typer.Option("--format", "-f")] = "json",
) -> None:
    """Send a GET request to a gateway API endpoint."""
    with _client(gateway, url, token) as client:
        resp = client.get(path)
        data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text
        output(data, fmt, kv=isinstance(data, dict))


@app.command("post")
@error_handler
def api_post(
    path: Annotated[str, typer.Argument(help="API path")],
    body: Annotated[Optional[str], typer.Option("--data", "-d", help="JSON body")] = None,
    gateway: Annotated[Optional[str], typer.Option("--gateway", "-g")] = None,
    url: Annotated[Optional[str], typer.Option("--url")] = None,
    token: Annotated[Optional[str], typer.Option("--token")] = None,
    fmt: Annotated[str, typer.Option("--format", "-f")] = "json",
) -> None:
    """Send a POST request to a gateway API endpoint."""
    json_body = _parse_body(body)
    with _client(gateway, url, token) as client:
        resp = client.post(path, json=json_body)
        data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text
        output(data, fmt, kv=isinstance(data, dict))


@app.command("put")
@error_handler
def api_put(
    path: Annotated[str, typer.Argument(help="API path")],
    body: Annotated[Optional[str], typer.Option("--data", "-d", help="JSON body")] = None,
    gateway: Annotated[Optional[str], typer.Option("--gateway", "-g")] = None,
    url: Annotated[Optional[str], typer.Option("--url")] = None,
    token: Annotated[Optional[str], typer.Option("--token")] = None,
    fmt: Annotated[str, typer.Option("--format", "-f")] = "json",
) -> None:
    """Send a PUT request to a gateway API endpoint."""
    json_body = _parse_body(body)
    with _client(gateway, url, token) as client:
        resp = client.put(path, json=json_body)
        data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text
        output(data, fmt, kv=isinstance(data, dict))


@app.command("delete")
@error_handler
def api_delete(
    path: Annotated[str, typer.Argument(help="API path")],
    gateway: Annotated[Optional[str], typer.Option("--gateway", "-g")] = None,
    url: Annotated[Optional[str], typer.Option("--url")] = None,
    token: Annotated[Optional[str], typer.Option("--token")] = None,
    fmt: Annotated[str, typer.Option("--format", "-f")] = "json",
) -> None:
    """Send a DELETE request to a gateway API endpoint."""
    with _client(gateway, url, token) as client:
        resp = client.delete(path)
        if resp.status_code == 204:
            console.print("[green]Deleted.[/]")
        else:
            data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text
            output(data, fmt, kv=isinstance(data, dict))


@app.command("discover")
@error_handler
def api_discover(
    filter_path: Annotated[Optional[str], typer.Option("--filter", help="Filter endpoints by path")] = None,
    method: Annotated[Optional[str], typer.Option("--method", "-m", help="Filter by HTTP method")] = None,
    gateway: Annotated[Optional[str], typer.Option("--gateway", "-g")] = None,
    url: Annotated[Optional[str], typer.Option("--url")] = None,
    token: Annotated[Optional[str], typer.Option("--token")] = None,
) -> None:
    """Browse available API endpoints from the OpenAPI spec."""
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
    output_file: Annotated[Optional[str], typer.Option("--output", "-o", help="Save spec to file")] = None,
    gateway: Annotated[Optional[str], typer.Option("--gateway", "-g")] = None,
    url: Annotated[Optional[str], typer.Option("--url")] = None,
    token: Annotated[Optional[str], typer.Option("--token")] = None,
) -> None:
    """Download the OpenAPI spec from the gateway."""
    import httpx
    from pathlib import Path

    mgr = ConfigManager()
    profile = mgr.resolve_gateway(profile_name=gateway, url=url, token=token)
    resp = httpx.get(
        f"{profile.url}/openapi.json",
        verify=profile.verify_ssl,
        timeout=profile.timeout,
    )
    spec = resp.json()

    if output_file:
        Path(output_file).write_text(json.dumps(spec, indent=2))
        console.print(f"[green]OpenAPI spec saved to {output_file}[/]")
    else:
        console.print_json(json.dumps(spec, indent=2))
