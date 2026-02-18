"""Shared test fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from ignition_cli.config.manager import ConfigManager
from ignition_cli.config.models import GatewayProfile


def pytest_addoption(parser):
    parser.addoption("--gateway-url", action="store", default=None)
    parser.addoption("--gateway-token", action="store", default=None)


@pytest.fixture
def gw_opts(request):
    url = request.config.getoption("--gateway-url")
    token = request.config.getoption("--gateway-token")
    if not url or not token:
        pytest.skip("Live gateway credentials not provided")
    return ["--url", url, "--token", token]


@pytest.fixture
def tmp_config(tmp_path: Path) -> Path:
    """Return a temporary config file path."""
    return tmp_path / "config.toml"


@pytest.fixture
def config_manager(tmp_config: Path) -> ConfigManager:
    """Return a ConfigManager pointed at a temp config file."""
    return ConfigManager(config_path=tmp_config)


@pytest.fixture
def sample_profile() -> GatewayProfile:
    """Return a sample gateway profile for testing."""
    return GatewayProfile(
        name="test-gw",
        url="https://localhost:8043",
        token="testkey:testsecret",
    )


@pytest.fixture
def mock_gateway_status() -> dict:
    """Sample gateway status response (matches /gateway-info)."""
    return {
        "name": "Test Gateway",
        "ignitionVersion": "8.3.0",
        "edition": "standard",
        "redundancyRole": "Independent",
        "deploymentMode": "",
    }


@pytest.fixture
def mock_gateway_info() -> dict:
    """Sample gateway info response (matches /gateway-info)."""
    return {
        "name": "Test Gateway",
        "ignitionVersion": "8.3.0",
        "edition": "standard",
        "redundancyRole": "Independent",
        "hostname": "localhost",
        "port": "8043",
        "deploymentMode": "",
        "timeZone": "Eastern Standard Time",
        "timeZoneId": "America/New_York",
        "jvmVersion": "17.0.9",
        "allowUnsignedModules": False,
    }


@pytest.fixture
def mock_modules() -> list[dict]:
    """Sample modules list."""
    return [
        {
            "name": "Perspective",
            "id": "com.inductiveautomation.perspective",
            "version": "2.0.0",
            "state": "RUNNING",
        },
        {
            "name": "Vision",
            "id": "com.inductiveautomation.vision",
            "version": "5.0.0",
            "state": "RUNNING",
        },
    ]
