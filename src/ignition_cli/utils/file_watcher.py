"""File watcher for project watch command — syncs local changes to gateway."""

from __future__ import annotations

from pathlib import Path

import httpx
from rich.console import Console

from ignition_cli.client.errors import IgnitionCLIError
from ignition_cli.config.models import GatewayProfile


def watch_and_sync(
    profile: GatewayProfile,
    project_name: str,
    watch_dir: Path,
    console: Console,
) -> None:
    """Watch a directory for changes and sync to the gateway project."""
    try:
        from watchfiles import Change, watch
    except ImportError:
        console.print(
            "[red]watchfiles is required for project watch. "
            "Install it with: pip install 'ignition-cli[watch]'[/]"
        )
        raise SystemExit(1) from None

    from ignition_cli.client.gateway import GatewayClient

    with GatewayClient(profile) as client:
        for changes in watch(watch_dir):
            for change_type, changed_path in changes:
                rel_path = Path(changed_path).relative_to(watch_dir)
                change_name = {
                    Change.added: "added",
                    Change.modified: "modified",
                    Change.deleted: "deleted",
                }.get(change_type, str(change_type))

                console.print(f"  [dim]{change_name}:[/] {rel_path}")

                if change_type == Change.deleted:
                    try:
                        client.delete(f"/projects/{project_name}/resources/{rel_path}")
                    except (httpx.HTTPError, IgnitionCLIError) as exc:
                        console.print(
                            "  [yellow]Warning: could not delete"
                            f" remote resource: {exc}[/]"
                        )
                else:
                    file_path = Path(changed_path)
                    if file_path.is_file():
                        try:
                            client.put(
                                f"/projects/{project_name}/resources/{rel_path}",
                                content=file_path.read_bytes(),
                            )
                        except (httpx.HTTPError, IgnitionCLIError) as exc:
                            console.print(
                                "  [yellow]Warning: could not"
                                f" sync resource: {exc}[/]"
                            )
