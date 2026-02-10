"""Tests for output formatting."""

from io import StringIO

from rich.console import Console

from ignition_cli.output.tables import kv_table, make_table


class TestTables:
    def test_make_table(self):
        table = make_table("Test", ["A", "B"], [["1", "2"], ["3", "4"]])
        buf = StringIO()
        console = Console(file=buf, force_terminal=True, width=80)
        console.print(table)
        out = buf.getvalue()
        assert "Test" in out
        assert "1" in out
        assert "4" in out

    def test_kv_table(self):
        table = kv_table({"key1": "val1", "key2": "val2"}, title="KV")
        buf = StringIO()
        console = Console(file=buf, force_terminal=True, width=80)
        console.print(table)
        out = buf.getvalue()
        assert "key1" in out
        assert "val1" in out

    def test_kv_table_none_values(self):
        table = kv_table({"key": None})
        buf = StringIO()
        console = Console(file=buf, force_terminal=True, width=80)
        console.print(table)
        out = buf.getvalue()
        assert "key" in out
