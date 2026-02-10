"""Integration tests for config commands."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from ignition_cli.app import app
from ignition_cli.config.manager import ConfigManager

runner = CliRunner()


def _patch_manager(tmp_path: Path):
    """Patch ConfigManager to use a temp config file."""
    config_path = tmp_path / "config.toml"
    return patch(
        "ignition_cli.commands.config_cmd._get_manager",
        return_value=ConfigManager(config_path=config_path),
    )


class TestConfigCommands:
    def test_list_empty(self, tmp_path: Path):
        with _patch_manager(tmp_path):
            result = runner.invoke(app, ["config", "list"])
            assert result.exit_code == 0
            assert "No profiles configured" in result.output

    def test_add_and_list(self, tmp_path: Path):
        with _patch_manager(tmp_path):
            result = runner.invoke(app, ["config", "add", "dev", "--url", "https://gw:8043", "--token", "k:s"])
            assert result.exit_code == 0
            assert "added" in result.output

            result = runner.invoke(app, ["config", "list"])
            assert result.exit_code == 0
            assert "dev" in result.output

    def test_show_profile(self, tmp_path: Path):
        with _patch_manager(tmp_path):
            runner.invoke(app, ["config", "add", "dev", "--url", "https://gw:8043", "--token", "longtoken:secret"])
            result = runner.invoke(app, ["config", "show", "dev"])
            assert result.exit_code == 0
            assert "dev" in result.output
            # Token should be masked
            assert "longtoken:secret" not in result.output

    def test_show_nonexistent(self, tmp_path: Path):
        with _patch_manager(tmp_path):
            result = runner.invoke(app, ["config", "show", "nope"])
            assert result.exit_code == 1

    def test_set_default(self, tmp_path: Path):
        with _patch_manager(tmp_path):
            runner.invoke(app, ["config", "add", "a", "--url", "https://a:8043"])
            runner.invoke(app, ["config", "add", "b", "--url", "https://b:8043"])
            result = runner.invoke(app, ["config", "set-default", "b"])
            assert result.exit_code == 0
            assert "b" in result.output

    def test_remove_profile(self, tmp_path: Path):
        with _patch_manager(tmp_path):
            runner.invoke(app, ["config", "add", "dev", "--url", "https://gw:8043"])
            result = runner.invoke(app, ["config", "remove", "dev", "--force"])
            assert result.exit_code == 0
            assert "removed" in result.output

    def test_remove_nonexistent(self, tmp_path: Path):
        with _patch_manager(tmp_path):
            result = runner.invoke(app, ["config", "remove", "nope", "--force"])
            assert result.exit_code == 1

    def test_list_json_format(self, tmp_path: Path):
        with _patch_manager(tmp_path):
            runner.invoke(app, ["config", "add", "dev", "--url", "https://gw:8043", "--token", "k:s"])
            result = runner.invoke(app, ["config", "list", "--format", "json"])
            assert result.exit_code == 0
            assert "profiles" in result.output
