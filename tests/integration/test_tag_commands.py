"""Integration tests for tag commands."""

from __future__ import annotations

import json

import httpx
import respx
from typer.testing import CliRunner

from ignition_cli.app import app

runner = CliRunner()
GW = "https://gw:8043"
BASE = f"{GW}/data/api/v1"


class TestTagCommands:
    @respx.mock
    def test_browse(self):
        respx.get(f"{BASE}/tags/export").mock(
            return_value=httpx.Response(200, json=[
                {"name": "Folder1", "tagType": "Folder"},
                {"name": "Tag1", "tagType": "AtomicTag", "dataType": "Int4"},
            ])
        )
        result = runner.invoke(app, ["tag", "browse", "--url", GW, "--token", "k:s"])
        assert result.exit_code == 0
        assert "Folder1" in result.output
        assert "Tag1" in result.output

    @respx.mock
    def test_browse_json(self):
        respx.get(f"{BASE}/tags/export").mock(
            return_value=httpx.Response(200, json=[{"name": "T1"}])
        )
        result = runner.invoke(app, ["tag", "browse", "-f", "json", "--url", GW, "--token", "k:s"])
        assert result.exit_code == 0
        assert "T1" in result.output

    @respx.mock
    def test_read(self):
        respx.post(f"{BASE}/tags/read").mock(
            return_value=httpx.Response(200, json=[
                {"path": "Tag1", "value": 42, "quality": "Good", "timestamp": "2024-01-01T00:00:00Z"},
            ])
        )
        result = runner.invoke(app, ["tag", "read", "Tag1", "--url", GW, "--token", "k:s"])
        assert result.exit_code == 0
        assert "42" in result.output

    @respx.mock
    def test_write(self):
        respx.post(f"{BASE}/tags/write").mock(
            return_value=httpx.Response(200, json={"success": True})
        )
        result = runner.invoke(app, ["tag", "write", "Tag1", "100", "--url", GW, "--token", "k:s"])
        assert result.exit_code == 0
        assert "Wrote" in result.output

    @respx.mock
    def test_export(self):
        respx.get(f"{BASE}/tags/export").mock(
            return_value=httpx.Response(200, json={"tags": [{"name": "T1"}]})
        )
        result = runner.invoke(app, ["tag", "export", "--url", GW, "--token", "k:s"])
        assert result.exit_code == 0
        assert "T1" in result.output

    @respx.mock
    def test_export_to_file(self, tmp_path):
        respx.get(f"{BASE}/tags/export").mock(
            return_value=httpx.Response(200, json={"tags": [{"name": "T1"}]})
        )
        out = str(tmp_path / "tags.json")
        result = runner.invoke(app, ["tag", "export", "-o", out, "--url", GW, "--token", "k:s"])
        assert result.exit_code == 0
        assert "exported" in result.output

    @respx.mock
    def test_import(self, tmp_path):
        tag_file = tmp_path / "tags.json"
        tag_file.write_text(json.dumps({"tags": [{"name": "T1"}]}))
        respx.post(f"{BASE}/tags/import").mock(
            return_value=httpx.Response(200, json={"success": True})
        )
        result = runner.invoke(app, ["tag", "import", str(tag_file), "--url", GW, "--token", "k:s"])
        assert result.exit_code == 0
        assert "imported" in result.output

    @respx.mock
    def test_providers(self):
        respx.get(f"{BASE}/resources/list/ignition/tag-provider").mock(
            return_value=httpx.Response(200, json=[
                {"name": "default", "type": "internal", "state": "Running"},
            ])
        )
        result = runner.invoke(app, ["tag", "providers", "--url", GW, "--token", "k:s"])
        assert result.exit_code == 0
        assert "default" in result.output
