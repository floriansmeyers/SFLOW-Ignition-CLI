"""Deployment mode commands — manage dev/staging/prod modes."""

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
    get_resource_data,
    make_client,
    validate_resource_type,
)
from ignition_cli.output.formatter import output

app = typer.Typer(
    name="mode",
    help="Manage gateway deployment modes (dev/staging/prod).",
)
console = Console()


@app.command("list")
@error_handler
def list_modes(
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
    fmt: FormatOpt = "table",
) -> None:
    """List all deployment modes."""
    with make_client(gateway, url, token) as client:
        data = client.get_json("/mode")
        items = extract_items(data)
        columns = ["Name", "Title", "Description", "Resources"]
        rows = [
            [
                m.get("name", ""),
                m.get("title", ""),
                m.get("description", ""),
                str(m.get("resourceCount", 0)),
            ]
            for m in items
        ]
        output(
            data, fmt,
            columns=columns, rows=rows,
            title="Deployment Modes",
        )


@app.command()
@error_handler
def show(
    name: Annotated[str, typer.Argument(help="Mode name")],
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
    fmt: FormatOpt = "table",
) -> None:
    """Show details of a deployment mode."""
    with make_client(gateway, url, token) as client:
        data = client.get_json("/mode")
        items = extract_items(data)
        match = next((m for m in items if m.get("name") == name), None)
        if match is None:
            console.print(f"[red]Mode '{name}' not found.[/]")
            raise typer.Exit(1)
        output(match, fmt, kv=True, title=f"Mode: {name}")


@app.command()
@error_handler
def create(
    name: Annotated[str, typer.Argument(help="Mode name")],
    title: Annotated[str | None, typer.Option(
        "--title", "-t", help="Short title for the mode",
    )] = None,
    description: Annotated[str | None, typer.Option(
        "--description", "-d", help="Mode description",
    )] = None,
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
) -> None:
    """Create a new deployment mode."""
    body: dict[str, str] = {"name": name}
    if title:
        body["title"] = title
    if description:
        body["description"] = description
    with make_client(gateway, url, token) as client:
        client.post("/mode", json=body)
        console.print(
            f"[green]Deployment mode '{name}' created.[/]"
        )


@app.command()
@error_handler
def update(
    name: Annotated[str, typer.Argument(help="Mode name")],
    new_name: Annotated[str | None, typer.Option(
        "--name", "-n", help="Rename the mode",
    )] = None,
    title: Annotated[str | None, typer.Option(
        "--title", "-t", help="Short title for the mode",
    )] = None,
    description: Annotated[str | None, typer.Option(
        "--description", "-d", help="Mode description",
    )] = None,
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
) -> None:
    """Update or rename a deployment mode."""
    body: dict[str, str] = {"name": new_name or name}
    if title:
        body["title"] = title
    if description:
        body["description"] = description
    if not new_name and not title and not description:
        console.print("[yellow]Nothing to update.[/]")
        return
    with make_client(gateway, url, token) as client:
        client.put(f"/mode/{name}", json=body)
        console.print(
            f"[green]Deployment mode '{name}' updated.[/]"
        )


@app.command()
@error_handler
def delete(
    name: Annotated[str, typer.Argument(help="Mode name")],
    force: Annotated[bool, typer.Option(
        "--force", help="Skip confirmation",
    )] = False,
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
) -> None:
    """Delete a deployment mode."""
    if not force:
        from rich.prompt import Confirm

        if not Confirm.ask(f"Delete mode '{name}'?"):
            console.print("Cancelled.")
            return
    with make_client(gateway, url, token) as client:
        client.delete(f"/mode/{name}")
        console.print(
            f"[green]Deployment mode '{name}' deleted.[/]"
        )


@app.command()
@error_handler
def assign(
    name: Annotated[str, typer.Argument(help="Mode name")],
    resource_type: Annotated[
        str,
        typer.Argument(
            help="Resource type (e.g. ignition/database-connection)"
        ),
    ],
    resource_name: Annotated[
        str | None,
        typer.Argument(
            help="Resource name (omit for singleton resources)",
        ),
    ] = None,
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
) -> None:
    """Assign a resource to a deployment mode.

    Omit RESOURCE_NAME for singleton resources.
    """
    module, rtype = validate_resource_type(resource_type)
    with make_client(gateway, url, token) as client:
        # Fetch existing resource to get its current config
        data = get_resource_data(client, module, rtype, resource_name)
        resolved_name = resource_name or data.get("name", "")
        body = {**data, "name": resolved_name, "collection": name}
        # Remove read-only fields that shouldn't be sent back
        for key in ("signature", "state", "resourceCount"):
            body.pop(key, None)
        client.post(f"/resources/{module}/{rtype}", json=[body])
        console.print(
            f"[green]Resource '{resolved_name}' ({resource_type}) "
            f"assigned to mode '{name}'.[/]"
        )


@app.command()
@error_handler
def unassign(
    name: Annotated[str, typer.Argument(help="Mode name")],
    resource_type: Annotated[
        str,
        typer.Argument(
            help="Resource type (e.g. ignition/database-connection)"
        ),
    ],
    resource_name: Annotated[
        str | None,
        typer.Argument(
            help="Resource name (omit for singleton resources)",
        ),
    ] = None,
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
) -> None:
    """Remove a resource from a deployment mode.

    Omit RESOURCE_NAME for singleton resources.
    """
    module, rtype = validate_resource_type(resource_type)
    with make_client(gateway, url, token) as client:
        # Fetch mode-specific resource to get its signature
        data = get_resource_data(
            client, module, rtype, resource_name,
            params={"collection": name},
        )
        resolved_name = resource_name or data.get("name", "")
        sig = data.get("signature")
        if not sig:
            console.print(
                f"[red]No signature found on resource '{resolved_name}'. "
                "Cannot unassign.[/]"
            )
            raise typer.Exit(1)
        client.delete(
            f"/resources/{module}/{rtype}/{resolved_name}/{sig}",
            params={"collection": name, "confirm": "true"},
        )
        console.print(
            f"[green]Resource '{resolved_name}' ({resource_type}) "
            f"removed from mode '{name}'.[/]"
        )
