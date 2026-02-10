"""Gateway HTTP client."""

from __future__ import annotations

from typing import Any

import httpx

from ignition_cli.client.auth import resolve_auth
from ignition_cli.client.errors import (
    AuthenticationError,
    ConflictError,
    GatewayAPIError,
    GatewayConnectionError,
    NotFoundError,
)
from ignition_cli.config.constants import DEFAULT_API_BASE
from ignition_cli.config.models import GatewayProfile


class GatewayClient:
    """Synchronous HTTP client for the Ignition REST API."""

    def __init__(self, profile: GatewayProfile) -> None:
        self.profile = profile
        self.base_url = f"{profile.url}{DEFAULT_API_BASE}"
        auth = resolve_auth(profile)
        transport = httpx.HTTPTransport(retries=3)
        self._client = httpx.Client(
            base_url=self.base_url,
            auth=auth,
            verify=profile.verify_ssl,
            timeout=profile.timeout,
            transport=transport,
            headers={"Accept": "application/json"},
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> GatewayClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def _handle_response(self, response: httpx.Response) -> httpx.Response:
        if response.is_success:
            return response
        status = response.status_code
        try:
            detail = response.json().get("message", response.text)
        except Exception:
            detail = response.text
        if status in (401, 403):
            raise AuthenticationError(f"Authentication failed: {detail}")
        if status == 404:
            raise NotFoundError(f"Not found: {detail}")
        if status == 409:
            raise ConflictError(f"Conflict: {detail}")
        raise GatewayAPIError(status, detail)

    def request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        try:
            response = self._client.request(method, path, **kwargs)
        except httpx.ConnectError as exc:
            raise GatewayConnectionError(
                f"Cannot connect to gateway at {self.profile.url}: {exc}"
            ) from exc
        except httpx.TimeoutException as exc:
            raise GatewayConnectionError(
                f"Request to {self.profile.url} timed out: {exc}"
            ) from exc
        return self._handle_response(response)

    def get(self, path: str, **kwargs: Any) -> httpx.Response:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> httpx.Response:
        return self.request("POST", path, **kwargs)

    def put(self, path: str, **kwargs: Any) -> httpx.Response:
        return self.request("PUT", path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> httpx.Response:
        return self.request("DELETE", path, **kwargs)

    def get_json(self, path: str, **kwargs: Any) -> Any:
        return self.get(path, **kwargs).json()
