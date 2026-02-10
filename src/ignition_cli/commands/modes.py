"""Deployment mode commands — manage dev/staging/prod modes."""

from __future__ import annotations

from typing import Annotated, Optional

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
    title: Annotated[Optional[str], typer.Option(
        "--title", "-t", help="Short title for the mode",
    )] = None,
    description: Annotated[Optional[str], typer.Option(
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
    new_name: Annotated[Optional[str], typer.Option(
        "--name", "-n", help="Rename the mode",
    )] = None,
    title: Annotated[Optional[str], typer.Option(
        "--title", "-t", help="Short title for the mode",
    )] = None,
    description: Annotated[Optional[str], typer.Option(
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
