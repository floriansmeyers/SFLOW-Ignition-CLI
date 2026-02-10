"""Integration tests for device commands."""

from __future__ import annotations

import httpx
import respx
from typer.testing import CliRunner

from ignition_cli.app import app

runner = CliRunner()
GW = "https://gw:8043"
BASE = f"{GW}/data/api/v1"
DEVICE_PATH = "resources/list/com.inductiveautomation.opcua/device"
DEVICE_FIND = "resources/find/com.inductiveautomation.opcua/device"


class TestDeviceCommands:
    @respx.mock
    def test_list_devices(self):
        respx.get(f"{BASE}/{DEVICE_PATH}").mock(
            return_value=httpx.Response(200, json=[
                {"name": "PLC1", "type": "Modbus TCP", "enabled": True, "state": "Connected", "hostname": "10.0.0.1"},
                {"name": "PLC2", "type": "OPC-UA", "enabled": True, "state": "Faulted", "hostname": "10.0.0.2"},
            ])
        )
        result = runner.invoke(app, ["device", "list", "--url", GW, "--token", "k:s"])
        assert result.exit_code == 0
        assert "PLC1" in result.output
        assert "PLC2" in result.output

    @respx.mock
    def test_list_filter_status(self):
        respx.get(f"{BASE}/{DEVICE_PATH}").mock(
            return_value=httpx.Response(200, json=[
                {"name": "PLC1", "state": "Connected"},
                {"name": "PLC2", "state": "Faulted"},
            ])
        )
        result = runner.invoke(app, ["device", "list", "--status", "Faulted", "--url", GW, "--token", "k:s"])
        assert result.exit_code == 0
        assert "PLC2" in result.output

    @respx.mock
    def test_show_device(self):
        respx.get(f"{BASE}/{DEVICE_FIND}/PLC1").mock(
            return_value=httpx.Response(200, json={"name": "PLC1", "type": "Modbus TCP", "hostname": "10.0.0.1"})
        )
        result = runner.invoke(app, ["device", "show", "PLC1", "--url", GW, "--token", "k:s"])
        assert result.exit_code == 0
        assert "PLC1" in result.output

    @respx.mock
    def test_device_status(self):
        respx.get(f"{BASE}/{DEVICE_FIND}/PLC1").mock(
            return_value=httpx.Response(200, json={"name": "PLC1", "state": "Connected"})
        )
        result = runner.invoke(app, ["device", "status", "PLC1", "--url", GW, "--token", "k:s"])
        assert result.exit_code == 0
        assert "Connected" in result.output

    def test_restart_shows_note(self):
        result = runner.invoke(app, ["device", "restart", "PLC1", "--url", GW, "--token", "k:s"])
        assert result.exit_code == 0
        assert "does not have a direct device restart endpoint" in result.output
