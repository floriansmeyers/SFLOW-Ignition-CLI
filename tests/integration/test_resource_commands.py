"""Integration tests for resource commands — CRUD, upload, download, show."""

from __future__ import annotations

import json

import httpx
import respx
from typer.testing import CliRunner

from ignition_cli.app import app

runner = CliRunner()

BASE = "https://gw:8043/data/api/v1"
COMMON_OPTS = ["--url", "https://gw:8043", "--token", "k:s"]


class TestResourceList:
    @respx.mock
    def test_list_resources(self):
        respx.get(f"{BASE}/resources/list/ignition/database-connection").mock(
            return_value=httpx.Response(200, json=[
                {"name": "db1",
                 "type": "ignition/database-connection",
                 "state": "Running"},
            ])
        )
        result = runner.invoke(app, [
            "resource", "list", "ignition/database-connection", *COMMON_OPTS,
        ])
        assert result.exit_code == 0
        assert "db1" in result.output

    @respx.mock
    def test_list_paginated(self):
        respx.get(f"{BASE}/resources/list/ignition/database-connection").mock(
            return_value=httpx.Response(200, json={
                "items": [{"name": "db1"}],
                "metadata": {"total": 1},
            })
        )
        result = runner.invoke(app, [
            "resource", "list", "ignition/database-connection", *COMMON_OPTS,
        ])
        assert result.exit_code == 0
        assert "db1" in result.output

    def test_list_invalid_type(self):
        result = runner.invoke(app, [
            "resource", "list", "invalid-no-slash", *COMMON_OPTS,
        ])
        assert result.exit_code != 0


class TestResourceCreate:
    @respx.mock
    def test_create_basic(self):
        respx.post(f"{BASE}/resources/ignition/database-connection").mock(
            return_value=httpx.Response(201, json={})
        )
        result = runner.invoke(app, [
            "resource", "create", "ignition/database-connection",
            "--name", "new-db", *COMMON_OPTS,
        ])
        assert result.exit_code == 0
        assert "created" in result.output

    @respx.mock
    def test_create_with_collection(self):
        route = respx.post(f"{BASE}/resources/ignition/database-connection").mock(
            return_value=httpx.Response(201, json={})
        )
        result = runner.invoke(app, [
            "resource", "create", "ignition/database-connection",
            "--name", "new-db", "--collection", "staging",
            *COMMON_OPTS,
        ])
        assert result.exit_code == 0
        assert "created" in result.output
        body = json.loads(route.calls.last.request.content)
        assert body[0]["collection"] == "staging"


class TestResourceUpdate:
    @respx.mock
    def test_update_auto_fetches_signature(self):
        respx.get(f"{BASE}/resources/find/ignition/database-connection/db1").mock(
            return_value=httpx.Response(200, json={
                "name": "db1", "signature": "sig456",
            })
        )
        respx.put(f"{BASE}/resources/ignition/database-connection").mock(
            return_value=httpx.Response(200, json={})
        )
        result = runner.invoke(app, [
            "resource", "update", "ignition/database-connection", "db1",
            "--config", '{"description":"updated"}', *COMMON_OPTS,
        ])
        assert result.exit_code == 0
        assert "updated" in result.output

    @respx.mock
    def test_update_with_collection(self):
        # With --collection, signature fetch should include collection param
        respx.get(
            url__regex=r".*/resources/find/ignition/database-connection/db1.*",
        ).mock(
            return_value=httpx.Response(200, json={
                "name": "db1", "signature": "sig456",
            })
        )
        route = respx.put(f"{BASE}/resources/ignition/database-connection").mock(
            return_value=httpx.Response(200, json={})
        )
        result = runner.invoke(app, [
            "resource", "update", "ignition/database-connection", "db1",
            "--config", '{"description":"updated"}',
            "--collection", "staging",
            *COMMON_OPTS,
        ])
        assert result.exit_code == 0
        assert "updated" in result.output
        body = json.loads(route.calls.last.request.content)
        assert body[0]["collection"] == "staging"

    @respx.mock
    def test_update_no_signature_found(self):
        respx.get(f"{BASE}/resources/find/ignition/database-connection/db1").mock(
            return_value=httpx.Response(200, json={"name": "db1"})
        )
        result = runner.invoke(app, [
            "resource", "update", "ignition/database-connection", "db1",
            "--config", '{"description":"updated"}', *COMMON_OPTS,
        ])
        assert result.exit_code != 0
        assert "signature" in result.output.lower()


class TestResourceDelete:
    @respx.mock
    def test_delete_with_auto_signature(self):
        respx.get(f"{BASE}/resources/find/ignition/database-connection/db1").mock(
            return_value=httpx.Response(200, json={
                "name": "db1", "signature": "sig123",
            })
        )
        respx.delete(f"{BASE}/resources/ignition/database-connection/db1/sig123").mock(
            return_value=httpx.Response(200, json={})
        )
        result = runner.invoke(app, [
            "resource", "delete", "ignition/database-connection", "db1",
            "--force", *COMMON_OPTS,
        ])
        assert result.exit_code == 0
        assert "deleted" in result.output

    @respx.mock
    def test_delete_with_explicit_signature(self):
        respx.delete(f"{BASE}/resources/ignition/database-connection/db1/mysig").mock(
            return_value=httpx.Response(200, json={})
        )
        result = runner.invoke(app, [
            "resource", "delete", "ignition/database-connection", "db1",
            "--force", "--signature", "mysig", *COMMON_OPTS,
        ])
        assert result.exit_code == 0
        assert "deleted" in result.output

    @respx.mock
    def test_delete_no_signature_found(self):
        respx.get(f"{BASE}/resources/find/ignition/database-connection/db1").mock(
            return_value=httpx.Response(200, json={"name": "db1"})
        )
        result = runner.invoke(app, [
            "resource", "delete", "ignition/database-connection", "db1",
            "--force", *COMMON_OPTS,
        ])
        assert result.exit_code != 0
        assert "signature" in result.output.lower()

    @respx.mock
    def test_delete_with_collection(self):
        """Delete with --collection passes collection and confirm params."""
        respx.get(
            url__regex=r".*/resources/find/ignition/database-connection/db1.*",
        ).mock(
            return_value=httpx.Response(200, json={
                "name": "db1", "signature": "mode-sig-999",
            })
        )
        route = respx.delete(
            url__regex=r".*/resources/ignition/database-connection/db1/mode-sig-999.*",
        ).mock(
            return_value=httpx.Response(200, json={})
        )
        result = runner.invoke(app, [
            "resource", "delete", "ignition/database-connection", "db1",
            "--force", "--collection", "staging",
            *COMMON_OPTS,
        ])
        assert result.exit_code == 0
        assert "deleted" in result.output
        # Verify collection and confirm params were sent
        req_url = str(route.calls.last.request.url)
        assert "collection=staging" in req_url
        assert "confirm=true" in req_url


class TestResourceUpload:
    @respx.mock
    def test_upload_with_explicit_signature(self, tmp_path):
        test_file = tmp_path / "font.woff2"
        test_file.write_bytes(b"\x00\x01binary-content")

        route = f"{BASE}/resources/datafile/ignition/theme/my-theme/font.woff2"
        respx.put(route).mock(
            return_value=httpx.Response(200, json={"status": "ok"})
        )
        result = runner.invoke(app, [
            "resource", "upload", "ignition/theme",
            "my-theme", str(test_file),
            "--signature", "abc123",
            *COMMON_OPTS,
        ])
        assert result.exit_code == 0
        assert "Uploaded" in result.output
        assert "font.woff2" in result.output

    @respx.mock
    def test_upload_auto_fetches_signature(self, tmp_path):
        test_file = tmp_path / "style.css"
        test_file.write_bytes(b"body { color: red; }")

        find_url = f"{BASE}/resources/find/ignition/theme/my-theme"
        respx.get(find_url).mock(
            return_value=httpx.Response(200, json={
                "name": "my-theme", "signature": "auto-sig",
            })
        )
        upload_url = (
            f"{BASE}/resources/datafile"
            "/ignition/theme/my-theme/style.css"
        )
        respx.put(upload_url).mock(
            return_value=httpx.Response(200, json={"status": "ok"})
        )
        result = runner.invoke(app, [
            "resource", "upload", "ignition/theme",
            "my-theme", str(test_file),
            *COMMON_OPTS,
        ])
        assert result.exit_code == 0
        assert "Uploaded" in result.output

    def test_upload_file_not_found(self):
        result = runner.invoke(app, [
            "resource", "upload", "ignition/theme", "my-theme",
            "/nonexistent/file.woff2",
            "--signature", "abc", *COMMON_OPTS,
        ])
        assert result.exit_code != 0
        assert "not found" in result.output.lower()

    @respx.mock
    def test_upload_no_signature_on_resource(self, tmp_path):
        test_file = tmp_path / "icon.png"
        test_file.write_bytes(b"\x89PNG")

        find_url = f"{BASE}/resources/find/ignition/theme/my-theme"
        respx.get(find_url).mock(
            return_value=httpx.Response(
                200, json={"name": "my-theme"},
            )
        )
        result = runner.invoke(app, [
            "resource", "upload", "ignition/theme",
            "my-theme", str(test_file),
            *COMMON_OPTS,
        ])
        assert result.exit_code != 0
        assert "signature" in result.output.lower()

    @respx.mock
    def test_upload_custom_filename(self, tmp_path):
        test_file = tmp_path / "local-name.css"
        test_file.write_bytes(b"/* css */")

        route = (
            f"{BASE}/resources/datafile"
            "/ignition/theme/my-theme/remote-name.css"
        )
        respx.put(route).mock(
            return_value=httpx.Response(200, json={"status": "ok"})
        )
        result = runner.invoke(app, [
            "resource", "upload", "ignition/theme",
            "my-theme", str(test_file),
            "--signature", "sig1",
            "--filename", "remote-name.css",
            *COMMON_OPTS,
        ])
        assert result.exit_code == 0
        assert "remote-name.css" in result.output


class TestResourceDownload:
    @respx.mock
    def test_download_to_explicit_path(self, tmp_path):
        route = (
            f"{BASE}/resources/datafile"
            "/ignition/theme/my-theme/style.css"
        )
        respx.get(route).mock(
            return_value=httpx.Response(
                200, content=b"body { color: blue; }",
            )
        )
        dest = tmp_path / "style.css"
        result = runner.invoke(app, [
            "resource", "download", "ignition/theme",
            "my-theme", "style.css",
            "--output", str(dest),
            *COMMON_OPTS,
        ])
        assert result.exit_code == 0
        assert "Downloaded" in result.output
        assert dest.read_bytes() == b"body { color: blue; }"

    @respx.mock
    def test_download_binary(self, tmp_path):
        route = (
            f"{BASE}/resources/datafile"
            "/ignition/theme/my-theme/font.woff2"
        )
        respx.get(route).mock(
            return_value=httpx.Response(
                200, content=b"\x00\x01woff2data",
            )
        )
        dest = tmp_path / "custom-output.woff2"
        result = runner.invoke(app, [
            "resource", "download", "ignition/theme",
            "my-theme", "font.woff2",
            "--output", str(dest),
            *COMMON_OPTS,
        ])
        assert result.exit_code == 0
        assert dest.read_bytes() == b"\x00\x01woff2data"


class TestResourceShowWithFiles:
    @respx.mock
    def test_show_with_files_table(self):
        find_url = f"{BASE}/resources/find/ignition/theme/my-theme"
        respx.get(find_url).mock(
            return_value=httpx.Response(200, json={
                "name": "my-theme",
                "signature": "sig123",
                "files": ["style.css", "logo.png"],
            })
        )
        result = runner.invoke(app, [
            "resource", "show", "ignition/theme", "my-theme",
            *COMMON_OPTS,
        ])
        assert result.exit_code == 0
        assert "style.css" in result.output
        assert "logo.png" in result.output

    @respx.mock
    def test_show_with_files_json(self):
        find_url = f"{BASE}/resources/find/ignition/theme/my-theme"
        respx.get(find_url).mock(
            return_value=httpx.Response(200, json={
                "name": "my-theme",
                "files": ["a.css", "b.js"],
            })
        )
        result = runner.invoke(app, [
            "resource", "show", "ignition/theme", "my-theme",
            "-f", "json",
            *COMMON_OPTS,
        ])
        assert result.exit_code == 0
        assert "a.css" in result.output


class TestResourceNames:
    @respx.mock
    def test_names(self):
        respx.get(f"{BASE}/resources/names/ignition/database-connection").mock(
            return_value=httpx.Response(200, json=["db1", "db2"])
        )
        result = runner.invoke(app, [
            "resource", "names", "ignition/database-connection", *COMMON_OPTS,
        ])
        assert result.exit_code == 0


class TestResourceSingleton:
    @respx.mock
    def test_show_singleton(self):
        respx.get(
            f"{BASE}/resources/singleton/com.inductiveautomation.opcua/server-config"
        ).mock(
            return_value=httpx.Response(200, json={
                "name": "server-config",
                "signature": "sig-singleton",
                "config": {"enabled": True},
            })
        )
        result = runner.invoke(app, [
            "resource", "show",
            "com.inductiveautomation.opcua/server-config",
            *COMMON_OPTS,
        ])
        assert result.exit_code == 0
        assert "singleton" in result.output.lower()

    @respx.mock
    def test_show_singleton_with_collection(self):
        route = respx.get(
            f"{BASE}/resources/singleton/com.inductiveautomation.opcua/server-config"
        ).mock(
            return_value=httpx.Response(200, json={
                "name": "server-config",
                "signature": "sig-mode",
            })
        )
        result = runner.invoke(app, [
            "resource", "show",
            "com.inductiveautomation.opcua/server-config",
            "--collection", "staging",
            *COMMON_OPTS,
        ])
        assert result.exit_code == 0
        req_url = str(route.calls.last.request.url)
        assert "collection=staging" in req_url

    @respx.mock
    def test_show_singleton_default_if_undefined(self):
        route = respx.get(
            f"{BASE}/resources/singleton/com.inductiveautomation.opcua/server-config"
        ).mock(
            return_value=httpx.Response(200, json={
                "name": "server-config",
                "config": {"enabled": False},
            })
        )
        result = runner.invoke(app, [
            "resource", "show",
            "com.inductiveautomation.opcua/server-config",
            "--default-if-undefined",
            *COMMON_OPTS,
        ])
        assert result.exit_code == 0
        req_url = str(route.calls.last.request.url)
        assert "defaultIfUndefined=true" in req_url

    @respx.mock
    def test_show_regular_with_name_still_works(self):
        respx.get(
            f"{BASE}/resources/find/ignition/database-connection/db1"
        ).mock(
            return_value=httpx.Response(200, json={
                "name": "db1",
                "signature": "sig123",
            })
        )
        result = runner.invoke(app, [
            "resource", "show",
            "ignition/database-connection", "db1",
            *COMMON_OPTS,
        ])
        assert result.exit_code == 0
        assert "db1" in result.output

    @respx.mock
    def test_update_singleton(self):
        respx.get(
            f"{BASE}/resources/singleton/com.inductiveautomation.opcua/server-config"
        ).mock(
            return_value=httpx.Response(200, json={
                "name": "server-config",
                "signature": "sig-single",
            })
        )
        route = respx.put(
            f"{BASE}/resources/com.inductiveautomation.opcua/server-config"
        ).mock(
            return_value=httpx.Response(200, json={})
        )
        result = runner.invoke(app, [
            "resource", "update",
            "com.inductiveautomation.opcua/server-config",
            "--config", '{"enabled": false}',
            *COMMON_OPTS,
        ])
        assert result.exit_code == 0
        assert "updated" in result.output
        body = json.loads(route.calls.last.request.content)
        assert body[0]["name"] == "server-config"
        assert body[0]["signature"] == "sig-single"


class TestResourceTypes:
    @respx.mock
    def test_types(self):
        spec = {
            "paths": {
                "/data/api/v1/resources/list/ignition/database-connection": {"get": {}},
                "/data/api/v1/resources/list/ignition/tag-provider": {"get": {}},
            }
        }
        respx.get("https://gw:8043/openapi.json").mock(
            return_value=httpx.Response(200, json=spec)
        )
        result = runner.invoke(app, [
            "resource", "types", *COMMON_OPTS,
        ])
        assert result.exit_code == 0
        assert "ignition/database-connection" in result.output
