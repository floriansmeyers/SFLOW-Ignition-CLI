"""Rich table rendering helpers."""

from __future__ import annotations

from typing import Any, Sequence

from rich.table import Table


def make_table(
    title: str | None,
    columns: Sequence[str],
    rows: Sequence[Sequence[Any]],
    *,
    show_lines: bool = False,
) -> Table:
    """Build a Rich Table from column headers and row data."""
    table = Table(title=title, show_lines=show_lines)
    for col in columns:
        table.add_column(col, no_wrap=False)
    for row in rows:
        table.add_row(*(str(cell) if cell is not None else "" for cell in row))
    return table


def kv_table(data: dict[str, Any], *, title: str | None = None) -> Table:
    """Render a key-value dict as a two-column table."""
    table = Table(title=title, show_header=False, show_lines=False)
    table.add_column("Key", style="bold cyan", no_wrap=True)
    table.add_column("Value")
    for key, value in data.items():
        table.add_row(key, str(value) if value is not None else "")
    return table
