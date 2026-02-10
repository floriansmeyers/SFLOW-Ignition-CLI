"""Integration tests for deployment mode commands."""

from __future__ import annotations

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
