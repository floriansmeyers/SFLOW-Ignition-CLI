"""Tests for output formatting."""

from __future__ import annotations

from io import StringIO
from unittest.mock import patch

from rich.console import Console

from ignition_cli.output.formatter import output, output_csv


class TestOutputJson:
    def test_dict(self, capsys):
        output({"key": "val"}, "json")
        # output_json uses console.print_json, check it doesn't crash

    def test_list(self, capsys):
        output([1, 2, 3], "json")

    def test_pydantic_model(self):
        from ignition_cli.models.mode import DeploymentMode

        m = DeploymentMode(name="dev", title="Development")
        output(m, "json")


class TestOutputYaml:
    def test_dict(self, capsys):
        output({"key": "val"}, "yaml")

    def test_list(self, capsys):
        output([{"a": 1}], "yaml")


class TestOutputCsv:
    def test_csv_output(self):
        buf = StringIO()
        console = Console(file=buf, force_terminal=False, width=200)
        with patch("ignition_cli.output.formatter.console", console):
            output_csv(["Name", "Value"], [["a", "1"], ["b", "2"]])
        out = buf.getvalue()
        assert "Name,Value" in out
        assert "a,1" in out

    def test_csv_via_output(self):
        output(
            {"items": []},
            "csv",
            columns=["A", "B"],
            rows=[["1", "2"]],
        )


class TestOutputTable:
    def test_kv_table(self, capsys):
        output({"key": "val"}, "table", kv=True, title="Test")

    def test_columns_rows(self, capsys):
        output(
            [{"a": 1}],
            "table",
            columns=["A", "B"],
            rows=[["1", "2"]],
            title="Test",
        )

    def test_fallback_dict_as_kv(self, capsys):
        output({"k": "v"}, "table")

    def test_fallback_other(self, capsys):
        output("plain text", "table")


class TestEdgeCases:
    def test_empty_dict(self):
        output({}, "json")

    def test_empty_list(self):
        output([], "json")

    def test_none_values_in_dict(self):
        output({"key": None, "other": "val"}, "table", kv=True)
