"""Shared helpers for CLI commands — client factory, options, response parsing."""

from __future__ import annotations

from typing import Annotated, Any

import typer
from rich.console import Console

from ignition_cli.client.gateway import GatewayClient
from ignition_cli.config.manager import ConfigManager

_console = Console()

# Shared Typer option type aliases
GatewayOpt = Annotated[
    str | None,
    typer.Option("--gateway", "-g", help="Gateway profile"),
]
UrlOpt = Annotated[
    str | None,
    typer.Option("--url", help="Gateway URL override"),
]
TokenOpt = Annotated[
    str | None,
    typer.Option("--token", help="API token override"),
]
FormatOpt = Annotated[
    str,
    typer.Option("--format", "-f", help="Output format"),
]
LimitOpt = Annotated[
    int | None,
    typer.Option("--limit", help="Max items to return"),
]
OffsetOpt = Annotated[
    int | None,
    typer.Option("--offset", help="Offset for pagination"),
]


def make_client(
    gateway: str | None,
    url: str | None,
    token: str | None,
) -> GatewayClient:
    """Create a GatewayClient from CLI options, env vars, or config profile."""
    mgr = ConfigManager()
    profile = mgr.resolve_gateway(profile_name=gateway, url=url, token=token)
    return GatewayClient(profile)


def extract_items(data: Any, *fallback_keys: str) -> list[Any]:
    """Extract a list of items from a paginated or mixed API response.

    Tries ``data`` directly if it's a list, then checks ``items``, then
    each *fallback_keys* in order, falling back to an empty list.
    """
    if isinstance(data, list):
        return list(data)
    if isinstance(data, dict):
        if "items" in data:
            return list(data["items"])
        for key in fallback_keys:
            if key in data:
                return list(data[key])
    return []


def extract_metadata(data: Any) -> dict[str, Any]:
    """Extract pagination metadata from an API response."""
    if isinstance(data, dict) and "metadata" in data:
        result: dict[str, Any] = data["metadata"]
        return result
    return {}


def validate_resource_type(resource_type: str) -> tuple[str, str]:
    """Validate and split resource_type into (module, type)."""
    if "/" not in resource_type:
        _console.print(
            f"[red]Invalid resource type '{resource_type}'. "
            "Use module/type format (e.g. ignition/database-connection).[/]"
        )
        raise typer.Exit(1)
    parts = resource_type.split("/", 1)
    return parts[0], parts[1]


def get_resource_data(
    client: GatewayClient,
    module: str,
    rtype: str,
    name: str | None,
    *,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Fetch resource data, using the singleton endpoint when *name* is ``None``.

    Named resources use ``GET /resources/find/{module}/{type}/{name}``.
    Singleton resources use ``GET /resources/singleton/{module}/{type}``.
    """
    if name:
        path = f"/resources/find/{module}/{rtype}/{name}"
    else:
        path = f"/resources/singleton/{module}/{rtype}"
    result: dict[str, Any] = client.get_json(path, params=params)
    return result
