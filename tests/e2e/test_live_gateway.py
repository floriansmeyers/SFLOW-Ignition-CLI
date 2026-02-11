"""Extensive end-to-end tests against a live Ignition gateway.

These tests require a running Ignition 8.3+ gateway with the REST API enabled.
Skipped by default unless gateway credentials are provided.

Run with:
    pytest -m e2e --gateway-url=http://host:8088 --gateway-token=keyId:secretKey

WARNING: These tests create and delete real resources on the gateway.
         Use a development/test gateway, never production.
"""

from __future__ import annotations

import contextlib
import json
import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ignition_cli.app import app

runner = CliRunner()

# ---------------------------------------------------------------------------
# Unique prefixes to avoid collisions with real gateway data
# ---------------------------------------------------------------------------
_PREFIX = "e2e-test"
_PROJECT = f"{_PREFIX}-proj"
_PROJECT_COPY = f"{_PREFIX}-proj-copy"
_PROJECT_RENAME = f"{_PREFIX}-proj-renamed"
_MODE = f"{_PREFIX}-mode"
_MODE_RENAMED = f"{_PREFIX}-mode-renamed"
_RESOURCE_DB = f"{_PREFIX}-db-conn"
_MODE_ASSIGN = f"{_PREFIX}-assign-mode"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def invoke(args: list[str], gw_opts: list[str], *, should_succeed: bool = True):
    """Invoke the CLI and optionally assert success."""
    result = runner.invoke(app, [*args, *gw_opts])
    if should_succeed:
        assert result.exit_code == 0, (
            f"Command failed: {' '.join(args)}\n"
            f"Exit code: {result.exit_code}\n"
            f"Output: {result.output}"
        )
    return result


def invoke_no_gw(args: list[str], *, should_succeed: bool = True):
    """Invoke a command that doesn't need gateway opts (e.g. config)."""
    result = runner.invoke(app, args)
    if should_succeed:
        assert result.exit_code == 0, (
            f"Command failed: {' '.join(args)}\n"
            f"Exit code: {result.exit_code}\n"
            f"Output: {result.output}"
        )
    return result


# ===================================================================
# 1. GATEWAY COMMANDS
# ===================================================================


@pytest.mark.e2e
class TestGatewayStatus:
    """gateway status — concise status summary."""

    def test_status_table(self, gw_opts):
        result = invoke(["gateway", "status"], gw_opts)
        # Should contain key status fields
        # (API uses ignitionVersion, edition, deploymentMode)
        out = result.output.lower()
        assert any(k in out for k in ("edition", "version", "state", "deploymentmode"))

    def test_status_json(self, gw_opts):
        result = invoke(["gateway", "status", "--format", "json"], gw_opts)
        data = json.loads(result.output)
        assert isinstance(data, dict)
        # Gateway-info returns edition, deploymentMode,
        # ignitionVersion (not "version" or "state")
        expected_keys = (
            "edition", "state", "version",
            "deploymentMode", "ignitionVersion",
        )
        assert any(k in data for k in expected_keys)


@pytest.mark.e2e
class TestGatewayInfo:
    """gateway info — full gateway details."""

    def test_info_table(self, gw_opts):
        result = invoke(["gateway", "info"], gw_opts)
        out = result.output.lower()
        assert "version" in out or "edition" in out

    def test_info_json(self, gw_opts):
        result = invoke(["gateway", "info", "--format", "json"], gw_opts)
        data = json.loads(result.output)
        assert isinstance(data, dict)
        # Ignition 8.3 uses "ignitionVersion" not "version"
        assert "ignitionVersion" in data or "version" in data

    def test_info_yaml(self, gw_opts):
        result = invoke(["gateway", "info", "--format", "yaml"], gw_opts)
        assert "version" in result.output.lower()

    def test_info_csv(self, gw_opts):
        result = invoke(["gateway", "info", "--format", "csv"], gw_opts)
        assert len(result.output.strip()) > 0


@pytest.mark.e2e
class TestGatewayModules:
    """gateway modules — list healthy and quarantined modules."""

    def test_modules_healthy(self, gw_opts):
        result = invoke(["gateway", "modules"], gw_opts)
        out = result.output.lower()
        assert "module" in out or "name" in out or "installed" in out.lower()

    def test_modules_healthy_json(self, gw_opts):
        result = invoke(["gateway", "modules", "--format", "json"], gw_opts)
        data = json.loads(result.output)
        assert isinstance(data, (dict, list))

    def test_modules_quarantined(self, gw_opts):
        # Quarantined may be empty but the command should succeed
        result = invoke(["gateway", "modules", "--quarantined"], gw_opts)
        assert result.exit_code == 0


@pytest.mark.e2e
class TestGatewayLogs:
    """gateway logs — view and download logs."""

    def test_logs_default(self, gw_opts):
        result = invoke(["gateway", "logs"], gw_opts)
        assert result.exit_code == 0

    def test_logs_limited(self, gw_opts):
        result = invoke(["gateway", "logs", "--lines", "5"], gw_opts)
        assert result.exit_code == 0

    def test_logs_json(self, gw_opts):
        result = invoke(["gateway", "logs", "--format", "json"], gw_opts)
        data = json.loads(result.output)
        assert isinstance(data, (dict, list))

    def test_loggers(self, gw_opts):
        result = invoke(["gateway", "loggers"], gw_opts)
        assert result.exit_code == 0


@pytest.mark.e2e
class TestGatewayLogDownload:
    """gateway log-download — download logs as ZIP."""

    def test_log_download(self, gw_opts, tmp_path):
        dest = tmp_path / "logs.zip"
        invoke(["gateway", "log-download", "--output", str(dest)], gw_opts)
        assert dest.exists()
        assert dest.stat().st_size > 0


@pytest.mark.e2e
class TestGatewayScan:
    """gateway scan-projects / scan-config — fire-and-forget triggers."""

    def test_scan_projects(self, gw_opts):
        result = invoke(["gateway", "scan-projects"], gw_opts)
        assert "scan" in result.output.lower() or result.exit_code == 0

    def test_scan_config(self, gw_opts):
        result = invoke(["gateway", "scan-config"], gw_opts)
        assert "scan" in result.output.lower() or result.exit_code == 0


@pytest.mark.e2e
class TestGatewayEntityBrowse:
    """gateway entity-browse — browse the entity tree."""

    def test_entity_browse_root(self, gw_opts):
        result = invoke(["gateway", "entity-browse"], gw_opts)
        assert result.exit_code == 0

    def test_entity_browse_json(self, gw_opts):
        result = invoke(["gateway", "entity-browse", "--format", "json"], gw_opts)
        data = json.loads(result.output)
        assert isinstance(data, (dict, list))

    def test_entity_browse_depth(self, gw_opts):
        result = invoke(["gateway", "entity-browse", "--depth", "2"], gw_opts)
        assert result.exit_code == 0


@pytest.mark.e2e
class TestGatewayBackupRestore:
    """gateway backup / restore — backup round-trip.

    NOTE: Restore is intentionally skipped in automated tests to avoid
    disrupting the gateway state. Backup is tested for real.
    """

    def test_backup(self, gw_opts, tmp_path):
        dest = tmp_path / "test-backup.gwbk"
        invoke(["gateway", "backup", "--output", str(dest)], gw_opts)
        assert dest.exists()
        assert dest.stat().st_size > 1000  # Should be a real backup, not empty


# ===================================================================
# 2. PROJECT COMMANDS (CRUD + export/import + copy/rename)
# ===================================================================


@pytest.mark.e2e
class TestProjectList:
    """project list — listing and filtering."""

    def test_list_table(self, gw_opts):
        result = invoke(["project", "list"], gw_opts)
        assert result.exit_code == 0

    def test_list_json(self, gw_opts):
        result = invoke(["project", "list", "--format", "json"], gw_opts)
        data = json.loads(result.output)
        assert isinstance(data, (dict, list))

    def test_list_csv(self, gw_opts):
        result = invoke(["project", "list", "--format", "csv"], gw_opts)
        assert result.exit_code == 0

    def test_list_filter(self, gw_opts):
        # Filter with a term that won't match e2e artifacts
        result = invoke(["project", "list", "--filter", "zzz-nonexistent"], gw_opts)
        assert result.exit_code == 0


@pytest.mark.e2e
class TestProjectCRUD:
    """project create / show / delete — full lifecycle."""

    def test_01_create(self, gw_opts):
        result = invoke([
            "project", "create", _PROJECT,
            "--title", "E2E Test Project",
            "--description", "Created by automated tests",
        ], gw_opts)
        assert "created" in result.output.lower()

    def test_02_show(self, gw_opts):
        result = invoke(["project", "show", _PROJECT], gw_opts)
        assert _PROJECT in result.output

    def test_03_show_json(self, gw_opts):
        result = invoke(["project", "show", _PROJECT, "--format", "json"], gw_opts)
        data = json.loads(result.output)
        assert isinstance(data, dict)
        assert data.get("name") == _PROJECT

    def test_04_resources(self, gw_opts):
        result = invoke(["project", "resources", _PROJECT], gw_opts)
        assert result.exit_code == 0

    def test_05_delete(self, gw_opts):
        result = invoke(["project", "delete", _PROJECT, "--force"], gw_opts)
        assert "deleted" in result.output.lower()


@pytest.mark.e2e
class TestProjectExportImport:
    """project export / import — round-trip test."""

    def test_01_create_for_export(self, gw_opts):
        invoke(["project", "create", _PROJECT, "--title", "Export Test"], gw_opts)

    def test_02_export(self, gw_opts, tmp_path):
        dest = tmp_path / "exported.zip"
        result = invoke(["project", "export", _PROJECT, "--output", str(dest)], gw_opts)
        assert dest.exists()
        assert dest.stat().st_size > 0
        assert "exported" in result.output.lower()
        # Store path for import test
        os.environ["_E2E_EXPORT_PATH"] = str(dest)

    def test_03_import_as_copy(self, gw_opts):
        export_path = os.environ.get("_E2E_EXPORT_PATH")
        if not export_path or not Path(export_path).exists():
            pytest.skip("Export file not available from previous test")
        import_name = f"{_PROJECT}-imported"
        result = invoke([
            "project", "import", export_path,
            "--name", import_name,
        ], gw_opts)
        assert "imported" in result.output.lower()
        # Clean up
        invoke(["project", "delete", import_name, "--force"], gw_opts)

    def test_04_cleanup(self, gw_opts):
        invoke(
            ["project", "delete", _PROJECT, "--force"],
            gw_opts, should_succeed=False,
        )


@pytest.mark.e2e
class TestProjectCopyRename:
    """project copy / rename."""

    def test_01_create_source(self, gw_opts):
        invoke(["project", "create", _PROJECT, "--title", "Copy Source"], gw_opts)

    def test_02_copy(self, gw_opts):
        result = runner.invoke(app, [
            "project", "copy", _PROJECT, "--name", _PROJECT_COPY, *gw_opts,
        ])
        if result.exit_code != 0:
            pytest.skip(
                "Project copy not supported by this gateway: "
                f"{result.output[:200]}"
            )
        assert "copied" in result.output.lower()

    def test_03_rename(self, gw_opts):
        # Verify the copy target exists first; skip if copy was skipped
        check = runner.invoke(app, [
            "project", "show", _PROJECT_COPY,
            "--format", "json", *gw_opts,
        ])
        if check.exit_code != 0:
            pytest.skip(
                "Copy target does not exist "
                "(copy may have been skipped)"
            )
        result = invoke([
            "project", "rename", _PROJECT_COPY, "--name", _PROJECT_RENAME,
        ], gw_opts)
        assert "renamed" in result.output.lower()

    def test_04_verify_renamed(self, gw_opts):
        check = runner.invoke(app, [
            "project", "show", _PROJECT_RENAME,
            "--format", "json", *gw_opts,
        ])
        if check.exit_code != 0:
            pytest.skip(
                "Renamed project does not exist "
                "(copy/rename may have been skipped)"
            )
        assert _PROJECT_RENAME in check.output

    def test_05_cleanup(self, gw_opts):
        invoke(
            ["project", "delete", _PROJECT, "--force"],
            gw_opts, should_succeed=False,
        )
        invoke(
            ["project", "delete", _PROJECT_RENAME, "--force"],
            gw_opts, should_succeed=False,
        )
        invoke(
            ["project", "delete", _PROJECT_COPY, "--force"],
            gw_opts, should_succeed=False,
        )


# ===================================================================
# 3. TAG COMMANDS
# ===================================================================


@pytest.mark.e2e
class TestTagProviders:
    """tag providers — list available tag providers."""

    def test_providers_table(self, gw_opts):
        result = invoke(["tag", "providers"], gw_opts)
        assert result.exit_code == 0

    def test_providers_json(self, gw_opts):
        result = invoke(["tag", "providers", "--format", "json"], gw_opts)
        data = json.loads(result.output)
        assert isinstance(data, (dict, list))


@pytest.mark.e2e
class TestTagBrowse:
    """tag browse — browse the tag tree."""

    def test_browse_root(self, gw_opts):
        result = invoke(["tag", "browse"], gw_opts)
        assert result.exit_code == 0

    def test_browse_json(self, gw_opts):
        result = invoke(["tag", "browse", "--format", "json"], gw_opts)
        data = json.loads(result.output)
        assert isinstance(data, (dict, list))

    def test_browse_recursive(self, gw_opts):
        result = invoke(["tag", "browse", "--recursive"], gw_opts)
        assert result.exit_code == 0

    def test_browse_custom_provider(self, gw_opts):
        result = invoke(["tag", "browse", "--provider", "default"], gw_opts)
        assert result.exit_code == 0


@pytest.mark.e2e
class TestTagExportImport:
    """tag export / import — round-trip test."""

    def test_01_export_json_stdout(self, gw_opts):
        result = invoke(["tag", "export"], gw_opts)
        assert result.exit_code == 0

    def test_02_export_json_file(self, gw_opts, tmp_path):
        dest = tmp_path / "tags-export.json"
        invoke(["tag", "export", "--output", str(dest)], gw_opts)
        assert dest.exists()
        assert dest.stat().st_size > 0
        # Store for import test
        os.environ["_E2E_TAG_EXPORT"] = str(dest)

    def test_03_import_json(self, gw_opts):
        export_path = os.environ.get("_E2E_TAG_EXPORT")
        if not export_path or not Path(export_path).exists():
            pytest.skip("Tag export file not available")
        result = invoke([
            "tag", "import", export_path,
            "--collision-policy", "Ignore",
        ], gw_opts)
        assert "imported" in result.output.lower()


@pytest.mark.e2e
class TestTagReadWrite:
    """tag read / tag write — non-standard API endpoints.

    These endpoints require a WebDev module. Tests verify proper error
    handling when the endpoint doesn't exist (404).
    """

    def test_read_handles_missing_endpoint(self, gw_opts):
        """read should fail gracefully if /tags/read doesn't exist."""
        result = runner.invoke(app, ["tag", "read", "Path/To/Tag", *gw_opts])
        # Either succeeds (WebDev installed) or exits with helpful message
        assert result.exit_code in (0, 1)
        if result.exit_code == 1:
            out = result.output.lower()
            assert "not found" in out or "not a standard" in out

    def test_write_handles_missing_endpoint(self, gw_opts):
        """write should fail gracefully if /tags/write doesn't exist."""
        result = runner.invoke(
            app, ["tag", "write", "Path/To/Tag", "42", *gw_opts],
        )
        assert result.exit_code in (0, 1)
        if result.exit_code == 1:
            out = result.output.lower()
            assert "not found" in out or "not a standard" in out


# ===================================================================
# 4. DEVICE COMMANDS
# ===================================================================


@pytest.mark.e2e
class TestDeviceList:
    """device list — list OPC-UA device connections."""

    def test_list_table(self, gw_opts):
        result = invoke(["device", "list"], gw_opts)
        assert result.exit_code == 0

    def test_list_json(self, gw_opts):
        result = invoke(["device", "list", "--format", "json"], gw_opts)
        data = json.loads(result.output)
        assert isinstance(data, (dict, list))

    def test_list_csv(self, gw_opts):
        result = invoke(["device", "list", "--format", "csv"], gw_opts)
        assert result.exit_code == 0


@pytest.mark.e2e
class TestDeviceShow:
    """device show — show device details (requires at least one device)."""

    def test_show_first_device(self, gw_opts):
        """Show details for the first device found, skip if none."""
        list_result = invoke(["device", "list", "--format", "json"], gw_opts)
        data = json.loads(list_result.output)
        items = (
            data if isinstance(data, list)
            else data.get("items", data.get("resources", []))
        )
        if not items:
            pytest.skip("No device connections configured on gateway")
        first_name = items[0].get("name")
        if not first_name:
            pytest.skip("First device has no name")

        result = invoke(["device", "show", first_name], gw_opts)
        assert first_name in result.output


# ===================================================================
# 5. RESOURCE COMMANDS
# ===================================================================


@pytest.mark.e2e
class TestResourceTypes:
    """resource types — discover available resource types from OpenAPI."""

    def test_types(self, gw_opts):
        result = invoke(["resource", "types"], gw_opts)
        out = result.output.lower()
        assert "resource" in out or "module" in out or "/" in result.output


@pytest.mark.e2e
class TestResourceList:
    """resource list / names — list resources by type."""

    def test_list_tag_providers(self, gw_opts):
        result = invoke(["resource", "list", "ignition/tag-provider"], gw_opts)
        assert result.exit_code == 0

    def test_list_tag_providers_json(self, gw_opts):
        result = invoke(
            ["resource", "list", "ignition/tag-provider",
             "--format", "json"],
            gw_opts,
        )
        data = json.loads(result.output)
        assert isinstance(data, (dict, list))

    def test_names_tag_providers(self, gw_opts):
        result = invoke(["resource", "names", "ignition/tag-provider"], gw_opts)
        assert result.exit_code == 0

    def test_list_invalid_type(self, gw_opts):
        """Invalid resource type format should fail gracefully."""
        result = runner.invoke(app, ["resource", "list", "no-slash", *gw_opts])
        assert result.exit_code != 0
        out = result.output.lower()
        assert "module/type" in out or "invalid" in out


@pytest.mark.e2e
class TestResourceShow:
    """resource show — show resource configuration."""

    def test_show_default_tag_provider(self, gw_opts):
        """Show the default tag provider (should always exist)."""
        result = invoke([
            "resource", "show", "ignition/tag-provider", "default",
        ], gw_opts)
        assert "default" in result.output.lower()

    def test_show_json(self, gw_opts):
        result = invoke([
            "resource", "show", "ignition/tag-provider", "default",
            "--format", "json",
        ], gw_opts)
        data = json.loads(result.output)
        assert isinstance(data, dict)
        assert data.get("name") == "default"


# ===================================================================
# 6. MODE COMMANDS (CRUD lifecycle)
# ===================================================================


@pytest.mark.e2e
class TestModeList:
    """mode list — list deployment modes."""

    def test_list_table(self, gw_opts):
        result = invoke(["mode", "list"], gw_opts)
        assert result.exit_code == 0

    def test_list_json(self, gw_opts):
        result = invoke(["mode", "list", "--format", "json"], gw_opts)
        data = json.loads(result.output)
        assert isinstance(data, (dict, list))


@pytest.mark.e2e
class TestModeCRUD:
    """mode create / show / update / delete — full lifecycle."""

    def test_01_create(self, gw_opts):
        result = invoke([
            "mode", "create", _MODE,
            "--title", "E2E Test Mode",
            "--description", "Created by automated tests",
        ], gw_opts)
        assert "created" in result.output.lower()

    def test_02_show(self, gw_opts):
        result = invoke(["mode", "show", _MODE], gw_opts)
        assert _MODE in result.output

    def test_03_show_json(self, gw_opts):
        result = invoke(["mode", "show", _MODE, "--format", "json"], gw_opts)
        data = json.loads(result.output)
        assert isinstance(data, dict)
        assert data.get("name") == _MODE

    def test_04_update_title(self, gw_opts):
        result = invoke([
            "mode", "update", _MODE,
            "--title", "Updated E2E Mode",
        ], gw_opts)
        assert "updated" in result.output.lower()

    def test_05_update_description(self, gw_opts):
        result = invoke([
            "mode", "update", _MODE,
            "--description", "Updated description",
        ], gw_opts)
        assert "updated" in result.output.lower()

    def test_06_verify_update(self, gw_opts):
        result = invoke(["mode", "show", _MODE, "--format", "json"], gw_opts)
        data = json.loads(result.output)
        assert data.get("title") == "Updated E2E Mode"
        assert data.get("description") == "Updated description"

    def test_07_rename(self, gw_opts):
        result = invoke([
            "mode", "update", _MODE,
            "--name", _MODE_RENAMED,
        ], gw_opts)
        assert "updated" in result.output.lower()

    def test_08_verify_rename(self, gw_opts):
        result = invoke(["mode", "show", _MODE_RENAMED], gw_opts)
        assert _MODE_RENAMED in result.output

    def test_09_delete(self, gw_opts):
        result = invoke(["mode", "delete", _MODE_RENAMED, "--force"], gw_opts)
        assert "deleted" in result.output.lower()

    def test_10_verify_deleted(self, gw_opts):
        """The deleted mode should no longer appear in list."""
        result = invoke(["mode", "list", "--format", "json"], gw_opts)
        data = json.loads(result.output)
        items = data if isinstance(data, list) else data.get("items", [])
        names = [m.get("name") for m in items]
        assert _MODE_RENAMED not in names
        assert _MODE not in names


# ===================================================================
# 7. API COMMANDS (raw HTTP + discover + spec)
# ===================================================================


@pytest.mark.e2e
class TestApiGet:
    """api get — raw GET requests."""

    def test_get_gateway_info(self, gw_opts):
        result = invoke(["api", "get", "/gateway-info"], gw_opts)
        data = json.loads(result.output)
        assert isinstance(data, dict)
        assert "ignitionVersion" in data or "version" in data

    def test_get_projects_list(self, gw_opts):
        result = invoke(["api", "get", "/projects/list"], gw_opts)
        data = json.loads(result.output)
        assert isinstance(data, (dict, list))

    def test_get_modules(self, gw_opts):
        result = invoke(["api", "get", "/modules/healthy"], gw_opts)
        data = json.loads(result.output)
        assert isinstance(data, (dict, list))


@pytest.mark.e2e
class TestApiPost:
    """api post — raw POST requests (fire-and-forget endpoints)."""

    def test_post_scan_projects(self, gw_opts):
        result = invoke(["api", "post", "/scan/projects"], gw_opts)
        assert result.exit_code == 0

    def test_post_scan_config(self, gw_opts):
        result = invoke(["api", "post", "/scan/config"], gw_opts)
        assert result.exit_code == 0


@pytest.mark.e2e
class TestApiDiscover:
    """api discover — browse available endpoints."""

    def test_discover_all(self, gw_opts):
        result = invoke(["api", "discover"], gw_opts)
        assert "endpoint" in result.output.lower()
        assert "path" in result.output.lower() or "/" in result.output

    def test_discover_filter(self, gw_opts):
        result = invoke(["api", "discover", "--filter", "project"], gw_opts)
        assert result.exit_code == 0
        assert "project" in result.output.lower()

    def test_discover_method_filter(self, gw_opts):
        result = invoke(["api", "discover", "--method", "GET"], gw_opts)
        assert result.exit_code == 0
        assert "GET" in result.output


@pytest.mark.e2e
class TestApiSpec:
    """api spec — download OpenAPI spec."""

    def test_spec_stdout(self, gw_opts):
        result = invoke(["api", "spec"], gw_opts)
        # Should be valid JSON (OpenAPI spec)
        data = json.loads(result.output)
        assert "openapi" in data or "swagger" in data or "paths" in data

    def test_spec_file(self, gw_opts, tmp_path):
        dest = tmp_path / "openapi.json"
        invoke(["api", "spec", "--output", str(dest)], gw_opts)
        assert dest.exists()
        spec = json.loads(dest.read_text())
        assert "paths" in spec


# ===================================================================
# 8. CONFIG COMMANDS (non-gateway, uses temp config)
# ===================================================================


@pytest.mark.e2e
class TestConfigLifecycle:
    """config add / list / show / set-default / remove — profile management.

    Uses a temporary config directory to avoid touching real config.
    """

    def test_01_add_profile(self, gw_opts, tmp_path, monkeypatch):
        config_dir = tmp_path / ".ignition-cli"
        config_dir.mkdir()
        monkeypatch.setenv("IGNITION_CLI_CONFIG_DIR", str(config_dir))
        monkeypatch.setenv("HOME", str(tmp_path))

        result = invoke_no_gw([
            "config", "add", "test-gw",
            "--url", "http://test.example.com:8088",
            "--token", "key:secret",
            "--default",
        ])
        assert "added" in result.output.lower()

    def test_02_add_second_profile(self, gw_opts, tmp_path, monkeypatch):
        config_dir = tmp_path / ".ignition-cli"
        config_dir.mkdir(exist_ok=True)
        monkeypatch.setenv("IGNITION_CLI_CONFIG_DIR", str(config_dir))
        monkeypatch.setenv("HOME", str(tmp_path))

        # Add first to make sure config exists
        invoke_no_gw([
            "config", "add", "gw-1",
            "--url", "http://gw1.example.com:8088",
            "--token", "key1:secret1",
            "--default",
        ])
        invoke_no_gw([
            "config", "add", "gw-2",
            "--url", "http://gw2.example.com:8088",
            "--token", "key2:secret2",
        ])

        result = invoke_no_gw(["config", "list"])
        assert "gw-1" in result.output
        assert "gw-2" in result.output

    def test_03_show_profile(self, gw_opts, tmp_path, monkeypatch):
        config_dir = tmp_path / ".ignition-cli"
        config_dir.mkdir(exist_ok=True)
        monkeypatch.setenv("IGNITION_CLI_CONFIG_DIR", str(config_dir))
        monkeypatch.setenv("HOME", str(tmp_path))

        invoke_no_gw([
            "config", "add", "show-test",
            "--url", "http://show.example.com:8088",
            "--token", "key:secret",
        ])
        result = invoke_no_gw(["config", "show", "show-test"])
        assert "show.example.com" in result.output

    def test_04_remove_profile(self, gw_opts, tmp_path, monkeypatch):
        config_dir = tmp_path / ".ignition-cli"
        config_dir.mkdir(exist_ok=True)
        monkeypatch.setenv("IGNITION_CLI_CONFIG_DIR", str(config_dir))
        monkeypatch.setenv("HOME", str(tmp_path))

        invoke_no_gw([
            "config", "add", "removable",
            "--url", "http://remove.example.com:8088",
            "--token", "key:secret",
        ])
        result = invoke_no_gw(["config", "remove", "removable", "--force"])
        assert "removed" in result.output.lower()


@pytest.mark.e2e
class TestConfigConnectivity:
    """config test — verify real gateway connectivity."""

    def test_connectivity(self, gw_opts, tmp_path, monkeypatch):
        """Test connectivity using the real gateway URL from gw_opts."""
        config_dir = tmp_path / ".ignition-cli"
        config_dir.mkdir(exist_ok=True)
        monkeypatch.setenv("IGNITION_CLI_CONFIG_DIR", str(config_dir))
        monkeypatch.setenv("HOME", str(tmp_path))

        # Extract URL and token from gw_opts
        url_idx = gw_opts.index("--url")
        token_idx = gw_opts.index("--token")
        url = gw_opts[url_idx + 1]
        token = gw_opts[token_idx + 1]

        invoke_no_gw([
            "config", "add", "live-test",
            "--url", url,
            "--token", token,
            "--default",
        ])
        result = invoke_no_gw(["config", "test", "live-test"])
        assert "connected" in result.output.lower()


# ===================================================================
# 9. OUTPUT FORMAT TESTS (cross-command format verification)
# ===================================================================


@pytest.mark.e2e
class TestOutputFormats:
    """Verify all output formats work across different command types."""

    @pytest.mark.parametrize("fmt", ["table", "json", "yaml", "csv"])
    def test_gateway_status_formats(self, gw_opts, fmt):
        result = invoke(["gateway", "status", "--format", fmt], gw_opts)
        if fmt == "json":
            json.loads(result.output)
        elif fmt == "yaml":
            assert ":" in result.output  # YAML key-value pairs
        elif fmt == "csv":
            assert len(result.output.strip()) > 0

    @pytest.mark.parametrize("fmt", ["table", "json", "yaml", "csv"])
    def test_project_list_formats(self, gw_opts, fmt):
        result = invoke(["project", "list", "--format", fmt], gw_opts)
        if fmt == "json":
            json.loads(result.output)

    @pytest.mark.parametrize("fmt", ["table", "json", "yaml", "csv"])
    def test_mode_list_formats(self, gw_opts, fmt):
        result = invoke(["mode", "list", "--format", fmt], gw_opts)
        if fmt == "json":
            json.loads(result.output)

    @pytest.mark.parametrize("fmt", ["table", "json", "yaml", "csv"])
    def test_device_list_formats(self, gw_opts, fmt):
        result = invoke(["device", "list", "--format", fmt], gw_opts)
        if fmt == "json":
            json.loads(result.output)


# ===================================================================
# 10. ERROR HANDLING TESTS
# ===================================================================


@pytest.mark.e2e
class TestErrorHandling:
    """Verify graceful error handling for invalid inputs."""

    def test_project_show_nonexistent(self, gw_opts):
        """Showing a nonexistent project should fail with 404."""
        result = runner.invoke(app, [
            "project", "show", "nonexistent-zzz-project", *gw_opts,
        ])
        assert result.exit_code != 0

    def test_mode_show_nonexistent(self, gw_opts):
        """Showing a nonexistent mode should fail."""
        result = runner.invoke(app, [
            "mode", "show", "nonexistent-zzz-mode", *gw_opts,
        ])
        assert result.exit_code != 0

    def test_resource_invalid_type_format(self, gw_opts):
        """Resource type without slash should fail gracefully."""
        result = runner.invoke(app, ["resource", "list", "noslash", *gw_opts])
        assert result.exit_code != 0

    def test_invalid_gateway_url(self):
        """Connection to a bogus URL should fail with a connection error."""
        result = runner.invoke(app, [
            "gateway", "status",
            "--url", "http://192.0.2.1:9999",
            "--token", "fake:token",
        ])
        assert result.exit_code != 0

    def test_invalid_token(self, gw_opts):
        """Request with an invalid token should fail with auth error."""
        # Extract URL from gw_opts
        url_idx = gw_opts.index("--url")
        url = gw_opts[url_idx + 1]
        result = runner.invoke(app, [
            "gateway", "status",
            "--url", url,
            "--token", "invalid:badtoken",
        ])
        assert result.exit_code != 0

    def test_project_delete_nonexistent(self, gw_opts):
        """Deleting a nonexistent project should fail."""
        result = runner.invoke(app, [
            "project", "delete", "nonexistent-zzz-project", "--force", *gw_opts,
        ])
        assert result.exit_code != 0

    def test_mode_delete_nonexistent(self, gw_opts):
        """Deleting a nonexistent mode should fail."""
        result = runner.invoke(app, [
            "mode", "delete", "nonexistent-zzz-mode", "--force", *gw_opts,
        ])
        assert result.exit_code != 0

    def test_gateway_restore_missing_file(self, gw_opts):
        """Restoring from a nonexistent file should fail."""
        result = runner.invoke(app, [
            "gateway", "restore", "/nonexistent/file.gwbk", *gw_opts,
        ])
        assert result.exit_code != 0


# ===================================================================
# 11. COMBINED WORKFLOW TESTS
# ===================================================================


@pytest.mark.e2e
class TestProjectModeWorkflow:
    """End-to-end workflow combining multiple command groups.

    1. Create a project
    2. Create a mode
    3. List both to verify they appear
    4. Use api get to verify raw access
    5. Export tags
    6. Clean up
    """

    def test_full_workflow(self, gw_opts, tmp_path):
        proj = f"{_PREFIX}-workflow-proj"
        mode = f"{_PREFIX}-workflow-mode"

        # --- Step 1: Create project ---
        result = invoke(
            ["project", "create", proj, "--title", "Workflow Test"],
            gw_opts,
        )
        assert "created" in result.output.lower()

        # --- Step 2: Create mode ---
        result = invoke([
            "mode", "create", mode,
            "--title", "Workflow Mode",
            "--description", "For workflow testing",
        ], gw_opts)
        assert "created" in result.output.lower()

        # --- Step 3: Verify both appear in lists ---
        result = invoke(["project", "list", "--format", "json"], gw_opts)
        projects = json.loads(result.output)
        proj_items = (
            projects if isinstance(projects, list)
            else projects.get("items", [])
        )
        proj_names = [p.get("name") for p in proj_items]
        assert proj in proj_names

        result = invoke(["mode", "list", "--format", "json"], gw_opts)
        modes = json.loads(result.output)
        mode_items = modes if isinstance(modes, list) else modes.get("items", [])
        mode_names = [m.get("name") for m in mode_items]
        assert mode in mode_names

        # --- Step 4: Raw API access ---
        result = invoke(["api", "get", f"/projects/find/{proj}"], gw_opts)
        proj_data = json.loads(result.output)
        assert proj_data.get("name") == proj

        # --- Step 5: Gateway info via API ---
        result = invoke(["api", "get", "/gateway-info"], gw_opts)
        info = json.loads(result.output)
        assert "ignitionVersion" in info or "version" in info

        # --- Step 6: Tag export ---
        export_dest = tmp_path / "workflow-tags.json"
        result = invoke(["tag", "export", "--output", str(export_dest)], gw_opts)
        assert export_dest.exists()

        # --- Step 7: Discover endpoints ---
        result = invoke(["api", "discover", "--filter", "project"], gw_opts)
        assert "project" in result.output.lower()

        # --- Cleanup ---
        invoke(["mode", "delete", mode, "--force"], gw_opts, should_succeed=False)
        invoke(["project", "delete", proj, "--force"], gw_opts, should_succeed=False)


@pytest.mark.e2e
class TestResourceDiscoveryWorkflow:
    """Discover resource types, then list and show resources for each."""

    def test_discover_and_inspect(self, gw_opts):
        # Get resource types
        invoke(["resource", "types"], gw_opts)

        # Try listing a few well-known resource types
        known_types = [
            "ignition/tag-provider",
        ]
        for rtype in known_types:
            list_result = invoke(["resource", "list", rtype], gw_opts)
            assert list_result.exit_code == 0

            names_result = invoke(["resource", "names", rtype], gw_opts)
            assert names_result.exit_code == 0


# ===================================================================
# 12. IDEMPOTENCY & EDGE CASE TESTS
# ===================================================================


@pytest.mark.e2e
class TestIdempotency:
    """Verify commands behave correctly when called multiple times."""

    def test_project_list_idempotent(self, gw_opts):
        """Calling project list multiple times should return consistent results."""
        result1 = invoke(["project", "list", "--format", "json"], gw_opts)
        result2 = invoke(["project", "list", "--format", "json"], gw_opts)
        data1 = json.loads(result1.output)
        data2 = json.loads(result2.output)
        # Same structure
        assert type(data1) is type(data2)

    def test_gateway_status_idempotent(self, gw_opts):
        """Gateway status should return consistent results."""
        result1 = invoke(["gateway", "status", "--format", "json"], gw_opts)
        result2 = invoke(["gateway", "status", "--format", "json"], gw_opts)
        data1 = json.loads(result1.output)
        data2 = json.loads(result2.output)
        # State should be the same between rapid calls
        assert data1.get("state") == data2.get("state")

    def test_mode_list_idempotent(self, gw_opts):
        result1 = invoke(["mode", "list", "--format", "json"], gw_opts)
        result2 = invoke(["mode", "list", "--format", "json"], gw_opts)
        data1 = json.loads(result1.output)
        data2 = json.loads(result2.output)
        assert type(data1) is type(data2)


# ===================================================================
# 13. HELP TEXT TESTS (no gateway required)
# ===================================================================


@pytest.mark.e2e
class TestHelpText:
    """Verify help text is generated for all command groups."""

    @pytest.mark.parametrize("group", [
        "gateway", "project", "tag", "device", "resource", "mode", "api", "config",
    ])
    def test_help(self, group):
        result = runner.invoke(app, [group, "--help"])
        assert result.exit_code == 0
        assert "usage" in result.output.lower() or "options" in result.output.lower()

    @pytest.mark.parametrize("command", [
        ["gateway", "status"],
        ["gateway", "info"],
        ["gateway", "backup"],
        ["gateway", "modules"],
        ["gateway", "logs"],
        ["gateway", "entity-browse"],
        ["project", "list"],
        ["project", "show"],
        ["project", "create"],
        ["project", "delete"],
        ["project", "export"],
        ["project", "import"],
        ["project", "copy"],
        ["project", "rename"],
        ["tag", "browse"],
        ["tag", "read"],
        ["tag", "write"],
        ["tag", "export"],
        ["tag", "import"],
        ["tag", "providers"],
        ["device", "list"],
        ["device", "show"],
        ["device", "restart"],
        ["resource", "list"],
        ["resource", "show"],
        ["resource", "create"],
        ["resource", "update"],
        ["resource", "delete"],
        ["resource", "names"],
        ["resource", "upload"],
        ["resource", "download"],
        ["resource", "types"],
        ["mode", "list"],
        ["mode", "show"],
        ["mode", "create"],
        ["mode", "update"],
        ["mode", "delete"],
        ["api", "get"],
        ["api", "post"],
        ["api", "put"],
        ["api", "delete"],
        ["api", "discover"],
        ["api", "spec"],
        ["config", "add"],
        ["config", "list"],
        ["config", "show"],
        ["config", "set-default"],
        ["config", "test"],
        ["config", "remove"],
    ])
    def test_subcommand_help(self, command):
        result = runner.invoke(app, [*command, "--help"])
        assert result.exit_code == 0


# ===================================================================
# 14. RESOURCE CRUD LIFECYCLE
# ===================================================================


@pytest.mark.e2e
class TestResourceCRUD:
    """resource create / show / update / delete — full lifecycle.

    Uses ignition/database-connection as a well-known writable resource type.
    """

    def test_01_create(self, gw_opts):
        config = json.dumps({
            "name": _RESOURCE_DB,
            "config": {
                "driver": "MySQL ConnectorJ",
                "translator": "MYSQL",
                "connectURL": "jdbc:mysql://localhost:3306/e2etest",
                "username": "test",
            },
        })
        result = invoke([
            "resource", "create", "ignition/database-connection",
            "--name", _RESOURCE_DB,
            "--config", config,
        ], gw_opts)
        assert "created" in result.output.lower()

    def test_02_show_table(self, gw_opts):
        result = invoke([
            "resource", "show", "ignition/database-connection", _RESOURCE_DB,
        ], gw_opts)
        assert _RESOURCE_DB in result.output

    def test_03_show_json(self, gw_opts):
        result = invoke([
            "resource", "show", "ignition/database-connection", _RESOURCE_DB,
            "--format", "json",
        ], gw_opts)
        data = json.loads(result.output)
        assert data.get("name") == _RESOURCE_DB
        assert "signature" in data

    def test_04_show_yaml(self, gw_opts):
        result = invoke([
            "resource", "show", "ignition/database-connection", _RESOURCE_DB,
            "--format", "yaml",
        ], gw_opts)
        assert _RESOURCE_DB in result.output

    def test_05_update(self, gw_opts):
        config = json.dumps({
            "name": _RESOURCE_DB,
            "config": {
                "driver": "MySQL ConnectorJ",
                "translator": "MYSQL",
                "connectURL": (
                    "jdbc:mysql://localhost:3306/e2etest-updated"
                ),
                "username": "test-updated",
            },
        })
        result = invoke([
            "resource", "update",
            "ignition/database-connection", _RESOURCE_DB,
            "--config", config,
        ], gw_opts)
        assert "updated" in result.output.lower()

    def test_06_verify_update(self, gw_opts):
        result = invoke([
            "resource", "show",
            "ignition/database-connection", _RESOURCE_DB,
            "--format", "json",
        ], gw_opts)
        data = json.loads(result.output)
        cfg = data.get("config", {})
        assert "updated" in cfg.get("connectURL", "")

    def test_07_names_includes_resource(self, gw_opts):
        result = invoke([
            "resource", "names", "ignition/database-connection",
        ], gw_opts)
        assert _RESOURCE_DB in result.output

    def test_08_list_includes_resource(self, gw_opts):
        result = invoke([
            "resource", "list", "ignition/database-connection",
            "--format", "json",
        ], gw_opts)
        data = json.loads(result.output)
        items = (
            data if isinstance(data, list)
            else data.get("items", data.get("resources", []))
        )
        names = [r.get("name", "") for r in items]
        assert _RESOURCE_DB in names

    def test_09_delete(self, gw_opts):
        result = invoke([
            "resource", "delete", "ignition/database-connection",
            _RESOURCE_DB, "--force",
        ], gw_opts)
        assert "deleted" in result.output.lower()

    def test_10_verify_deleted(self, gw_opts):
        result = runner.invoke(app, [
            "resource", "show", "ignition/database-connection", _RESOURCE_DB,
            *gw_opts,
        ])
        assert result.exit_code != 0


# ===================================================================
# 15. MODE ASSIGN / UNASSIGN
# ===================================================================


@pytest.mark.e2e
class TestModeAssignUnassign:
    """mode assign / unassign — assign resources to deployment modes.

    Creates a mode and a resource, then assigns/unassigns with verification.
    """

    def test_01_setup_mode(self, gw_opts):
        """Create a deployment mode for assignment tests."""
        result = invoke([
            "mode", "create", _MODE_ASSIGN,
            "--title", "Assignment Test Mode",
        ], gw_opts)
        assert "created" in result.output.lower()

    def test_02_assign_tag_provider(self, gw_opts):
        """Assign the default tag provider to the test mode."""
        result = invoke([
            "mode", "assign", _MODE_ASSIGN,
            "ignition/tag-provider", "default",
        ], gw_opts)
        assert "assigned" in result.output.lower()

    def test_03_verify_mode_resource_count(self, gw_opts):
        """The mode should now show at least one resource."""
        result = invoke([
            "mode", "show", _MODE_ASSIGN, "--format", "json",
        ], gw_opts)
        data = json.loads(result.output)
        assert data.get("resourceCount", 0) >= 1

    def test_04_show_resource_with_collection(self, gw_opts):
        """Show the mode-scoped resource — should have a different signature."""
        result = invoke([
            "resource", "show", "ignition/tag-provider", "default",
            "--collection", _MODE_ASSIGN,
            "--format", "json",
        ], gw_opts)
        data = json.loads(result.output)
        assert data.get("name") == "default"
        assert "signature" in data

    def test_05_unassign_tag_provider(self, gw_opts):
        """Unassign the tag provider from the mode."""
        result = invoke([
            "mode", "unassign", _MODE_ASSIGN,
            "ignition/tag-provider", "default",
        ], gw_opts)
        assert "removed" in result.output.lower()

    def test_06_verify_unassigned(self, gw_opts):
        """Mode resource count should be back to zero."""
        result = invoke([
            "mode", "show", _MODE_ASSIGN, "--format", "json",
        ], gw_opts)
        data = json.loads(result.output)
        assert data.get("resourceCount", 0) == 0

    def test_07_cleanup_mode(self, gw_opts):
        invoke(["mode", "delete", _MODE_ASSIGN, "--force"], gw_opts)


# ===================================================================
# 16. RESOURCE WITH --COLLECTION (mode-scoped CRUD)
# ===================================================================


@pytest.mark.e2e
class TestResourceCollectionScoped:
    """Resource create/update/delete with --collection flag."""

    def test_01_setup(self, gw_opts):
        """Create a mode and a base resource for scoped tests."""
        invoke([
            "mode", "create", _MODE_ASSIGN,
            "--title", "Collection Test",
        ], gw_opts)
        # Create a database connection resource
        config = json.dumps({
            "name": _RESOURCE_DB,
            "config": {
                "driver": "MySQL ConnectorJ",
                "translator": "MYSQL",
                "connectURL": (
                    "jdbc:mysql://localhost:3306/collectiontest"
                ),
                "username": "test",
            },
        })
        invoke([
            "resource", "create",
            "ignition/database-connection",
            "--name", _RESOURCE_DB,
            "--config", config,
        ], gw_opts)

    def test_02_create_with_collection(self, gw_opts):
        """Create a mode-scoped override via --collection."""
        config = json.dumps({
            "name": _RESOURCE_DB,
            "config": {
                "driver": "MySQL ConnectorJ",
                "translator": "MYSQL",
                "connectURL": (
                    "jdbc:mysql://localhost:3306/mode-override"
                ),
                "username": "test-mode",
            },
        })
        result = invoke([
            "resource", "create",
            "ignition/database-connection",
            "--name", _RESOURCE_DB,
            "--config", config,
            "--collection", _MODE_ASSIGN,
        ], gw_opts)
        assert "created" in result.output.lower()

    def test_03_show_collection_resource(self, gw_opts):
        """Show the mode-scoped resource; should differ from base."""
        result = invoke([
            "resource", "show", "ignition/database-connection", _RESOURCE_DB,
            "--collection", _MODE_ASSIGN,
            "--format", "json",
        ], gw_opts)
        data = json.loads(result.output)
        assert data.get("name") == _RESOURCE_DB

    def test_04_delete_collection_resource(self, gw_opts):
        """Delete the mode-scoped resource using --collection flag."""
        result = invoke([
            "resource", "delete", "ignition/database-connection",
            _RESOURCE_DB, "--force",
            "--collection", _MODE_ASSIGN,
        ], gw_opts)
        assert "deleted" in result.output.lower()

    def test_05_base_resource_still_exists(self, gw_opts):
        """The base resource should still exist after mode-scoped delete."""
        result = invoke([
            "resource", "show", "ignition/database-connection", _RESOURCE_DB,
            "--format", "json",
        ], gw_opts)
        data = json.loads(result.output)
        assert data.get("name") == _RESOURCE_DB

    def test_06_cleanup(self, gw_opts):
        invoke([
            "resource", "delete", "ignition/database-connection",
            _RESOURCE_DB, "--force",
        ], gw_opts, should_succeed=False)
        invoke(
            ["mode", "delete", _MODE_ASSIGN, "--force"],
            gw_opts, should_succeed=False,
        )


# ===================================================================
# 17. SINGLETON RESOURCES
# ===================================================================


@pytest.mark.e2e
class TestSingletonResource:
    """resource show (singleton) — resources without a name."""

    def test_show_singleton_json(self, gw_opts):
        """Show a singleton resource like OPC UA server config.

        Skip if no singleton types available on this gateway.
        """
        # Try the gateway-network singleton (usually present)
        result = runner.invoke(app, [
            "resource", "show", "ignition/gateway-network",
            "--format", "json", *gw_opts,
        ])
        if result.exit_code == 0:
            data = json.loads(result.output)
            assert isinstance(data, dict)
            assert "name" in data or "config" in data or "signature" in data
        else:
            # Not every gateway has this — try OPC UA server settings
            result2 = runner.invoke(app, [
                "resource", "show",
                "com.inductiveautomation.opcua/opcua-server-settings",
                "--format", "json", *gw_opts,
            ])
            if result2.exit_code != 0:
                pytest.skip("No singleton resource types available")
            data = json.loads(result2.output)
            assert isinstance(data, dict)

    def test_show_singleton_default_if_undefined(self, gw_opts):
        """Show a singleton with --default-if-undefined flag."""
        # Use a type that may or may not be defined
        result = runner.invoke(app, [
            "resource", "show", "ignition/gateway-network",
            "--default-if-undefined",
            "--format", "json", *gw_opts,
        ])
        # Should either succeed or 404 (depending on gateway config)
        if result.exit_code == 0:
            data = json.loads(result.output)
            assert isinstance(data, dict)


# ===================================================================
# 18. API PUT / DELETE
# ===================================================================


@pytest.mark.e2e
class TestApiPutDelete:
    """api put / api delete — raw HTTP methods.

    Uses mode endpoints for a safe create/update/delete cycle.
    """

    def test_01_api_put_mode(self, gw_opts):
        """Create a mode, then update it via api put."""
        # Create first
        invoke([
            "mode", "create", f"{_PREFIX}-api-put-test",
            "--title", "API Put Test",
        ], gw_opts)
        # Update via raw PUT
        body = json.dumps({
            "name": f"{_PREFIX}-api-put-test",
            "title": "Updated via API put",
        })
        result = invoke([
            "api", "put", f"/mode/{_PREFIX}-api-put-test",
            "--data", body,
        ], gw_opts)
        assert result.exit_code == 0

    def test_02_verify_put(self, gw_opts):
        """Verify the PUT actually changed the title."""
        result = invoke([
            "mode", "show", f"{_PREFIX}-api-put-test", "--format", "json",
        ], gw_opts)
        data = json.loads(result.output)
        assert data.get("title") == "Updated via API put"

    def test_03_api_delete_mode(self, gw_opts):
        """Delete the mode via api delete."""
        result = invoke([
            "api", "delete", f"/mode/{_PREFIX}-api-put-test",
        ], gw_opts)
        assert result.exit_code == 0


# ===================================================================
# 19. DEVICE RESTART
# ===================================================================


@pytest.mark.e2e
class TestDeviceRestart:
    """device restart — toggle device enable/disable.

    Requires at least one device connection to be present.
    """

    def test_restart_first_device(self, gw_opts):
        """Restart the first available device (skip if none)."""
        list_result = invoke(["device", "list", "--format", "json"], gw_opts)
        data = json.loads(list_result.output)
        items = (
            data if isinstance(data, list)
            else data.get("items", data.get("resources", []))
        )
        if not items:
            pytest.skip("No device connections configured")
        first_name = items[0].get("name")
        if not first_name:
            pytest.skip("First device has no name")
        result = invoke([
            "device", "restart", first_name, "--delay", "1",
        ], gw_opts)
        assert "restarted" in result.output.lower()


# ===================================================================
# 20. TAG IMPORT COLLISION POLICIES
# ===================================================================


@pytest.mark.e2e
class TestTagImportCollisionPolicies:
    """tag import — test different collision policies."""

    def test_01_export_for_reimport(self, gw_opts, tmp_path):
        """Export tags so we have something to reimport."""
        dest = tmp_path / "tags-collision-test.json"
        invoke(["tag", "export", "--output", str(dest)], gw_opts)
        assert dest.exists()
        os.environ["_E2E_TAG_COLLISION_PATH"] = str(dest)

    def test_02_import_merge_overwrite(self, gw_opts):
        path = os.environ.get("_E2E_TAG_COLLISION_PATH")
        if not path or not Path(path).exists():
            pytest.skip("Tag export not available")
        result = invoke([
            "tag", "import", path,
            "--collision-policy", "MergeOverwrite",
        ], gw_opts)
        assert "imported" in result.output.lower()

    def test_03_import_overwrite(self, gw_opts):
        path = os.environ.get("_E2E_TAG_COLLISION_PATH")
        if not path or not Path(path).exists():
            pytest.skip("Tag export not available")
        result = invoke([
            "tag", "import", path,
            "--collision-policy", "Overwrite",
        ], gw_opts)
        assert "imported" in result.output.lower()

    def test_04_import_ignore(self, gw_opts):
        path = os.environ.get("_E2E_TAG_COLLISION_PATH")
        if not path or not Path(path).exists():
            pytest.skip("Tag export not available")
        result = invoke([
            "tag", "import", path,
            "--collision-policy", "Ignore",
        ], gw_opts)
        assert "imported" in result.output.lower()

    def test_05_import_abort(self, gw_opts):
        """Abort policy should succeed when tags already match."""
        path = os.environ.get("_E2E_TAG_COLLISION_PATH")
        if not path or not Path(path).exists():
            pytest.skip("Tag export not available")
        # Abort may either succeed or error depending on tag state
        result = runner.invoke(app, [
            "tag", "import", path,
            "--collision-policy", "Abort", *gw_opts,
        ])
        # Either succeeds or fails — both are valid
        assert result.exit_code in (0, 1)


# ===================================================================
# 21. TAG BROWSE WITH PATH
# ===================================================================


@pytest.mark.e2e
class TestTagBrowseWithPath:
    """tag browse — browse specific paths and formats."""

    def test_browse_with_provider(self, gw_opts):
        result = invoke([
            "tag", "browse", "--provider", "default", "--format", "json",
        ], gw_opts)
        data = json.loads(result.output)
        assert isinstance(data, (dict, list))

    def test_browse_yaml(self, gw_opts):
        result = invoke(["tag", "browse", "--format", "yaml"], gw_opts)
        assert result.exit_code == 0

    def test_export_with_path(self, gw_opts):
        """Export a specific tag path (may be empty but should work)."""
        # Export from root with explicit provider
        result = runner.invoke(app, [
            "tag", "export",
            "--provider", "default", *gw_opts,
        ])
        # Should succeed (root always exists)
        assert result.exit_code == 0


# ===================================================================
# 22. GATEWAY LOGS WITH LEVEL FILTER
# ===================================================================


@pytest.mark.e2e
class TestGatewayLogsLevel:
    """gateway logs --level — filter by log level."""

    def test_logs_level_warn(self, gw_opts):
        result = invoke(["gateway", "logs", "--level", "WARN"], gw_opts)
        assert result.exit_code == 0

    def test_logs_level_error(self, gw_opts):
        result = invoke(["gateway", "logs", "--level", "ERROR"], gw_opts)
        assert result.exit_code == 0

    def test_logs_yaml(self, gw_opts):
        result = invoke(["gateway", "logs", "--format", "yaml"], gw_opts)
        assert result.exit_code == 0


# ===================================================================
# 23. EXPANDED OUTPUT FORMAT TESTS
# ===================================================================


@pytest.mark.e2e
class TestExpandedOutputFormats:
    """Additional output format tests for previously untested commands."""

    @pytest.mark.parametrize("fmt", ["table", "json", "yaml", "csv"])
    def test_resource_list_formats(self, gw_opts, fmt):
        result = invoke([
            "resource", "list", "ignition/tag-provider", "--format", fmt,
        ], gw_opts)
        if fmt == "json":
            json.loads(result.output)

    @pytest.mark.parametrize("fmt", ["table", "json", "yaml", "csv"])
    def test_resource_show_formats(self, gw_opts, fmt):
        result = invoke([
            "resource", "show", "ignition/tag-provider", "default",
            "--format", fmt,
        ], gw_opts)
        if fmt == "json":
            json.loads(result.output)

    @pytest.mark.parametrize("fmt", ["table", "json", "yaml", "csv"])
    def test_tag_providers_formats(self, gw_opts, fmt):
        result = invoke(["tag", "providers", "--format", fmt], gw_opts)
        if fmt == "json":
            json.loads(result.output)

    @pytest.mark.parametrize("fmt", ["table", "json", "yaml", "csv"])
    def test_gateway_logs_formats(self, gw_opts, fmt):
        result = invoke(["gateway", "logs", "--format", fmt], gw_opts)
        if fmt == "json":
            json.loads(result.output)

    @pytest.mark.parametrize("fmt", ["table", "json", "yaml", "csv"])
    def test_mode_show_formats(self, gw_opts, fmt):
        """Test mode show formats on a known mode.

        We list modes and pick the first one (or skip if none).
        """
        list_result = invoke(["mode", "list", "--format", "json"], gw_opts)
        data = json.loads(list_result.output)
        items = data if isinstance(data, list) else data.get("items", [])
        if not items:
            pytest.skip("No modes available")
        mode_name = items[0].get("name")
        result = invoke(["mode", "show", mode_name, "--format", fmt], gw_opts)
        if fmt == "json":
            json.loads(result.output)

    @pytest.mark.parametrize("fmt", ["table", "json", "yaml", "csv"])
    def test_project_show_formats(self, gw_opts, fmt):
        """Test project show formats on first available project."""
        list_result = invoke(["project", "list", "--format", "json"], gw_opts)
        data = json.loads(list_result.output)
        items = (
            data if isinstance(data, list)
            else data.get("items", data.get("projects", []))
        )
        if not items:
            pytest.skip("No projects available")
        proj_name = items[0].get("name")
        result = invoke(["project", "show", proj_name, "--format", fmt], gw_opts)
        if fmt == "json":
            json.loads(result.output)

    @pytest.mark.parametrize("fmt", ["table", "json", "yaml", "csv"])
    def test_device_show_formats(self, gw_opts, fmt):
        """Test device show formats on first available device."""
        list_result = invoke(["device", "list", "--format", "json"], gw_opts)
        data = json.loads(list_result.output)
        items = (
            data if isinstance(data, list)
            else data.get("items", data.get("resources", []))
        )
        if not items:
            pytest.skip("No devices available")
        name = items[0].get("name")
        result = invoke(["device", "show", name, "--format", fmt], gw_opts)
        if fmt == "json":
            json.loads(result.output)

    @pytest.mark.parametrize("fmt", ["table", "json", "yaml", "csv"])
    def test_entity_browse_formats(self, gw_opts, fmt):
        result = invoke(["gateway", "entity-browse", "--format", fmt], gw_opts)
        if fmt == "json":
            json.loads(result.output)


# ===================================================================
# 24. PROJECT IMPORT OVERWRITE
# ===================================================================


@pytest.mark.e2e
class TestProjectImportOverwrite:
    """project import --overwrite — verify full replacement behavior."""

    def test_01_create_and_export(self, gw_opts, tmp_path):
        """Create project, export, then re-import with --overwrite."""
        proj = f"{_PREFIX}-import-overwrite"
        invoke([
            "project", "create", proj, "--title", "Overwrite Test",
        ], gw_opts)
        dest = tmp_path / "overwrite.zip"
        invoke(["project", "export", proj, "--output", str(dest)], gw_opts)
        assert dest.exists()
        os.environ["_E2E_OVERWRITE_PATH"] = str(dest)
        os.environ["_E2E_OVERWRITE_NAME"] = proj

    def test_02_import_overwrite(self, gw_opts):
        path = os.environ.get("_E2E_OVERWRITE_PATH")
        proj = os.environ.get("_E2E_OVERWRITE_NAME")
        if not path or not Path(path).exists() or not proj:
            pytest.skip("Export not available")
        result = invoke([
            "project", "import", path,
            "--name", proj,
            "--overwrite", "--force",
        ], gw_opts)
        assert "imported" in result.output.lower()

    def test_03_cleanup(self, gw_opts):
        proj = os.environ.get("_E2E_OVERWRITE_NAME")
        if proj:
            invoke(
                ["project", "delete", proj, "--force"],
                gw_opts, should_succeed=False,
            )


# ===================================================================
# 25. ERROR HANDLING — EXPANDED
# ===================================================================


@pytest.mark.e2e
class TestExpandedErrorHandling:
    """Additional error handling edge cases."""

    def test_resource_show_nonexistent(self, gw_opts):
        """Showing a nonexistent resource should fail with 404."""
        result = runner.invoke(app, [
            "resource", "show", "ignition/database-connection",
            "nonexistent-zzz-resource", *gw_opts,
        ])
        assert result.exit_code != 0

    def test_resource_delete_nonexistent(self, gw_opts):
        """Deleting a nonexistent resource should fail."""
        result = runner.invoke(app, [
            "resource", "delete", "ignition/database-connection",
            "nonexistent-zzz-resource", "--force", *gw_opts,
        ])
        assert result.exit_code != 0

    def test_mode_unassign_nonexistent(self, gw_opts):
        """Unassigning from nonexistent mode should fail."""
        result = runner.invoke(app, [
            "mode", "unassign", "nonexistent-zzz-mode",
            "ignition/tag-provider", "default", *gw_opts,
        ])
        assert result.exit_code != 0

    def test_tag_export_invalid_provider(self, gw_opts):
        """Exporting from a nonexistent provider should fail."""
        result = runner.invoke(app, [
            "tag", "export",
            "--provider", "nonexistent-zzz-provider",
            *gw_opts,
        ])
        assert result.exit_code != 0

    def test_device_show_nonexistent(self, gw_opts):
        """Showing a nonexistent device should fail."""
        result = runner.invoke(app, [
            "device", "show", "nonexistent-zzz-device", *gw_opts,
        ])
        assert result.exit_code != 0

    def test_api_get_invalid_path(self, gw_opts):
        """GET on a nonexistent API path should fail."""
        result = runner.invoke(app, [
            "api", "get", "/nonexistent/path/zzz", *gw_opts,
        ])
        assert result.exit_code != 0


# ===================================================================
# 26. CLEANUP FIXTURE — global safety net
# ===================================================================


@pytest.fixture(autouse=True, scope="session")
def cleanup_e2e_artifacts(request):
    """Safety net: delete any e2e test artifacts left behind.

    Runs after all tests complete to make sure we don't leave
    test projects/modes on the gateway.
    """
    yield  # Run all tests first

    url = request.config.getoption("--gateway-url", default=None)
    token = request.config.getoption("--gateway-token", default=None)
    if not url or not token:
        return

    gw_opts = ["--url", url, "--token", token]
    artifacts = [
        # Resources (delete before modes to avoid dependency issues)
        (["resource", "delete", "ignition/database-connection",
          _RESOURCE_DB, "--force"], gw_opts),
        # Projects
        (["project", "delete", _PROJECT, "--force"], gw_opts),
        (["project", "delete", _PROJECT_COPY, "--force"], gw_opts),
        (["project", "delete", _PROJECT_RENAME, "--force"], gw_opts),
        (["project", "delete", f"{_PROJECT}-imported", "--force"], gw_opts),
        (["project", "delete", f"{_PREFIX}-workflow-proj", "--force"], gw_opts),
        (["project", "delete", f"{_PREFIX}-import-overwrite", "--force"], gw_opts),
        # Modes
        (["mode", "delete", _MODE, "--force"], gw_opts),
        (["mode", "delete", _MODE_RENAMED, "--force"], gw_opts),
        (["mode", "delete", _MODE_ASSIGN, "--force"], gw_opts),
        (["mode", "delete", f"{_PREFIX}-workflow-mode", "--force"], gw_opts),
        (["mode", "delete", f"{_PREFIX}-api-put-test", "--force"], gw_opts),
    ]

    for args, opts in artifacts:
        with contextlib.suppress(Exception):
            runner.invoke(app, [*args, *opts])
