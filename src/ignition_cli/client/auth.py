"""Authentication strategies for the Ignition gateway."""

from __future__ import annotations

from collections.abc import Generator

import httpx

from ignition_cli.config.models import GatewayProfile


class APITokenAuth(httpx.Auth):
    """Authenticate using an Ignition API token (X-Ignition-API-Token header)."""

    def __init__(self, token: str) -> None:
        self.token = token

    def auth_flow(
        self, request: httpx.Request,
    ) -> Generator[httpx.Request, httpx.Response, None]:
        request.headers["X-Ignition-API-Token"] = self.token
        yield request


class BasicAuth(httpx.BasicAuth):
    """HTTP Basic auth wrapper."""


def resolve_auth(profile: GatewayProfile) -> httpx.Auth | None:
    """Resolve authentication from a gateway profile."""
    if profile.token:
        return APITokenAuth(profile.token)
    if profile.username and profile.password:
        import sys

        print(
            "Warning: Using HTTP Basic auth. The Ignition 8.3 REST API"
            " only supports API token authentication"
            " (X-Ignition-API-Token). Basic auth will likely fail"
            " with a 401 error. Use 'config add' with --token instead.",
            file=sys.stderr,
        )
        return BasicAuth(profile.username, profile.password)
    return None
