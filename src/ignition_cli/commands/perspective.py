"""Perspective commands — manage views, pages, styles, and session props.

Perspective resources are project-scoped and not exposed via the gateway
resource API.  All operations use the project export/import cycle:
read-only commands stream the project zip and parse entries in memory;
write commands extract to a temp directory, apply changes, repack, and
import back with ``overwrite=true``.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import zipfile
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.tree import Tree

from ignition_cli.client.errors import error_handler
from ignition_cli.client.gateway import GatewayClient
from ignition_cli.commands._common import (
    FormatOpt,
    GatewayOpt,
    TokenOpt,
    UrlOpt,
    make_client,
)
from ignition_cli.output.formatter import output

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PERSPECTIVE = "com.inductiveautomation.perspective"

# ---------------------------------------------------------------------------
# Typer apps
# ---------------------------------------------------------------------------

app = typer.Typer(
    name="perspective",
    help="Manage Perspective views, pages, styles, and session properties.",
    no_args_is_help=True,
)
view_app = typer.Typer(
    name="view",
    help="Perspective view CRUD.",
    no_args_is_help=True,
)
page_app = typer.Typer(
    name="page",
    help="Perspective page configuration.",
    no_args_is_help=True,
)
style_app = typer.Typer(
    name="style",
    help="Perspective style classes.",
    no_args_is_help=True,
)
session_app = typer.Typer(
    name="session",
    help="Perspective session properties.",
    no_args_is_help=True,
)

app.add_typer(view_app, name="view")
app.add_typer(page_app, name="page")
app.add_typer(style_app, name="style")
app.add_typer(session_app, name="session")

console = Console()

# ---------------------------------------------------------------------------
# Project helper – export/import cycle
# ---------------------------------------------------------------------------


@contextmanager
def _open_project_zip(
    client: GatewayClient,
    project_name: str,
) -> Iterator[zipfile.ZipFile]:
    """Export a project and yield a read-only ZipFile."""
    with tempfile.NamedTemporaryFile(
        suffix=".zip", delete=False,
    ) as tmp:
        temp_path = Path(tmp.name)
    try:
        client.stream_to_file(
            f"/projects/export/{project_name}", temp_path,
        )
        with zipfile.ZipFile(temp_path, "r") as zf:
            yield zf
    finally:
        temp_path.unlink(missing_ok=True)


@contextmanager
def _modify_project(
    client: GatewayClient,
    project_name: str,
) -> Iterator[Path]:
    """Export, extract, yield work dir, repack, import."""
    with tempfile.TemporaryDirectory() as tmpdir:
        export_path = Path(tmpdir) / "export.zip"
        client.stream_to_file(
            f"/projects/export/{project_name}", export_path,
        )

        work_dir = Path(tmpdir) / "project"
        with zipfile.ZipFile(export_path, "r") as zf:
            zf.extractall(work_dir)

        yield work_dir

        # Repack
        import_path = Path(tmpdir) / "import.zip"
        with zipfile.ZipFile(
            import_path, "w", zipfile.ZIP_DEFLATED,
        ) as zf:
            for file in sorted(work_dir.rglob("*")):
                if file.is_file():
                    zf.write(file, file.relative_to(work_dir))

        # Import with overwrite
        client.stream_upload(
            "POST",
            f"/projects/import/{project_name}",
            import_path,
            params={"overwrite": "true"},
            headers={"Content-Type": "application/zip"},
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _perspective_prefix(resource_type: str) -> str:
    """Return zip path prefix for a Perspective resource type."""
    return f"{PERSPECTIVE}/{resource_type}/"


def _list_entries(
    zf: zipfile.ZipFile,
    resource_type: str,
    filename: str,
) -> list[str]:
    """List named entries under a Perspective resource type.

    Returns the path portion between the prefix and ``/filename``.
    For example, ``views/Page/Home/view.json`` -> ``Page/Home``.
    """
    prefix = _perspective_prefix(resource_type)
    suffix = f"/{filename}"
    paths: set[str] = set()
    for name in zf.namelist():
        if name.startswith(prefix) and name.endswith(suffix):
            mid = name[len(prefix) : -len(suffix)]
            if mid:
                paths.add(mid)
    return sorted(paths)


def _read_json(zf: zipfile.ZipFile, inner_path: str) -> Any:
    """Read and parse a JSON file from a zip."""
    try:
        raw = zf.read(inner_path)
    except KeyError:
        console.print(
            f"[red]Not found in project: {inner_path}[/]",
        )
        raise typer.Exit(1) from None
    return json.loads(raw)


def _parse_json_input(value: str) -> Any:
    """Parse a JSON string or ``@file`` reference."""
    if value.startswith("@"):
        file_path = Path(value[1:])
        if not file_path.exists():
            console.print(f"[red]File not found: {file_path}[/]")
            raise typer.Exit(1)
        return json.loads(file_path.read_text())
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        console.print("[red]Invalid JSON.[/]")
        raise typer.Exit(1) from None


def _make_resource_json(files: list[str]) -> dict[str, Any]:
    """Build a minimal resource.json for a new Perspective resource."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "scope": "G",
        "version": 1,
        "restricted": False,
        "overridable": True,
        "files": files,
        "attributes": {
            "lastModification": {
                "actor": "external",
                "timestamp": ts,
            },
            "lastModificationSignature": "",
        },
    }


def _write_json(path: Path, data: Any) -> None:
    """Write JSON data to a file, creating parent dirs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, default=str) + "\n",
    )


# ---------------------------------------------------------------------------
# View commands
# ---------------------------------------------------------------------------


@view_app.command("list")
@error_handler
def view_list(
    project: Annotated[str, typer.Argument(help="Project name")],
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
    fmt: FormatOpt = "table",
) -> None:
    """List all Perspective views in a project."""
    with (
        make_client(gateway, url, token) as client,
        _open_project_zip(client, project) as zf,
    ):
        views = _list_entries(zf, "views", "view.json")
    if fmt in ("json", "yaml"):
        output(views, fmt)
    else:
        from ignition_cli.output.tables import make_table

        rows = [[v] for v in views]
        console.print(
            make_table(f"Views: {project}", ["View Path"], rows),
        )


@view_app.command("show")
@error_handler
def view_show(
    project: Annotated[
        str, typer.Argument(help="Project name"),
    ],
    view_path: Annotated[
        str, typer.Argument(help="View path (e.g. Page/Home)"),
    ],
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
    fmt: FormatOpt = "json",
) -> None:
    """Show a Perspective view definition."""
    inner = f"{PERSPECTIVE}/views/{view_path}/view.json"
    with (
        make_client(gateway, url, token) as client,
        _open_project_zip(client, project) as zf,
    ):
        data = _read_json(zf, inner)
    output(data, fmt, kv=True, title=f"View: {view_path}")


@view_app.command("create")
@error_handler
def view_create(
    project: Annotated[
        str, typer.Argument(help="Project name"),
    ],
    view_path: Annotated[
        str,
        typer.Argument(help="View path (e.g. MyFolder/MyView)"),
    ],
    json_data: Annotated[
        str,
        typer.Option(
            "--json", "-j",
            help="View JSON string or @file path",
        ),
    ],
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
) -> None:
    """Create a new Perspective view."""
    view_json = _parse_json_input(json_data)
    with (
        make_client(gateway, url, token) as client,
        _modify_project(client, project) as work_dir,
    ):
        vdir = work_dir / PERSPECTIVE / "views" / view_path
        if (vdir / "view.json").exists():
            console.print(
                f"[red]View '{view_path}' already exists. "
                "Use 'perspective view update' instead.[/]"
            )
            raise typer.Exit(1)
        _write_json(vdir / "view.json", view_json)
        _write_json(
            vdir / "resource.json",
            _make_resource_json(["view.json"]),
        )
    console.print(
        f"[green]View '{view_path}' created in "
        f"project '{project}'.[/]"
    )


@view_app.command("update")
@error_handler
def view_update(
    project: Annotated[
        str, typer.Argument(help="Project name"),
    ],
    view_path: Annotated[
        str, typer.Argument(help="View path (e.g. Page/Home)"),
    ],
    json_data: Annotated[
        str,
        typer.Option(
            "--json", "-j",
            help="View JSON string or @file path",
        ),
    ],
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
) -> None:
    """Update an existing Perspective view."""
    view_json = _parse_json_input(json_data)
    with (
        make_client(gateway, url, token) as client,
        _modify_project(client, project) as work_dir,
    ):
        vf = (
            work_dir / PERSPECTIVE / "views"
            / view_path / "view.json"
        )
        if not vf.exists():
            console.print(
                f"[red]View '{view_path}' not found.[/]",
            )
            raise typer.Exit(1)
        _write_json(vf, view_json)
        # Update resource.json timestamp
        res_file = vf.parent / "resource.json"
        if res_file.exists():
            res = json.loads(res_file.read_text())
            attrs = res.setdefault("attributes", {})
            mod = attrs.setdefault("lastModification", {})
            mod["timestamp"] = (
                datetime.now(timezone.utc)
                .strftime("%Y-%m-%dT%H:%M:%SZ")
            )
            mod["actor"] = "external"
            _write_json(res_file, res)
    console.print(
        f"[green]View '{view_path}' updated in "
        f"project '{project}'.[/]"
    )


@view_app.command("delete")
@error_handler
def view_delete(
    project: Annotated[
        str, typer.Argument(help="Project name"),
    ],
    view_path: Annotated[
        str, typer.Argument(help="View path to delete"),
    ],
    force: Annotated[
        bool,
        typer.Option("--force", help="Skip confirmation"),
    ] = False,
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
) -> None:
    """Delete a Perspective view from a project."""
    if not force:
        from rich.prompt import Confirm

        if not Confirm.ask(
            f"Delete view '{view_path}' "
            f"from project '{project}'?"
        ):
            console.print("Cancelled.")
            return
    with (
        make_client(gateway, url, token) as client,
        _modify_project(client, project) as work_dir,
    ):
        vdir = work_dir / PERSPECTIVE / "views" / view_path
        if not vdir.exists():
            console.print(
                f"[red]View '{view_path}' not found.[/]",
            )
            raise typer.Exit(1)
        shutil.rmtree(vdir)
    console.print(
        f"[green]View '{view_path}' deleted from "
        f"project '{project}'.[/]"
    )


@view_app.command("tree")
@error_handler
def view_tree(
    project: Annotated[str, typer.Argument(help="Project name")],
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
) -> None:
    """Show the view hierarchy as a tree."""
    with (
        make_client(gateway, url, token) as client,
        _open_project_zip(client, project) as zf,
    ):
        views = _list_entries(zf, "views", "view.json")

    tree = Tree(f"[bold]{project}[/] views")
    nodes: dict[str, Tree] = {}

    for view_path in views:
        parts = view_path.split("/")
        for i in range(len(parts)):
            key = "/".join(parts[: i + 1])
            if key not in nodes:
                parent_key = (
                    "/".join(parts[:i]) if i > 0 else ""
                )
                parent = nodes.get(parent_key, tree)
                is_leaf = key in views
                label = (
                    f"[green]{parts[i]}[/]"
                    if is_leaf
                    else f"[dim]{parts[i]}[/]"
                )
                nodes[key] = parent.add(label)

    console.print(tree)


# ---------------------------------------------------------------------------
# Page commands
# ---------------------------------------------------------------------------


@page_app.command("show")
@error_handler
def page_show(
    project: Annotated[str, typer.Argument(help="Project name")],
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
    fmt: FormatOpt = "json",
) -> None:
    """Show the Perspective page configuration."""
    inner = f"{PERSPECTIVE}/page-config/config.json"
    with (
        make_client(gateway, url, token) as client,
        _open_project_zip(client, project) as zf,
    ):
        data = _read_json(zf, inner)
    output(data, fmt, kv=True, title=f"Page Config: {project}")


@page_app.command("list")
@error_handler
def page_list(
    project: Annotated[str, typer.Argument(help="Project name")],
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
    fmt: FormatOpt = "table",
) -> None:
    """List all page routes in the Perspective page config."""
    inner = f"{PERSPECTIVE}/page-config/config.json"
    with (
        make_client(gateway, url, token) as client,
        _open_project_zip(client, project) as zf,
    ):
        data = _read_json(zf, inner)
    pages = data.get("pages", {})
    if fmt in ("json", "yaml"):
        output(pages, fmt)
    else:
        from ignition_cli.output.tables import make_table

        rows = [
            [route, cfg.get("viewPath", "")]
            for route, cfg in sorted(pages.items())
        ]
        console.print(
            make_table(
                f"Pages: {project}",
                ["Route", "View Path"],
                rows,
            )
        )


@page_app.command("update")
@error_handler
def page_update(
    project: Annotated[str, typer.Argument(help="Project name")],
    json_data: Annotated[
        str,
        typer.Option(
            "--json", "-j",
            help="Page config JSON string or @file path",
        ),
    ],
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
) -> None:
    """Update the Perspective page configuration."""
    page_json = _parse_json_input(json_data)
    with (
        make_client(gateway, url, token) as client,
        _modify_project(client, project) as work_dir,
    ):
        cfg = (
            work_dir / PERSPECTIVE
            / "page-config" / "config.json"
        )
        if not cfg.exists():
            console.print(
                "[red]Page configuration not found "
                "in project.[/]"
            )
            raise typer.Exit(1)
        _write_json(cfg, page_json)
    console.print(
        "[green]Page configuration updated in "
        f"project '{project}'.[/]"
    )


# ---------------------------------------------------------------------------
# Style commands
# ---------------------------------------------------------------------------


@style_app.command("list")
@error_handler
def style_list(
    project: Annotated[str, typer.Argument(help="Project name")],
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
    fmt: FormatOpt = "table",
) -> None:
    """List all Perspective style classes in a project."""
    with (
        make_client(gateway, url, token) as client,
        _open_project_zip(client, project) as zf,
    ):
        styles = _list_entries(
            zf, "style-classes", "style.json",
        )
    if fmt in ("json", "yaml"):
        output(styles, fmt)
    else:
        from ignition_cli.output.tables import make_table

        rows = [[s] for s in styles]
        console.print(
            make_table(
                f"Style Classes: {project}", ["Name"], rows,
            )
        )


@style_app.command("show")
@error_handler
def style_show(
    project: Annotated[str, typer.Argument(help="Project name")],
    style_name: Annotated[
        str, typer.Argument(help="Style class name"),
    ],
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
    fmt: FormatOpt = "json",
) -> None:
    """Show a Perspective style class definition."""
    inner = (
        f"{PERSPECTIVE}/style-classes/{style_name}/style.json"
    )
    with (
        make_client(gateway, url, token) as client,
        _open_project_zip(client, project) as zf,
    ):
        data = _read_json(zf, inner)
    output(data, fmt, kv=True, title=f"Style: {style_name}")


@style_app.command("create")
@error_handler
def style_create(
    project: Annotated[str, typer.Argument(help="Project name")],
    style_name: Annotated[
        str, typer.Argument(help="Style class name"),
    ],
    json_data: Annotated[
        str,
        typer.Option(
            "--json", "-j",
            help="Style JSON string or @file path",
        ),
    ],
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
) -> None:
    """Create a new Perspective style class."""
    style_json = _parse_json_input(json_data)
    with (
        make_client(gateway, url, token) as client,
        _modify_project(client, project) as work_dir,
    ):
        sdir = (
            work_dir / PERSPECTIVE
            / "style-classes" / style_name
        )
        if (sdir / "style.json").exists():
            console.print(
                f"[red]Style class '{style_name}' "
                "already exists. Use "
                "'perspective style update' instead.[/]"
            )
            raise typer.Exit(1)
        _write_json(sdir / "style.json", style_json)
        _write_json(
            sdir / "resource.json",
            _make_resource_json(["style.json"]),
        )
    console.print(
        f"[green]Style class '{style_name}' created in "
        f"project '{project}'.[/]"
    )


@style_app.command("update")
@error_handler
def style_update(
    project: Annotated[str, typer.Argument(help="Project name")],
    style_name: Annotated[
        str, typer.Argument(help="Style class name"),
    ],
    json_data: Annotated[
        str,
        typer.Option(
            "--json", "-j",
            help="Style JSON string or @file path",
        ),
    ],
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
) -> None:
    """Update an existing Perspective style class."""
    style_json = _parse_json_input(json_data)
    with (
        make_client(gateway, url, token) as client,
        _modify_project(client, project) as work_dir,
    ):
        sf = (
            work_dir / PERSPECTIVE
            / "style-classes" / style_name / "style.json"
        )
        if not sf.exists():
            console.print(
                f"[red]Style class '{style_name}' "
                "not found.[/]"
            )
            raise typer.Exit(1)
        _write_json(sf, style_json)
    console.print(
        f"[green]Style class '{style_name}' updated in "
        f"project '{project}'.[/]"
    )


@style_app.command("delete")
@error_handler
def style_delete(
    project: Annotated[str, typer.Argument(help="Project name")],
    style_name: Annotated[
        str, typer.Argument(help="Style class name to delete"),
    ],
    force: Annotated[
        bool,
        typer.Option("--force", help="Skip confirmation"),
    ] = False,
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
) -> None:
    """Delete a Perspective style class from a project."""
    if not force:
        from rich.prompt import Confirm

        if not Confirm.ask(
            f"Delete style class '{style_name}' "
            f"from project '{project}'?"
        ):
            console.print("Cancelled.")
            return
    with (
        make_client(gateway, url, token) as client,
        _modify_project(client, project) as work_dir,
    ):
        sdir = (
            work_dir / PERSPECTIVE
            / "style-classes" / style_name
        )
        if not sdir.exists():
            console.print(
                f"[red]Style class '{style_name}' "
                "not found.[/]"
            )
            raise typer.Exit(1)
        shutil.rmtree(sdir)
    console.print(
        f"[green]Style class '{style_name}' deleted from "
        f"project '{project}'.[/]"
    )


# ---------------------------------------------------------------------------
# Session commands
# ---------------------------------------------------------------------------


@session_app.command("show")
@error_handler
def session_show(
    project: Annotated[str, typer.Argument(help="Project name")],
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
    fmt: FormatOpt = "json",
) -> None:
    """Show the Perspective session properties."""
    inner = f"{PERSPECTIVE}/session-props/props.json"
    with (
        make_client(gateway, url, token) as client,
        _open_project_zip(client, project) as zf,
    ):
        data = _read_json(zf, inner)
    output(data, fmt, kv=True, title=f"Session Props: {project}")


@session_app.command("update")
@error_handler
def session_update(
    project: Annotated[str, typer.Argument(help="Project name")],
    json_data: Annotated[
        str,
        typer.Option(
            "--json", "-j",
            help="Session props JSON string or @file path",
        ),
    ],
    gateway: GatewayOpt = None,
    url: UrlOpt = None,
    token: TokenOpt = None,
) -> None:
    """Update the Perspective session properties."""
    session_json = _parse_json_input(json_data)
    with (
        make_client(gateway, url, token) as client,
        _modify_project(client, project) as work_dir,
    ):
        pf = (
            work_dir / PERSPECTIVE
            / "session-props" / "props.json"
        )
        if not pf.exists():
            console.print(
                "[red]Session properties not found "
                "in project.[/]"
            )
            raise typer.Exit(1)
        _write_json(pf, session_json)
    console.print(
        "[green]Session properties updated in "
        f"project '{project}'.[/]"
    )
