"""Output dispatcher — renders data in table, JSON, YAML, or CSV format."""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Sequence
from typing import Any

from rich.console import Console

from ignition_cli.output.tables import kv_table, make_table

console = Console()


def output_json(data: Any) -> None:
    """Print data as formatted JSON."""
    if hasattr(data, "model_dump"):
        data = data.model_dump(mode="json")
    console.print_json(json.dumps(data, indent=2, default=str))


def output_yaml(data: Any) -> None:
    """Print data as YAML."""
    import yaml

    if hasattr(data, "model_dump"):
        data = data.model_dump(mode="json")
    console.print(yaml.dump(data, default_flow_style=False, sort_keys=False), end="")


def output_csv(columns: Sequence[str], rows: Sequence[Sequence[Any]]) -> None:
    """Print data as CSV."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(columns)
    writer.writerows(
        [[str(v) if v is not None else "" for v in row] for row in rows]
    )
    console.print(buf.getvalue(), end="")


def output_table(
    data: Any,
    *,
    columns: Sequence[str] | None = None,
    rows: Sequence[Sequence[Any]] | None = None,
    title: str | None = None,
    kv: bool = False,
) -> None:
    """Print data as a Rich table."""
    if kv and isinstance(data, dict):
        console.print(kv_table(data, title=title))
    elif columns and rows is not None:
        console.print(make_table(title, columns, rows))
    elif isinstance(data, dict):
        console.print(kv_table(data, title=title))
    else:
        console.print(data)


def output(
    data: Any,
    fmt: str = "table",
    *,
    columns: Sequence[str] | None = None,
    rows: Sequence[Sequence[Any]] | None = None,
    title: str | None = None,
    kv: bool = False,
) -> None:
    """Dispatch output to the appropriate formatter."""
    if fmt == "json":
        output_json(data)
    elif fmt == "yaml":
        output_yaml(data)
    elif fmt == "csv":
        if columns and rows is not None:
            output_csv(columns, rows)
        else:
            output_json(data)
    else:
        output_table(data, columns=columns, rows=rows, title=title, kv=kv)
