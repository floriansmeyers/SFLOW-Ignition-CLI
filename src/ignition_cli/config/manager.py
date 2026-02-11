"""Configuration manager — read/write TOML config, resolve profiles."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import tomli_w

from ignition_cli.client.errors import ConfigurationError
from ignition_cli.config.constants import (
    CONFIG_FILE,
    ENV_API_TOKEN,
    ENV_GATEWAY_PROFILE,
    ENV_GATEWAY_URL,
)
from ignition_cli.config.models import CLIConfig, GatewayProfile

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


class ConfigManager:
    """Manages CLI configuration on disk and resolves gateway profiles."""

    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or CONFIG_FILE
        self._config: CLIConfig | None = None

    @property
    def config(self) -> CLIConfig:
        if self._config is None:
            self._config = self._load()
        return self._config

    def _load(self) -> CLIConfig:
        if not self.config_path.exists():
            return CLIConfig()
        raw = self.config_path.read_bytes()
        data = tomllib.loads(raw.decode())
        profiles: dict[str, GatewayProfile] = {}
        for name, prof_data in data.get("profiles", {}).items():
            profiles[name] = GatewayProfile(name=name, **prof_data)
        return CLIConfig(
            default_profile=data.get("default_profile"),
            default_format=data.get("default_format", "table"),
            profiles=profiles,
        )

    def save(self) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        # Secure directory permissions (owner-only)
        os.chmod(self.config_path.parent, 0o700)
        data: dict[str, Any] = {}
        if self.config.default_profile:
            data["default_profile"] = self.config.default_profile
        if self.config.default_format != "table":
            data["default_format"] = self.config.default_format
        if self.config.profiles:
            data["profiles"] = {}
            for name, profile in self.config.profiles.items():
                prof_dict = profile.model_dump(exclude={"name"}, exclude_none=True)
                # Remove defaults to keep config clean
                if prof_dict.get("verify_ssl") is True:
                    del prof_dict["verify_ssl"]
                if prof_dict.get("timeout") == 30.0:
                    del prof_dict["timeout"]
                data["profiles"][name] = prof_dict
        # Atomic write: write to temp file, then rename
        temp = self.config_path.with_suffix(".tmp")
        fd = os.open(str(temp), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            os.write(fd, tomli_w.dumps(data).encode())
        finally:
            os.close(fd)
        temp.rename(self.config_path)

    def add_profile(self, profile: GatewayProfile) -> None:
        self.config.profiles[profile.name] = profile
        if not self.config.default_profile:
            self.config.default_profile = profile.name
        self.save()

    def remove_profile(self, name: str) -> bool:
        if name not in self.config.profiles:
            return False
        del self.config.profiles[name]
        if self.config.default_profile == name:
            self.config.default_profile = next(iter(self.config.profiles), None)
        self.save()
        return True

    def set_default(self, name: str) -> bool:
        if name not in self.config.profiles:
            return False
        self.config.default_profile = name
        self.save()
        return True

    def get_profile(self, name: str | None = None) -> GatewayProfile | None:
        if name:
            return self.config.profiles.get(name)
        default = self.config.default_profile
        if default:
            return self.config.profiles.get(default)
        return None

    def resolve_gateway(
        self,
        profile_name: str | None = None,
        url: str | None = None,
        token: str | None = None,
    ) -> GatewayProfile:
        """Resolve gateway connection.

        Precedence: CLI flags > env vars > config profile.
        """
        # Start from config profile
        env_profile = os.environ.get(ENV_GATEWAY_PROFILE)
        profile = self.get_profile(profile_name or env_profile)

        env_url = os.environ.get(ENV_GATEWAY_URL)
        env_token = os.environ.get(ENV_API_TOKEN)

        resolved_url = url or env_url or (profile.url if profile else None)
        resolved_token = token or env_token or (profile.token if profile else None)

        if not resolved_url:
            raise ConfigurationError(
                "No gateway URL configured. Use 'ignition-cli config add' or set "
                f"{ENV_GATEWAY_URL} or pass --url."
            )

        return GatewayProfile(
            name=profile.name if profile else "cli",
            url=resolved_url.rstrip("/"),
            token=resolved_token,
            username=profile.username if profile else None,
            password=profile.password if profile else None,
            verify_ssl=profile.verify_ssl if profile else True,
            timeout=profile.timeout if profile else 30.0,
        )
