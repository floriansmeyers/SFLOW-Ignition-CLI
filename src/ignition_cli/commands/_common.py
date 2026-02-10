"""Shared helpers for CLI commands — client factory, options, response parsing."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from ignition_cli.client.gateway import GatewayClient
from ignition_cli.config.manager import ConfigManager

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
        return data
    if isinstance(data, dict):
        if "items" in data:
            return data["items"]
        for key in fallback_keys:
            if key in data:
                return data[key]
    return []


def extract_metadata(data: Any) -> dict[str, Any]:
    """Extract pagination metadata from an API response."""
    if isinstance(data, dict) and "metadata" in data:
        return data["metadata"]
    return {}
