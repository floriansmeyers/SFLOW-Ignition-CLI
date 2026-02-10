"""Tests for config manager."""

import os

import pytest

from ignition_cli.config.manager import ConfigManager
from ignition_cli.config.models import GatewayProfile


class TestConfigManager:
    def test_load_empty(self, config_manager: ConfigManager):
        assert config_manager.config.profiles == {}
        assert config_manager.config.default_profile is None

    def test_add_profile(self, config_manager: ConfigManager, sample_profile: GatewayProfile):
        config_manager.add_profile(sample_profile)
        assert "test-gw" in config_manager.config.profiles
        assert config_manager.config.default_profile == "test-gw"

    def test_add_sets_first_as_default(self, config_manager: ConfigManager):
        p1 = GatewayProfile(name="first", url="https://first:8043")
        p2 = GatewayProfile(name="second", url="https://second:8043")
        config_manager.add_profile(p1)
        config_manager.add_profile(p2)
        assert config_manager.config.default_profile == "first"

    def test_remove_profile(self, config_manager: ConfigManager, sample_profile: GatewayProfile):
        config_manager.add_profile(sample_profile)
        assert config_manager.remove_profile("test-gw") is True
        assert "test-gw" not in config_manager.config.profiles

    def test_remove_nonexistent(self, config_manager: ConfigManager):
        assert config_manager.remove_profile("nope") is False

    def test_remove_default_reassigns(self, config_manager: ConfigManager):
        p1 = GatewayProfile(name="a", url="https://a:8043")
        p2 = GatewayProfile(name="b", url="https://b:8043")
        config_manager.add_profile(p1)
        config_manager.add_profile(p2)
        config_manager.set_default("a")
        config_manager.remove_profile("a")
        assert config_manager.config.default_profile == "b"

    def test_set_default(self, config_manager: ConfigManager):
        p = GatewayProfile(name="dev", url="https://dev:8043")
        config_manager.add_profile(p)
        assert config_manager.set_default("dev") is True
        assert config_manager.config.default_profile == "dev"

    def test_set_default_nonexistent(self, config_manager: ConfigManager):
        assert config_manager.set_default("nope") is False

    def test_get_profile(self, config_manager: ConfigManager, sample_profile: GatewayProfile):
        config_manager.add_profile(sample_profile)
        p = config_manager.get_profile("test-gw")
        assert p is not None
        assert p.name == "test-gw"

    def test_get_default_profile(self, config_manager: ConfigManager, sample_profile: GatewayProfile):
        config_manager.add_profile(sample_profile)
        p = config_manager.get_profile()
        assert p is not None
        assert p.name == "test-gw"

    def test_save_and_reload(self, config_manager: ConfigManager, sample_profile: GatewayProfile):
        config_manager.add_profile(sample_profile)
        # Create a new manager pointing to the same file to test persistence
        mgr2 = ConfigManager(config_path=config_manager.config_path)
        p = mgr2.get_profile("test-gw")
        assert p is not None
        assert p.url == "https://localhost:8043"
        assert p.token == "testkey:testsecret"

    def test_resolve_gateway_from_profile(self, config_manager: ConfigManager, sample_profile: GatewayProfile):
        config_manager.add_profile(sample_profile)
        resolved = config_manager.resolve_gateway()
        assert resolved.url == "https://localhost:8043"
        assert resolved.token == "testkey:testsecret"

    def test_resolve_gateway_cli_overrides(self, config_manager: ConfigManager, sample_profile: GatewayProfile):
        config_manager.add_profile(sample_profile)
        resolved = config_manager.resolve_gateway(url="https://other:8043", token="new:token")
        assert resolved.url == "https://other:8043"
        assert resolved.token == "new:token"

    def test_resolve_gateway_env_vars(self, config_manager: ConfigManager, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("IGNITION_GATEWAY_URL", "https://env-gw:8043")
        monkeypatch.setenv("IGNITION_API_TOKEN", "env:token")
        resolved = config_manager.resolve_gateway()
        assert resolved.url == "https://env-gw:8043"
        assert resolved.token == "env:token"

    def test_resolve_gateway_no_url_raises(self, config_manager: ConfigManager):
        from ignition_cli.client.errors import ConfigurationError

        with pytest.raises(ConfigurationError, match="No gateway URL configured"):
            config_manager.resolve_gateway()
