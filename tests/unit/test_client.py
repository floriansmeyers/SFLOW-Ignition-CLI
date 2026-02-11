"""Tests for the gateway client."""

from pathlib import Path

import httpx
import pytest
import respx

from ignition_cli.client.auth import APITokenAuth, BasicAuth, resolve_auth
from ignition_cli.client.errors import (
    AuthenticationError,
    GatewayAPIError,
    IgnitionCLIError,
    NotFoundError,
    ValidationError,
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
        with GatewayClient(profile) as client, pytest.raises(
            AuthenticationError, match="Check your API token",
        ):
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
    def test_auth_error_http_hint(self):
        """401 over http:// should include HTTPS hint."""
        profile = GatewayProfile(
            name="test", url="http://gw:8088",
            token="bad:token", verify_ssl=False,
        )
        respx.get("http://gw:8088/data/api/v1/status").mock(
            return_value=httpx.Response(401, json={"message": "Unauthorized"})
        )
        with GatewayClient(profile) as client, pytest.raises(
            AuthenticationError, match="Require secure connections",
        ):
            client.get("/status")

    @respx.mock
    def test_validation_error_422(self):
        """422 should raise ValidationError with detail."""
        profile = GatewayProfile(
            name="test", url="https://gw:8043",
            token="k:s", verify_ssl=False,
        )
        respx.post("https://gw:8043/data/api/v1/resources/ignition/test").mock(
            return_value=httpx.Response(
                422, json={"message": "Name exceeds 255 characters"},
            )
        )
        with GatewayClient(profile) as client, pytest.raises(
            ValidationError, match="255 characters",
        ):
            client.post("/resources/ignition/test", json=[{"name": "x" * 300}])

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


class TestStreamToFile:
    @respx.mock
    def test_stream_to_file_atomic(self, tmp_path: Path):
        """stream_to_file writes to .partial temp, then renames."""
        profile = GatewayProfile(
            name="test", url="https://gw:8043",
            token="k:s", verify_ssl=False,
        )
        respx.get("https://gw:8043/data/api/v1/backup").mock(
            return_value=httpx.Response(200, content=b"\x00GWBK")
        )
        dest = tmp_path / "backup.gwbk"
        with GatewayClient(profile) as client:
            total = client.stream_to_file("/backup", dest)
        assert total == 5
        assert dest.read_bytes() == b"\x00GWBK"
        # Partial file should be cleaned up
        assert not dest.with_suffix(".gwbk.partial").exists()

    @respx.mock
    def test_stream_to_file_empty_raises(self, tmp_path: Path):
        """Empty response should raise IgnitionCLIError."""
        profile = GatewayProfile(
            name="test", url="https://gw:8043",
            token="k:s", verify_ssl=False,
        )
        respx.get("https://gw:8043/data/api/v1/empty").mock(
            return_value=httpx.Response(200, content=b"")
        )
        dest = tmp_path / "empty.bin"
        with GatewayClient(profile) as client, pytest.raises(
            IgnitionCLIError, match="Empty response",
        ):
            client.stream_to_file("/empty", dest)
        # Partial file should be cleaned up
        assert not dest.with_suffix(".bin.partial").exists()


class TestStreamUpload:
    @respx.mock
    def test_stream_upload(self, tmp_path: Path):
        """stream_upload should send file content via streaming."""
        profile = GatewayProfile(
            name="test", url="https://gw:8043",
            token="k:s", verify_ssl=False,
        )
        route = respx.post("https://gw:8043/data/api/v1/backup").mock(
            return_value=httpx.Response(200, json={})
        )
        file_path = tmp_path / "upload.gwbk"
        file_path.write_bytes(b"\x00GWBK-DATA")
        with GatewayClient(profile) as client:
            resp = client.stream_upload("POST", "/backup", file_path)
        assert resp.status_code == 200
        assert route.call_count == 1


class TestPagination:
    @respx.mock
    def test_get_all_items_does_not_mutate_caller_params(self):
        """Pagination should not mutate the caller's params dict."""
        profile = GatewayProfile(
            name="test", url="https://gw:8043",
            token="k:s", verify_ssl=False,
        )
        respx.get("https://gw:8043/data/api/v1/items").mock(
            return_value=httpx.Response(200, json=[{"id": 1}])
        )
        caller_params = {"filter": "active"}
        with GatewayClient(profile) as client:
            client.get_all_items("/items", params=caller_params)
        # Original dict should not be mutated with limit/offset
        assert caller_params == {"filter": "active"}
