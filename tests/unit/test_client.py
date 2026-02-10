"""Tests for the gateway client."""

import httpx
import pytest
import respx

from ignition_cli.client.auth import APITokenAuth, BasicAuth, resolve_auth
from ignition_cli.client.errors import (
    AuthenticationError,
    GatewayAPIError,
    NotFoundError,
)
from ignition_cli.client.gateway import GatewayClient
from ignition_cli.config.models import GatewayProfile


class TestAuth:
    def test_api_token_auth(self):
        auth = APITokenAuth("key:secret")
        request = httpx.Request("GET", "https://example.com")
        flow = auth.auth_flow(request)
        modified = next(flow)
        assert modified.headers["X-Ignition-API-Token"] == "key:secret"

    def test_resolve_auth_token(self):
        profile = GatewayProfile(name="t", url="https://gw:8043", token="k:s")
        auth = resolve_auth(profile)
        assert isinstance(auth, APITokenAuth)

    def test_resolve_auth_basic(self):
        profile = GatewayProfile(
            name="t", url="https://gw:8043",
            username="admin", password="pass",
        )
        auth = resolve_auth(profile)
        assert isinstance(auth, BasicAuth)

    def test_resolve_auth_none(self):
        profile = GatewayProfile(name="t", url="https://gw:8043")
        assert resolve_auth(profile) is None


class TestGatewayClient:
    @respx.mock
    def test_get_json(self):
        profile = GatewayProfile(
            name="test", url="https://gw:8043",
            token="k:s", verify_ssl=False,
        )
        respx.get("https://gw:8043/data/api/v1/status").mock(
            return_value=httpx.Response(200, json={"state": "RUNNING"})
        )
        with GatewayClient(profile) as client:
            data = client.get_json("/status")
            assert data == {"state": "RUNNING"}

    @respx.mock
    def test_auth_error(self):
        profile = GatewayProfile(
            name="test", url="https://gw:8043",
            token="bad:token", verify_ssl=False,
        )
        respx.get("https://gw:8043/data/api/v1/status").mock(
            return_value=httpx.Response(401, json={"message": "Unauthorized"})
        )
        with GatewayClient(profile) as client, pytest.raises(AuthenticationError):
            client.get("/status")

    @respx.mock
    def test_not_found(self):
        profile = GatewayProfile(
            name="test", url="https://gw:8043",
            token="k:s", verify_ssl=False,
        )
        respx.get("https://gw:8043/data/api/v1/nope").mock(
            return_value=httpx.Response(404, json={"message": "Not found"})
        )
        with GatewayClient(profile) as client, pytest.raises(NotFoundError):
            client.get("/nope")

    @respx.mock
    def test_server_error(self):
        profile = GatewayProfile(
            name="test", url="https://gw:8043",
            token="k:s", verify_ssl=False,
        )
        respx.get("https://gw:8043/data/api/v1/broken").mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )
        with GatewayClient(profile) as client, pytest.raises(GatewayAPIError):
            client.get("/broken")

    @respx.mock
    def test_post(self):
        profile = GatewayProfile(
            name="test", url="https://gw:8043",
            token="k:s", verify_ssl=False,
        )
        respx.post("https://gw:8043/data/api/v1/resource").mock(
            return_value=httpx.Response(201, json={"id": "new"})
        )
        with GatewayClient(profile) as client:
            resp = client.post("/resource", json={"name": "test"})
            assert resp.json() == {"id": "new"}
