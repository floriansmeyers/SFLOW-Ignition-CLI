"""Gateway HTTP client."""

from __future__ import annotations

import json
from pathlib import Path
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
from ignition_cli.config.constants import DEFAULT_API_BASE, DEFAULT_MAX_RETRIES
from ignition_cli.config.models import GatewayProfile


class GatewayClient:
    """Synchronous HTTP client for the Ignition REST API."""

    def __init__(self, profile: GatewayProfile) -> None:
        self.profile = profile
        self.base_url = f"{profile.url}{DEFAULT_API_BASE}"
        auth = resolve_auth(profile)
        transport = httpx.HTTPTransport(retries=DEFAULT_MAX_RETRIES)
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
        except (json.JSONDecodeError, KeyError):
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
        resp = self.get(path, **kwargs)
        try:
            return resp.json()
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Fallback: decode with replacement for non-UTF8 responses
            text = resp.content.decode("utf-8", errors="replace")
            return json.loads(text)

    def get_all_items(
        self,
        path: str,
        *,
        limit: int = 100,
        **kwargs: Any,
    ) -> list[Any]:
        """Auto-paginate through a list endpoint, returning all items."""
        all_items: list[Any] = []
        offset = 0
        while True:
            params = kwargs.pop("params", {})
            params.update({"limit": limit, "offset": offset})
            data = self.get_json(path, params=params, **kwargs)
            if isinstance(data, list):
                all_items.extend(data)
                break  # non-paginated response
            items = data.get("items", [])
            all_items.extend(items)
            metadata = data.get("metadata", {})
            total = metadata.get("total") or metadata.get("matching")
            if total is None or offset + limit >= total or not items:
                break
            offset += limit
        return all_items

    def stream_to_file(self, path: str, dest: Path, **kwargs: Any) -> int:
        """Stream a response body to a file, returning bytes written."""
        try:
            with self._client.stream("GET", path, **kwargs) as response:
                if response.status_code >= 400:
                    response.read()  # must read body before _handle_response
                self._handle_response(response)
                total = 0
                with open(dest, "wb") as f:
                    for chunk in response.iter_bytes(chunk_size=8192):
                        f.write(chunk)
                        total += len(chunk)
                return total
        except httpx.ConnectError as exc:
            raise GatewayConnectionError(
                f"Cannot connect to gateway at {self.profile.url}: {exc}"
            ) from exc
        except httpx.TimeoutException as exc:
            raise GatewayConnectionError(
                f"Request to {self.profile.url} timed out: {exc}"
            ) from exc

    def get_openapi_spec(self) -> dict:
        """Fetch the OpenAPI spec from the gateway root URL (with auth)."""
        url = f"{self.profile.url}/openapi.json"
        try:
            response = self._client.get(url)
        except httpx.ConnectError as exc:
            raise GatewayConnectionError(
                f"Cannot connect to gateway at {self.profile.url}: {exc}"
            ) from exc
        except httpx.TimeoutException as exc:
            raise GatewayConnectionError(
                f"Request to {self.profile.url} timed out: {exc}"
            ) from exc
        return self._handle_response(response).json()
