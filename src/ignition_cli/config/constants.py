"""Default paths, environment variable names, and constants."""

from __future__ import annotations

import platformdirs

APP_NAME = "ignition-cli"
APP_AUTHOR = "SFLOW"

CONFIG_DIR = platformdirs.user_config_path(APP_NAME, APP_AUTHOR)
CONFIG_FILE = CONFIG_DIR / "config.toml"

# Environment variable names
ENV_GATEWAY_URL = "IGNITION_GATEWAY_URL"
ENV_API_TOKEN = "IGNITION_API_TOKEN"
ENV_GATEWAY_PROFILE = "IGNITION_GATEWAY_PROFILE"

# API defaults
DEFAULT_API_BASE = "/data/api/v1"
DEFAULT_TIMEOUT = 30.0
DEFAULT_MAX_RETRIES = 3
