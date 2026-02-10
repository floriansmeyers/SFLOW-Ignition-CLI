"""Integration tests for raw API commands."""

from __future__ import annotations

import httpx
import respx
from typer.testing import CliRunner

from ignition_cli.app import app

runner = CliRunner()


class TestAPICommands:
    @respx.mock
    def test_api_get(self):
        respx.get("https://gw:8043/data/api/v1/gateway-info").mock(
            return_value=httpx.Response(200, json={"state": "RUNNING"})
        )
        result = runner.invoke(app, [
            "api", "get", "/gateway-info",
            "--url", "https://gw:8043", "--token", "k:s",
        ])
        assert result.exit_code == 0
        assert "RUNNING" in result.output

    @respx.mock
    def test_api_post(self):
        respx.post("https://gw:8043/data/api/v1/projects").mock(
            return_value=httpx.Response(201, json={"id": "created"})
        )
        result = runner.invoke(
            app,
            ["api", "post", "/projects",
             "--data", '{"name":"test"}',
             "--url", "https://gw:8043", "--token", "k:s"],
        )
        assert result.exit_code == 0
        assert "created" in result.output

    @respx.mock
    def test_api_delete(self):
        respx.delete("https://gw:8043/data/api/v1/projects/old").mock(
            return_value=httpx.Response(204)
        )
        result = runner.invoke(app, [
            "api", "delete", "/projects/old",
            "--url", "https://gw:8043", "--token", "k:s",
        ])
        assert result.exit_code == 0
        assert "Deleted" in result.output

    @respx.mock
    def test_api_put(self):
        respx.put("https://gw:8043/data/api/v1/mode/dev").mock(
            return_value=httpx.Response(200, json={"name": "dev", "title": "Dev"})
        )
        result = runner.invoke(
            app,
            ["api", "put", "/mode/dev", "--data", '{"name":"dev","title":"Dev"}',
             "--url", "https://gw:8043", "--token", "k:s"],
        )
        assert result.exit_code == 0
        assert "dev" in result.output


class TestAPIDiscover:
    @respx.mock
    def test_discover(self):
        spec = {
            "paths": {
                "/data/api/v1/gateway-info": {
                    "get": {"summary": "Gateway info"},
                },
                "/data/api/v1/projects": {
                    "get": {"summary": "List projects"},
                    "post": {"summary": "Create project"},
                },
            }
        }
        respx.get("https://gw:8043/openapi.json").mock(
            return_value=httpx.Response(200, json=spec)
        )
        result = runner.invoke(app, [
            "api", "discover", "--url", "https://gw:8043", "--token", "k:s",
        ])
        assert result.exit_code == 0
        assert "gateway-info" in result.output
        assert "3 endpoints" in result.output

    @respx.mock
    def test_discover_with_filter(self):
        spec = {
            "paths": {
                "/data/api/v1/gateway-info": {"get": {"summary": "Info"}},
                "/data/api/v1/projects": {"get": {"summary": "List"}},
            }
        }
        respx.get("https://gw:8043/openapi.json").mock(
            return_value=httpx.Response(200, json=spec)
        )
        result = runner.invoke(app, [
            "api", "discover", "--filter", "project",
            "--url", "https://gw:8043", "--token", "k:s",
        ])
        assert result.exit_code == 0
        assert "1 endpoints" in result.output

    @respx.mock
    def test_discover_method_filter(self):
        spec = {
            "paths": {
                "/data/api/v1/projects": {
                    "get": {"summary": "List"},
                    "post": {"summary": "Create"},
                },
            }
        }
        respx.get("https://gw:8043/openapi.json").mock(
            return_value=httpx.Response(200, json=spec)
        )
        result = runner.invoke(app, [
            "api", "discover", "--method", "POST",
            "--url", "https://gw:8043", "--token", "k:s",
        ])
        assert result.exit_code == 0
        assert "1 endpoints" in result.output


class TestAPISpec:
    @respx.mock
    def test_spec_stdout(self):
        spec = {"openapi": "3.0.0", "paths": {}}
        respx.get("https://gw:8043/openapi.json").mock(
            return_value=httpx.Response(200, json=spec)
        )
        result = runner.invoke(app, [
            "api", "spec", "--url", "https://gw:8043", "--token", "k:s",
        ])
        assert result.exit_code == 0
        assert "3.0.0" in result.output

    @respx.mock
    def test_spec_to_file(self, tmp_path):
        spec = {"openapi": "3.0.0", "paths": {"/test": {}}}
        respx.get("https://gw:8043/openapi.json").mock(
            return_value=httpx.Response(200, json=spec)
        )
        dest = tmp_path / "spec.json"
        result = runner.invoke(app, [
            "api", "spec", "--output", str(dest),
            "--url", "https://gw:8043", "--token", "k:s",
        ])
        assert result.exit_code == 0
        assert "saved" in result.output.lower()
        assert dest.exists()
