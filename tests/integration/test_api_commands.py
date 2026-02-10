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
        result = runner.invoke(app, ["api", "get", "/gateway-info", "--url", "https://gw:8043", "--token", "k:s"])
        assert result.exit_code == 0
        assert "RUNNING" in result.output

    @respx.mock
    def test_api_post(self):
        respx.post("https://gw:8043/data/api/v1/projects").mock(
            return_value=httpx.Response(201, json={"id": "created"})
        )
        result = runner.invoke(
            app,
            ["api", "post", "/projects", "--data", '{"name":"test"}', "--url", "https://gw:8043", "--token", "k:s"],
        )
        assert result.exit_code == 0
        assert "created" in result.output

    @respx.mock
    def test_api_delete(self):
        respx.delete("https://gw:8043/data/api/v1/projects/old").mock(
            return_value=httpx.Response(204)
        )
        result = runner.invoke(app, ["api", "delete", "/projects/old", "--url", "https://gw:8043", "--token", "k:s"])
        assert result.exit_code == 0
        assert "Deleted" in result.output
