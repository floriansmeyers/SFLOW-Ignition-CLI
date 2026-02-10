"""Project diff utilities — colored unified diff between gateway project data."""

from __future__ import annotations

import difflib
import json

from rich.console import Console
from rich.syntax import Syntax


def diff_projects(
    name: str,
    source_data: dict,
    target_data: dict,
    console: Console,
) -> None:
    """Show a colored diff between project data from two gateways."""
    source_json = json.dumps(source_data, indent=2, sort_keys=True).splitlines(keepends=True)
    target_json = json.dumps(target_data, indent=2, sort_keys=True).splitlines(keepends=True)

    diff_lines = list(difflib.unified_diff(
        source_json,
        target_json,
        fromfile=f"{name} (source)",
        tofile=f"{name} (target)",
        lineterm="",
    ))

    if not diff_lines:
        console.print(f"[green]No differences found for project '{name}'.[/]")
        return

    diff_text = "\n".join(line.rstrip() for line in diff_lines)
    syntax = Syntax(diff_text, "diff", theme="monokai", line_numbers=True)
    console.print(syntax)
