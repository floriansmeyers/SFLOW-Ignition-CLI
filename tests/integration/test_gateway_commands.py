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
        result = runner.invoke(app, [
            "gateway", "status",
            "--url", "https://gw:8043", "--token", "k:s",
        ])
        assert result.exit_code == 0
        assert "RUNNING" in result.output

    @respx.mock
    def test_status_json(self, mock_gateway_status: dict):
        respx.get("https://gw:8043/data/api/v1/gateway-info").mock(
            return_value=httpx.Response(200, json=mock_gateway_status)
        )
        result = runner.invoke(app, [
            "gateway", "status",
            "--url", "https://gw:8043", "--token", "k:s",
            "-f", "json",
        ])
        assert result.exit_code == 0
        assert "RUNNING" in result.output

    @respx.mock
    def test_info(self, mock_gateway_info: dict):
        respx.get("https://gw:8043/data/api/v1/gateway-info").mock(
            return_value=httpx.Response(200, json=mock_gateway_info)
        )
        result = runner.invoke(app, [
            "gateway", "info",
            "--url", "https://gw:8043", "--token", "k:s",
        ])
        assert result.exit_code == 0
        assert "8.3.0" in result.output

    @respx.mock
    def test_modules(self, mock_modules: list):
        respx.get("https://gw:8043/data/api/v1/modules/healthy").mock(
            return_value=httpx.Response(200, json=mock_modules)
        )
        result = runner.invoke(app, [
            "gateway", "modules",
            "--url", "https://gw:8043", "--token", "k:s",
        ])
        assert result.exit_code == 0
        assert "Perspective" in result.output

    @respx.mock
    def test_modules_quarantined(self):
        respx.get("https://gw:8043/data/api/v1/modules/quarantined").mock(
            return_value=httpx.Response(200, json=[
                {"name": "BadModule", "id": "com.bad.module",
                 "version": "1.0.0", "state": "QUARANTINED"},
            ])
        )
        result = runner.invoke(app, [
            "gateway", "modules", "--quarantined",
            "--url", "https://gw:8043", "--token", "k:s",
        ])
        assert result.exit_code == 0
        assert "BadModule" in result.output


class TestGatewayScanCommands:
    @respx.mock
    def test_scan_projects(self):
        respx.post("https://gw:8043/data/api/v1/scan/projects").mock(
            return_value=httpx.Response(200, json={})
        )
        result = runner.invoke(app, [
            "gateway", "scan-projects",
            "--url", "https://gw:8043", "--token", "k:s",
        ])
        assert result.exit_code == 0
        assert "scan triggered" in result.output.lower()

    @respx.mock
    def test_scan_config(self):
        respx.post("https://gw:8043/data/api/v1/scan/config").mock(
            return_value=httpx.Response(200, json={})
        )
        result = runner.invoke(app, [
            "gateway", "scan-config",
            "--url", "https://gw:8043", "--token", "k:s",
        ])
        assert result.exit_code == 0
        assert "scan triggered" in result.output.lower()

    @respx.mock
    def test_scan_projects_auth_failure(self):
        respx.post("https://gw:8043/data/api/v1/scan/projects").mock(
            return_value=httpx.Response(
                401, json={"message": "Unauthorized"},
            )
        )
        result = runner.invoke(app, [
            "gateway", "scan-projects",
            "--url", "https://gw:8043", "--token", "bad:token",
        ])
        assert result.exit_code != 0


class TestGatewayBackupRestore:
    @respx.mock
    def test_backup(self, tmp_path):
        respx.get("https://gw:8043/data/api/v1/backup").mock(
            return_value=httpx.Response(200, content=b"\x00GWBK-CONTENT")
        )
        dest = tmp_path / "test.gwbk"
        result = runner.invoke(app, [
            "gateway", "backup",
            "--output", str(dest),
            "--url", "https://gw:8043", "--token", "k:s",
        ])
        assert result.exit_code == 0
        assert "saved" in result.output.lower()

    @respx.mock
    def test_restore(self, tmp_path):
        backup_file = tmp_path / "backup.gwbk"
        backup_file.write_bytes(b"\x00GWBK-DATA")
        respx.post("https://gw:8043/data/api/v1/backup").mock(
            return_value=httpx.Response(200, json={})
        )
        result = runner.invoke(app, [
            "gateway", "restore", str(backup_file),
            "--url", "https://gw:8043", "--token", "k:s",
        ])
        assert result.exit_code == 0
        assert "restore" in result.output.lower()

    def test_restore_file_not_found(self):
        result = runner.invoke(app, [
            "gateway", "restore", "/nonexistent/file.gwbk",
            "--url", "https://gw:8043", "--token", "k:s",
        ])
        assert result.exit_code != 0
        assert "not found" in result.output.lower()


class TestGatewayLogs:
    @respx.mock
    def test_logs(self):
        respx.get("https://gw:8043/data/api/v1/logs").mock(
            return_value=httpx.Response(200, json=[
                {"timestamp": "2024-01-01T00:00:00Z", "level": "INFO",
                 "logger": "Gateway", "message": "Started"},
            ])
        )
        result = runner.invoke(app, [
            "gateway", "logs",
            "--url", "https://gw:8043", "--token", "k:s",
        ])
        assert result.exit_code == 0
        assert "Started" in result.output

    @respx.mock
    def test_logs_with_level_filter(self):
        respx.get("https://gw:8043/data/api/v1/logs").mock(
            return_value=httpx.Response(200, json=[
                {"timestamp": "2024-01-01T00:00:00Z", "level": "ERROR",
                 "logger": "Gateway", "message": "Disk full"},
            ])
        )
        result = runner.invoke(app, [
            "gateway", "logs", "--level", "ERROR",
            "--url", "https://gw:8043", "--token", "k:s",
        ])
        assert result.exit_code == 0
        assert "Disk full" in result.output


class TestGatewayLogManagement:
    @respx.mock
    def test_log_download(self, tmp_path):
        respx.get("https://gw:8043/data/api/v1/logs/download").mock(
            return_value=httpx.Response(200, content=b"PK\x03\x04log-data")
        )
        dest = tmp_path / "logs.zip"
        result = runner.invoke(app, [
            "gateway", "log-download",
            "--output", str(dest),
            "--url", "https://gw:8043", "--token", "k:s",
        ])
        assert result.exit_code == 0
        assert "downloaded" in result.output.lower()

    @respx.mock
    def test_loggers(self):
        respx.get("https://gw:8043/data/api/v1/logs/loggers").mock(
            return_value=httpx.Response(200, json=[
                {"name": "com.inductiveautomation.gateway", "level": "INFO"},
                {"name": "com.inductiveautomation.perspective", "level": "WARN"},
            ])
        )
        result = runner.invoke(app, [
            "gateway", "loggers",
            "--url", "https://gw:8043", "--token", "k:s",
        ])
        assert result.exit_code == 0


class TestGatewayEntityBrowse:
    @respx.mock
    def test_entity_browse_default(self):
        respx.get("https://gw:8043/data/api/v1/entity/browse").mock(
            return_value=httpx.Response(200, json={
                "path": "/",
                "children": [{"name": "config", "type": "folder"}],
            })
        )
        result = runner.invoke(app, [
            "gateway", "entity-browse",
            "--url", "https://gw:8043", "--token", "k:s",
        ])
        assert result.exit_code == 0

    @respx.mock
    def test_entity_browse_with_path_and_depth(self):
        respx.get("https://gw:8043/data/api/v1/entity/browse").mock(
            return_value=httpx.Response(200, json={
                "path": "/config/databases",
                "children": [{"name": "MySQL", "type": "connection"}],
            })
        )
        result = runner.invoke(app, [
            "gateway", "entity-browse",
            "--path", "/config/databases", "--depth", "2",
            "--url", "https://gw:8043", "--token", "k:s",
        ])
        assert result.exit_code == 0


class TestGatewayErrors:
    @respx.mock
    def test_auth_failure(self):
        respx.get("https://gw:8043/data/api/v1/gateway-info").mock(
            return_value=httpx.Response(401, json={"message": "Unauthorized"})
        )
        result = runner.invoke(app, [
            "gateway", "status",
            "--url", "https://gw:8043", "--token", "bad:token",
        ])
        assert result.exit_code != 0
