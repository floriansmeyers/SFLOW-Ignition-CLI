"""Integration tests for deployment mode commands."""

from __future__ import annotations

import json

import httpx
import respx
from typer.testing import CliRunner

from ignition_cli.app import app

runner = CliRunner()

BASE = "https://gw:8043/data/api/v1"
COMMON_OPTS = ["--url", "https://gw:8043", "--token", "k:s"]

SAMPLE_MODES = {
    "items": [
        {
            "name": "dev",
            "title": "Development",
            "description": "Dev environment",
            "resourceCount": 5,
        },
        {
            "name": "staging",
            "title": "Staging",
            "description": "Pre-prod",
            "resourceCount": 3,
        },
        {
            "name": "prod",
            "title": "Production",
            "description": "",
            "resourceCount": 10,
        },
    ],
}


class TestModeListCommand:
    @respx.mock
    def test_list_table(self):
        respx.get(f"{BASE}/mode").mock(
            return_value=httpx.Response(200, json=SAMPLE_MODES)
        )
        result = runner.invoke(
            app, ["mode", "list", *COMMON_OPTS],
        )
        assert result.exit_code == 0
        assert "dev" in result.output
        assert "staging" in result.output
        assert "prod" in result.output

    @respx.mock
    def test_list_json(self):
        respx.get(f"{BASE}/mode").mock(
            return_value=httpx.Response(200, json=SAMPLE_MODES)
        )
        result = runner.invoke(
            app, ["mode", "list", "-f", "json", *COMMON_OPTS],
        )
        assert result.exit_code == 0
        assert "dev" in result.output


class TestModeShowCommand:
    @respx.mock
    def test_show_existing(self):
        respx.get(f"{BASE}/mode").mock(
            return_value=httpx.Response(200, json=SAMPLE_MODES)
        )
        result = runner.invoke(
            app, ["mode", "show", "dev", *COMMON_OPTS],
        )
        assert result.exit_code == 0
        assert "dev" in result.output
        assert "Development" in result.output

    @respx.mock
    def test_show_not_found(self):
        respx.get(f"{BASE}/mode").mock(
            return_value=httpx.Response(200, json=SAMPLE_MODES)
        )
        result = runner.invoke(
            app, ["mode", "show", "nonexistent", *COMMON_OPTS],
        )
        assert result.exit_code != 0


class TestModeCreateCommand:
    @respx.mock
    def test_create_basic(self):
        respx.post(f"{BASE}/mode").mock(
            return_value=httpx.Response(200, json={"name": "dev"})
        )
        result = runner.invoke(
            app, ["mode", "create", "dev", *COMMON_OPTS],
        )
        assert result.exit_code == 0
        assert "created" in result.output.lower()

    @respx.mock
    def test_create_with_title_and_description(self):
        respx.post(f"{BASE}/mode").mock(
            return_value=httpx.Response(200, json={
                "name": "staging",
                "title": "Staging",
                "description": "Pre-prod",
            })
        )
        result = runner.invoke(app, [
            "mode", "create", "staging",
            "--title", "Staging",
            "--description", "Pre-prod",
            *COMMON_OPTS,
        ])
        assert result.exit_code == 0
        assert "staging" in result.output


class TestModeUpdateCommand:
    @respx.mock
    def test_update_description(self):
        respx.put(f"{BASE}/mode/dev").mock(
            return_value=httpx.Response(200, json={
                "name": "dev", "description": "Updated",
            })
        )
        result = runner.invoke(app, [
            "mode", "update", "dev",
            "--description", "Updated",
            *COMMON_OPTS,
        ])
        assert result.exit_code == 0
        assert "updated" in result.output.lower()

    def test_update_nothing(self):
        result = runner.invoke(
            app, ["mode", "update", "dev", *COMMON_OPTS],
        )
        assert result.exit_code == 0
        assert "Nothing" in result.output


class TestModeDeleteCommand:
    @respx.mock
    def test_delete_with_force(self):
        respx.delete(f"{BASE}/mode/dev").mock(
            return_value=httpx.Response(200, json={"status": "ok"})
        )
        result = runner.invoke(
            app, ["mode", "delete", "dev", "--force", *COMMON_OPTS],
        )
        assert result.exit_code == 0
        assert "deleted" in result.output.lower()


class TestModeAssignCommand:
    @respx.mock
    def test_assign_resource(self):
        respx.get(
            f"{BASE}/resources/find/ignition/database-connection/Automotive"
        ).mock(
            return_value=httpx.Response(200, json={
                "name": "Automotive",
                "config": {"driver": "MySQL ConnectorJ"},
            })
        )
        route = respx.post(
            f"{BASE}/resources/ignition/database-connection"
        ).mock(
            return_value=httpx.Response(201, json={})
        )
        result = runner.invoke(app, [
            "mode", "assign", "staging",
            "ignition/database-connection", "Automotive",
            *COMMON_OPTS,
        ])
        assert result.exit_code == 0
        assert "assigned" in result.output.lower()
        assert "staging" in result.output
        body = json.loads(route.calls.last.request.content)
        assert body[0]["collection"] == "staging"
        assert body[0]["name"] == "Automotive"
        assert body[0]["config"] == {"driver": "MySQL ConnectorJ"}

    @respx.mock
    def test_assign_resource_without_config(self):
        respx.get(
            f"{BASE}/resources/find/ignition/database-connection/TestDB"
        ).mock(
            return_value=httpx.Response(200, json={"name": "TestDB"})
        )
        route = respx.post(
            f"{BASE}/resources/ignition/database-connection"
        ).mock(
            return_value=httpx.Response(201, json={})
        )
        result = runner.invoke(app, [
            "mode", "assign", "dev",
            "ignition/database-connection", "TestDB",
            *COMMON_OPTS,
        ])
        assert result.exit_code == 0
        body = json.loads(route.calls.last.request.content)
        assert body[0]["collection"] == "dev"
        assert "config" not in body[0]

    def test_assign_invalid_resource_type(self):
        result = runner.invoke(app, [
            "mode", "assign", "staging",
            "invalid-no-slash", "TestDB",
            *COMMON_OPTS,
        ])
        assert result.exit_code != 0


class TestModeAssignSingleton:
    @respx.mock
    def test_assign_singleton_resource(self):
        respx.get(
            f"{BASE}/resources/singleton"
            "/com.inductiveautomation.opcua/server-config"
        ).mock(
            return_value=httpx.Response(200, json={
                "name": "server-config",
                "config": {"enabled": True},
            })
        )
        route = respx.post(
            f"{BASE}/resources/com.inductiveautomation.opcua/server-config"
        ).mock(
            return_value=httpx.Response(201, json={})
        )
        result = runner.invoke(app, [
            "mode", "assign", "staging",
            "com.inductiveautomation.opcua/server-config",
            *COMMON_OPTS,
        ])
        assert result.exit_code == 0
        assert "assigned" in result.output.lower()
        assert "staging" in result.output
        body = json.loads(route.calls.last.request.content)
        assert body[0]["collection"] == "staging"
        assert body[0]["name"] == "server-config"
        assert body[0]["config"] == {"enabled": True}


class TestModeUnassignSingleton:
    @respx.mock
    def test_unassign_singleton_resource(self):
        respx.get(
            f"{BASE}/resources/singleton"
            "/com.inductiveautomation.opcua/server-config"
        ).mock(
            return_value=httpx.Response(200, json={
                "name": "server-config",
                "signature": "mode-sig-single",
                "collection": "staging",
            })
        )
        delete_route = respx.delete(
            f"{BASE}/resources/com.inductiveautomation.opcua"
            "/server-config/server-config/mode-sig-single"
        ).mock(
            return_value=httpx.Response(200, json={"success": True})
        )
        result = runner.invoke(app, [
            "mode", "unassign", "staging",
            "com.inductiveautomation.opcua/server-config",
            *COMMON_OPTS,
        ])
        assert result.exit_code == 0
        assert "removed" in result.output.lower()
        assert "staging" in result.output
        delete_url = str(delete_route.calls.last.request.url)
        assert "collection=staging" in delete_url
        assert "confirm=true" in delete_url


class TestModeUnassignCommand:
    @respx.mock
    def test_unassign_resource(self):
        # Fetch must include ?collection=staging to get mode-specific signature
        respx.get(
            f"{BASE}/resources/find/ignition/database-connection/Automotive"
        ).mock(
            return_value=httpx.Response(200, json={
                "name": "Automotive",
                "signature": "mode-sig-789",
                "collection": "staging",
            })
        )
        delete_route = respx.delete(
            f"{BASE}/resources/ignition/database-connection/Automotive/mode-sig-789"
        ).mock(
            return_value=httpx.Response(200, json={"success": True})
        )
        result = runner.invoke(app, [
            "mode", "unassign", "staging",
            "ignition/database-connection", "Automotive",
            *COMMON_OPTS,
        ])
        assert result.exit_code == 0
        assert "removed" in result.output.lower()
        assert "staging" in result.output
        # Verify collection and confirm params were sent
        delete_url = str(delete_route.calls.last.request.url)
        assert "collection=staging" in delete_url
        assert "confirm=true" in delete_url

    @respx.mock
    def test_unassign_no_signature(self):
        respx.get(
            f"{BASE}/resources/find/ignition/database-connection/TestDB"
        ).mock(
            return_value=httpx.Response(200, json={"name": "TestDB"})
        )
        result = runner.invoke(app, [
            "mode", "unassign", "staging",
            "ignition/database-connection", "TestDB",
            *COMMON_OPTS,
        ])
        assert result.exit_code != 0
        assert "signature" in result.output.lower()

    def test_unassign_invalid_resource_type(self):
        result = runner.invoke(app, [
            "mode", "unassign", "staging",
            "bad-type", "TestDB",
            *COMMON_OPTS,
        ])
        assert result.exit_code != 0
