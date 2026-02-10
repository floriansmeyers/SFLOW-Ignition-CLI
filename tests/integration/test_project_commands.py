"""Integration tests for project commands."""

from __future__ import annotations

import httpx
import respx
from typer.testing import CliRunner

from ignition_cli.app import app

runner = CliRunner()
GW = "https://gw:8043"
BASE = f"{GW}/data/api/v1"


class TestProjectCommands:
    @respx.mock
    def test_list_projects(self):
        respx.get(f"{BASE}/projects/list").mock(
            return_value=httpx.Response(200, json=[
                {"name": "MyProject", "title": "My Project", "enabled": True, "state": "Published"},
                {"name": "Dev", "title": "Dev Project", "enabled": False, "state": "Draft"},
            ])
        )
        result = runner.invoke(app, ["project", "list", "--url", GW, "--token", "k:s"])
        assert result.exit_code == 0
        assert "MyProject" in result.output
        assert "Dev" in result.output

    @respx.mock
    def test_list_with_filter(self):
        respx.get(f"{BASE}/projects/list").mock(
            return_value=httpx.Response(200, json=[
                {"name": "MyProject", "title": "X"},
                {"name": "Other", "title": "Y"},
            ])
        )
        result = runner.invoke(app, ["project", "list", "--filter", "My", "--url", GW, "--token", "k:s"])
        assert result.exit_code == 0
        assert "MyProject" in result.output

    @respx.mock
    def test_show_project(self):
        respx.get(f"{BASE}/projects/find/MyProject").mock(
            return_value=httpx.Response(200, json={"name": "MyProject", "title": "My Project", "enabled": True})
        )
        result = runner.invoke(app, ["project", "show", "MyProject", "--url", GW, "--token", "k:s"])
        assert result.exit_code == 0
        assert "MyProject" in result.output

    @respx.mock
    def test_create_project(self):
        respx.post(f"{BASE}/projects").mock(return_value=httpx.Response(201, json={}))
        result = runner.invoke(app, ["project", "create", "NewProj", "--url", GW, "--token", "k:s"])
        assert result.exit_code == 0
        assert "created" in result.output

    @respx.mock
    def test_delete_project(self):
        respx.delete(f"{BASE}/projects/OldProj").mock(return_value=httpx.Response(204))
        result = runner.invoke(app, ["project", "delete", "OldProj", "--force", "--url", GW, "--token", "k:s"])
        assert result.exit_code == 0
        assert "deleted" in result.output

    @respx.mock
    def test_export_project(self, tmp_path):
        content = b"PK\x03\x04fake-zip-content"
        respx.get(f"{BASE}/projects/export/MyProject").mock(
            return_value=httpx.Response(200, content=content)
        )
        out_file = str(tmp_path / "export.zip")
        result = runner.invoke(app, [
            "project", "export", "MyProject", "-o", out_file, "--url", GW, "--token", "k:s"
        ])
        assert result.exit_code == 0
        assert "exported" in result.output

    @respx.mock
    def test_import_project(self, tmp_path):
        import_file = tmp_path / "project.zip"
        import_file.write_bytes(b"PK\x03\x04fake-zip")
        respx.post(f"{BASE}/projects/import/project").mock(return_value=httpx.Response(200, json={}))
        result = runner.invoke(app, [
            "project", "import", str(import_file), "--url", GW, "--token", "k:s"
        ])
        assert result.exit_code == 0
        assert "imported" in result.output

    @respx.mock
    def test_import_project_with_name(self, tmp_path):
        import_file = tmp_path / "project.zip"
        import_file.write_bytes(b"PK\x03\x04fake-zip")
        respx.post(f"{BASE}/projects/import/CustomName").mock(return_value=httpx.Response(200, json={}))
        result = runner.invoke(app, [
            "project", "import", str(import_file), "--name", "CustomName", "--url", GW, "--token", "k:s"
        ])
        assert result.exit_code == 0
        assert "imported" in result.output

    @respx.mock
    def test_resources(self):
        respx.get(f"{BASE}/projects/find/MyProject").mock(
            return_value=httpx.Response(200, json={
                "name": "MyProject",
                "resources": [
                    {"name": "view.json", "type": "view", "path": "/views/main", "scope": "A"},
                ],
            })
        )
        result = runner.invoke(app, ["project", "resources", "MyProject", "--url", GW, "--token", "k:s"])
        assert result.exit_code == 0
        assert "view.json" in result.output

    @respx.mock
    def test_list_json_format(self):
        respx.get(f"{BASE}/projects/list").mock(
            return_value=httpx.Response(200, json=[{"name": "P1"}])
        )
        result = runner.invoke(app, ["project", "list", "-f", "json", "--url", GW, "--token", "k:s"])
        assert result.exit_code == 0
        assert "P1" in result.output


class TestProjectCopyRename:
    @respx.mock
    def test_copy_project(self):
        respx.post(f"{BASE}/projects/copy").mock(
            return_value=httpx.Response(200, json={})
        )
        result = runner.invoke(app, [
            "project", "copy", "MyApp", "--name", "MyApp-Copy",
            "--url", GW, "--token", "k:s",
        ])
        assert result.exit_code == 0
        assert "copied" in result.output
        assert "MyApp-Copy" in result.output

    @respx.mock
    def test_rename_project(self):
        respx.post(f"{BASE}/projects/rename/OldName").mock(
            return_value=httpx.Response(200, json={})
        )
        result = runner.invoke(app, [
            "project", "rename", "OldName", "--name", "NewName",
            "--url", GW, "--token", "k:s",
        ])
        assert result.exit_code == 0
        assert "renamed" in result.output
        assert "NewName" in result.output
