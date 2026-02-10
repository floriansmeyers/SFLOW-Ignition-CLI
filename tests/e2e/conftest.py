"""E2E test configuration — custom CLI options for live gateway."""

from __future__ import annotations

import pytest


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
