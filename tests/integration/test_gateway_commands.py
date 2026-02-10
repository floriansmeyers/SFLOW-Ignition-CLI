"""Integration tests for gateway commands."""

from __future__ import annotations

import httpx
import respx
from typer.testing import CliRunner

from ignition_cli.app import app

runner = CliRunner()


class TestGatewayCommands:
    @respx.mock
    def test_status(self, mock_gateway_status: dict):
        respx.get("https://gw:8043/data/api/v1/gateway-info").mock(
            return_value=httpx.Response(200, json=mock_gateway_status)
        )
        result = runner.invoke(app, ["gateway", "status", "--url", "https://gw:8043", "--token", "k:s"])
        assert result.exit_code == 0
        assert "RUNNING" in result.output

    @respx.mock
    def test_status_json(self, mock_gateway_status: dict):
        respx.get("https://gw:8043/data/api/v1/gateway-info").mock(
            return_value=httpx.Response(200, json=mock_gateway_status)
        )
        result = runner.invoke(app, ["gateway", "status", "--url", "https://gw:8043", "--token", "k:s", "-f", "json"])
        assert result.exit_code == 0
        assert "RUNNING" in result.output

    @respx.mock
    def test_info(self, mock_gateway_info: dict):
        respx.get("https://gw:8043/data/api/v1/gateway-info").mock(
            return_value=httpx.Response(200, json=mock_gateway_info)
        )
        result = runner.invoke(app, ["gateway", "info", "--url", "https://gw:8043", "--token", "k:s"])
        assert result.exit_code == 0
        assert "8.3.0" in result.output

    @respx.mock
    def test_modules(self, mock_modules: list):
        respx.get("https://gw:8043/data/api/v1/modules/healthy").mock(
            return_value=httpx.Response(200, json=mock_modules)
        )
        result = runner.invoke(app, ["gateway", "modules", "--url", "https://gw:8043", "--token", "k:s"])
        assert result.exit_code == 0
        assert "Perspective" in result.output

    @respx.mock
    def test_modules_quarantined(self):
        respx.get("https://gw:8043/data/api/v1/modules/quarantined").mock(
            return_value=httpx.Response(200, json=[
                {"name": "BadModule", "id": "com.bad.module", "version": "1.0.0", "state": "QUARANTINED"},
            ])
        )
        result = runner.invoke(app, ["gateway", "modules", "--quarantined", "--url", "https://gw:8043", "--token", "k:s"])
        assert result.exit_code == 0
        assert "BadModule" in result.output


class TestGatewayErrors:
    @respx.mock
    def test_auth_failure(self):
        respx.get("https://gw:8043/data/api/v1/gateway-info").mock(
            return_value=httpx.Response(401, json={"message": "Unauthorized"})
        )
        result = runner.invoke(app, ["gateway", "status", "--url", "https://gw:8043", "--token", "bad:token"])
        assert result.exit_code != 0
