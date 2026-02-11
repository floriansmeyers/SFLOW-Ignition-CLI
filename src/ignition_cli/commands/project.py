"""Project commands.

list, show, create, delete, export, import, diff, watch, resources.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console

from ignition_cli.client.errors import error_handler
from ignition_cli.client.gateway import GatewayClient
from ignition_cli.commands._common import (
    FormatOpt,
    GatewayOpt,
    TokenOpt,
    UrlOpt,
    extract_items,
    make_client,
)
from ignition_cli.config.manager import ConfigManager
from ignition_cli.output.formatter import output

app = typer.Typer(name="project", help="Manage Ignition projects.")
console = Console()


@app.command("list")
@error_handler
def list_projects(
    filter_text: Annotated[
        str | None,
        typer.Option("--filter", help="Filter by name"),
    ] = None,
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
    fmt: FormatOpt = "table",
) -> None:
    """List all projects on the gateway."""
    with make_client(gateway, url, token) as client:
        data = client.get_json("/projects/list")
        items = extract_items(data, "projects")
        if filter_text:
            items = [
                p for p in items
                if filter_text.lower() in p.get("name", "").lower()
            ]
        columns = ["Name", "Title", "Enabled", "State", "Last Modified"]
        rows = [
            [
                p.get("name", ""),
                p.get("title", ""),
                str(p.get("enabled", "")),
                p.get("state", ""),
                p.get("lastModified", p.get("last_modified", "")),
            ]
            for p in items
        ]
        output(data, fmt, columns=columns, rows=rows, title="Projects")


@app.command()
@error_handler
def show(
    name: Annotated[str, typer.Argument(help="Project name")],
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
    fmt: FormatOpt = "table",
) -> None:
    """Show project details."""
    with make_client(gateway, url, token) as client:
        data = client.get_json(f"/projects/find/{name}")
        output(data, fmt, kv=True, title=f"Project: {name}")


@app.command()
@error_handler
def create(
    name: Annotated[str, typer.Argument(help="Project name")],
    title: Annotated[
        str | None,
        typer.Option("--title", "-t", help="Project title"),
    ] = None,
    description: Annotated[str | None, typer.Option("--description", "-d")] = None,
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
) -> None:
    """Create a new project."""
    body: dict[str, Any] = {"name": name}
    if title:
        body["title"] = title
    if description:
        body["description"] = description
    with make_client(gateway, url, token) as client:
        client.post("/projects", json=body)
        console.print(f"[green]Project '{name}' created.[/]")


@app.command()
@error_handler
def delete(
    name: Annotated[str, typer.Argument(help="Project name")],
    force: Annotated[bool, typer.Option("--force", help="Skip confirmation")] = False,
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
) -> None:
    """Delete a project."""
    if not force:
        from rich.prompt import Confirm

        if not Confirm.ask(f"Delete project '{name}'? This cannot be undone"):
            console.print("Cancelled.")
            return
    with make_client(gateway, url, token) as client:
        client.delete(f"/projects/{name}")
        console.print(f"[green]Project '{name}' deleted.[/]")


@app.command("export")
@error_handler
def export_project(
    name: Annotated[str, typer.Argument(help="Project name")],
    output_file: Annotated[
        str | None,
        typer.Option("--output", "-o", help="Output file path"),
    ] = None,
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
) -> None:
    """Export a project as a .zip file."""
    dest = Path(output_file) if output_file else Path(f"{name}.zip")
    if dest.is_dir():
        console.print(f"[red]Output path is a directory: {dest}[/]")
        raise typer.Exit(1)
    if not dest.parent.exists():
        console.print(f"[red]Directory does not exist: {dest.parent}[/]")
        raise typer.Exit(1)
    with make_client(gateway, url, token) as client:
        size = client.stream_to_file(f"/projects/export/{name}", dest)
        console.print(
            f"[green]Project '{name}' exported to"
            f" {dest}[/] ({size:,} bytes)"
        )


@app.command("import")
@error_handler
def import_project(
    file: Annotated[str, typer.Argument(help="Project file to import (.zip)")],
    name: Annotated[
        str | None,
        typer.Option(
            "--name", "-n",
            help="Project name (defaults to filename stem)",
        ),
    ] = None,
    overwrite: Annotated[
        bool,
        typer.Option("--overwrite", help="Overwrite if exists"),
    ] = False,
    force: Annotated[bool, typer.Option("--force", help="Skip confirmation")] = False,
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
) -> None:
    """Import a project from a file."""
    file_path = Path(file)
    if not file_path.exists():
        console.print(f"[red]File not found: {file}[/]")
        raise typer.Exit(1)
    project_name = name or file_path.stem

    if overwrite and not force:
        from rich.prompt import Confirm

        if not Confirm.ask(
            f"Overwrite project '{project_name}' if it exists?"
        ):
            console.print("Cancelled.")
            return

    with make_client(gateway, url, token) as client:
        params = {"overwrite": "true"} if overwrite else {}
        client.stream_upload(
            "POST", f"/projects/import/{project_name}", file_path,
            params=params,
            headers={"Content-Type": "application/zip"},
        )
        console.print(f"[green]Project '{project_name}' imported from {file}.[/]")


@app.command()
@error_handler
def copy(
    name: Annotated[str, typer.Argument(help="Source project name")],
    new_name: Annotated[str, typer.Option("--name", "-n", help="New project name")],
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
) -> None:
    """Copy a project to a new name."""
    with make_client(gateway, url, token) as client:
        client.post(
            "/projects/copy",
            json={
                "fromName": name,
                "toName": new_name,
            },
        )
        console.print(f"[green]Project '{name}' copied to '{new_name}'.[/]")


@app.command()
@error_handler
def rename(
    name: Annotated[str, typer.Argument(help="Current project name")],
    new_name: Annotated[str, typer.Option("--name", "-n", help="New project name")],
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
) -> None:
    """Rename a project."""
    with make_client(gateway, url, token) as client:
        client.post(f"/projects/rename/{name}", json={"name": new_name})
        console.print(f"[green]Project '{name}' renamed to '{new_name}'.[/]")


@app.command()
@error_handler
def resources(
    name: Annotated[str, typer.Argument(help="Project name")],
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
    fmt: FormatOpt = "table",
) -> None:
    """List resources in a project."""
    with make_client(gateway, url, token) as client:
        data = client.get_json(f"/projects/find/{name}")
        items = extract_items(data, "resources")
        columns = ["Name", "Type", "Path", "Scope"]
        rows = [
            [
                r.get("name", ""),
                r.get("type", ""),
                r.get("path", ""),
                r.get("scope", ""),
            ]
            for r in items
        ]
        output(data, fmt, columns=columns, rows=rows, title=f"Resources: {name}")


@app.command()
@error_handler
def diff(
    name: Annotated[str, typer.Argument(help="Project name")],
    target: Annotated[
        str,
        typer.Option(
            "--target", "-t",
            help="Target gateway profile for comparison",
        ),
    ],
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
) -> None:
    """Diff a project between two gateways."""
    from ignition_cli.utils.diff import diff_projects

    mgr = ConfigManager()
    source_profile = mgr.resolve_gateway(profile_name=gateway, url=url, token=token)
    target_profile = mgr.resolve_gateway(profile_name=target)

    with (
        GatewayClient(source_profile) as source,
        GatewayClient(target_profile) as target_client,
    ):
        source_data = source.get_json(f"/projects/find/{name}")
        target_data = target_client.get_json(f"/projects/find/{name}")
        diff_projects(name, source_data, target_data, console)


@app.command()
@error_handler
def watch(
    name: Annotated[str, typer.Argument(help="Project name")],
    path: Annotated[str, typer.Argument(help="Local directory to watch")],
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
) -> None:
    """Watch a local directory and sync changes to a project."""
    from ignition_cli.utils.file_watcher import watch_and_sync

    mgr = ConfigManager()
    profile = mgr.resolve_gateway(profile_name=gateway, url=url, token=token)
    watch_dir = Path(path)
    if not watch_dir.is_dir():
        console.print(f"[red]Directory not found: {path}[/]")
        raise typer.Exit(1)
    console.print(f"[bold]Watching {watch_dir} for changes to project '{name}'...[/]")
    console.print("[dim]Press Ctrl+C to stop.[/]")
    watch_and_sync(profile, name, watch_dir, console)
