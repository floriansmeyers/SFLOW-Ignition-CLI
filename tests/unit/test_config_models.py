"""Tests for config models."""

from ignition_cli.config.models import CLIConfig, GatewayProfile


class TestGatewayProfile:
    def test_create_with_token(self):
        p = GatewayProfile(name="test", url="https://gw:8043", token="key:secret")
        assert p.name == "test"
        assert p.url == "https://gw:8043"
        assert p.token == "key:secret"
        assert p.auth_configured is True

    def test_create_with_basic_auth(self):
        p = GatewayProfile(
            name="test", url="https://gw:8043",
            username="admin", password="pass",
        )
        assert p.auth_configured is True

    def test_create_no_auth(self):
        p = GatewayProfile(name="test", url="https://gw:8043")
        assert p.auth_configured is False

    def test_defaults(self):
        p = GatewayProfile(name="test", url="https://gw:8043")
        assert p.verify_ssl is True
        assert p.timeout == 30.0
        assert p.username is None
        assert p.password is None


class TestCLIConfig:
    def test_empty_config(self):
        c = CLIConfig()
        assert c.default_profile is None
        assert c.default_format == "table"
        assert c.profiles == {}

    def test_config_with_profiles(self):
        p = GatewayProfile(name="dev", url="https://dev:8043")
        c = CLIConfig(default_profile="dev", profiles={"dev": p})
        assert c.default_profile == "dev"
        assert "dev" in c.profiles
