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
        result = runner.invoke(app, [
            "tag", "browse", "-f", "json",
            "--url", GW, "--token", "k:s",
        ])
        assert result.exit_code == 0
        assert "T1" in result.output

    @respx.mock
    def test_read(self):
        respx.post(f"{BASE}/tags/read").mock(
            return_value=httpx.Response(200, json=[
                {"path": "Tag1", "value": 42,
                 "quality": "Good",
                 "timestamp": "2024-01-01T00:00:00Z"},
            ])
        )
        result = runner.invoke(app, [
            "tag", "read", "Tag1",
            "--url", GW, "--token", "k:s",
        ])
        assert result.exit_code == 0
        assert "42" in result.output
        assert "Warning" in result.output

    @respx.mock
    def test_write(self):
        respx.post(f"{BASE}/tags/write").mock(
            return_value=httpx.Response(200, json={"success": True})
        )
        result = runner.invoke(app, [
            "tag", "write", "Tag1", "100",
            "--url", GW, "--token", "k:s",
        ])
        assert result.exit_code == 0
        assert "Wrote" in result.output
        assert "Warning" in result.output

    @respx.mock
    def test_export(self):
        respx.get(f"{BASE}/tags/export").mock(
            return_value=httpx.Response(200, json={"tags": [{"name": "T1"}]})
        )
        result = runner.invoke(app, ["tag", "export", "--url", GW, "--token", "k:s"])
        assert result.exit_code == 0
        assert "T1" in result.output

    @respx.mock
    def test_export_csv(self):
        respx.get(f"{BASE}/tags/export").mock(
            return_value=httpx.Response(200, json={
                "tags": [
                    {"name": "Folder1", "tagType": "Folder", "tags": [
                        {"name": "Tag1", "tagType": "AtomicTag", "dataType": "Int4"},
                    ]},
                    {"name": "Tag2", "tagType": "AtomicTag", "dataType": "Float8",
                     "value": 3.14, "tooltip": "A float tag"},
                ],
            })
        )
        result = runner.invoke(app, [
            "tag", "export", "-f", "csv",
            "--url", GW, "--token", "k:s",
        ])
        assert result.exit_code == 0
        lines = [line for line in result.output.splitlines() if line.strip()]
        assert lines[0] == "path,tagType,dataType,value,tooltip"
        assert "Folder1,Folder" in lines[1]
        assert "Folder1/Tag1,AtomicTag,Int4" in lines[2]
        assert "Tag2,AtomicTag,Float8,3.14,A float tag" in lines[3]

    @respx.mock
    def test_export_csv_to_file(self, tmp_path):
        respx.get(f"{BASE}/tags/export").mock(
            return_value=httpx.Response(200, json={
                "tags": [
                    {"name": "Tag1", "tagType": "AtomicTag", "dataType": "Boolean"},
                ],
            })
        )
        out = str(tmp_path / "tags.csv")
        result = runner.invoke(app, [
            "tag", "export", "-f", "csv", "-o", out,
            "--url", GW, "--token", "k:s",
        ])
        assert result.exit_code == 0
        assert "exported" in result.output
        content = (tmp_path / "tags.csv").read_text()
        assert "path,tagType,dataType,value,tooltip" in content
        assert "Tag1,AtomicTag,Boolean" in content

    def test_export_invalid_format(self):
        result = runner.invoke(app, [
            "tag", "export", "-f", "xml",
            "--url", GW, "--token", "k:s",
        ])
        assert result.exit_code == 1
        assert "Invalid format" in result.output

    @respx.mock
    def test_export_to_file(self, tmp_path):
        respx.get(f"{BASE}/tags/export").mock(
            return_value=httpx.Response(200, json={"tags": [{"name": "T1"}]})
        )
        out = str(tmp_path / "tags.json")
        result = runner.invoke(app, [
            "tag", "export", "-o", out,
            "--url", GW, "--token", "k:s",
        ])
        assert result.exit_code == 0
        assert "exported" in result.output

    @respx.mock
    def test_import(self, tmp_path):
        tag_file = tmp_path / "tags.json"
        tag_file.write_text(json.dumps({"tags": [{"name": "T1"}]}))
        respx.post(f"{BASE}/tags/import").mock(
            return_value=httpx.Response(200, json={"success": True})
        )
        result = runner.invoke(app, [
            "tag", "import", str(tag_file),
            "--url", GW, "--token", "k:s",
        ])
        assert result.exit_code == 0
        assert "imported" in result.output

    @respx.mock
    def test_read_webdev(self):
        respx.get(f"{GW}/system/webdev/mcp_connector/tags/read").mock(
            return_value=httpx.Response(200, json={
                "tags": [
                    {"path": "Tag1", "value": 42,
                     "quality": "Good",
                     "timestamp": "2024-01-01T00:00:00Z"},
                ],
            })
        )
        result = runner.invoke(app, [
            "tag", "read", "Tag1",
            "--webdev-project", "mcp_connector",
            "--url", GW, "--token", "k:s",
        ])
        assert result.exit_code == 0
        assert "42" in result.output
        assert "Warning" not in result.output

    @respx.mock
    def test_write_webdev(self):
        respx.post(f"{GW}/system/webdev/mcp_connector/tags/write").mock(
            return_value=httpx.Response(200, json={
                "quality": "Good",
            })
        )
        result = runner.invoke(app, [
            "tag", "write", "Tag1", "100",
            "--webdev-project", "mcp_connector",
            "--url", GW, "--token", "k:s",
        ])
        assert result.exit_code == 0
        assert "Wrote" in result.output
        assert "quality: Good" in result.output
        assert "Warning" not in result.output

    @respx.mock
    def test_read_webdev_from_profile(self, tmp_path):
        """Profile webdev_project is used when --webdev-project is not passed."""
        from unittest.mock import patch

        import tomli_w

        cfg = tmp_path / "config.toml"
        cfg.write_text(tomli_w.dumps({
            "default_profile": "dev",
            "profiles": {
                "dev": {
                    "url": GW,
                    "token": "k:s",
                    "webdev_project": "mcp_connector",
                },
            },
        }))
        respx.get(f"{GW}/system/webdev/mcp_connector/tags/read").mock(
            return_value=httpx.Response(200, json={
                "tags": [
                    {"path": "Sensor1", "value": 99.5,
                     "quality": "Good",
                     "timestamp": "2024-06-15T12:00:00Z"},
                ],
            })
        )

        with patch("ignition_cli.commands._common.ConfigManager") as MockCM:
            from ignition_cli.config.manager import ConfigManager as RealCM
            MockCM.return_value = RealCM(config_path=cfg)
            result = runner.invoke(app, [
                "tag", "read", "Sensor1",
                "--gateway", "dev",
            ])
        assert result.exit_code == 0
        assert "99.5" in result.output
        assert "Warning" not in result.output

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
