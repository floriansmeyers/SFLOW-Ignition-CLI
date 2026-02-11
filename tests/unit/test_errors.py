"""Tests for error_handler and custom exceptions."""

from __future__ import annotations

import pytest

from ignition_cli.client.errors import (
    AuthenticationError,
    ConfigurationError,
    ConflictError,
    GatewayAPIError,
    GatewayConnectionError,
    IgnitionCLIError,
    NotFoundError,
    ValidationError,
    error_handler,
)


class TestExceptionHierarchy:
    def test_base_error(self):
        exc = IgnitionCLIError("test")
        assert str(exc) == "test"
        assert exc.exit_code == 1

    def test_connection_error(self):
        exc = GatewayConnectionError("cannot connect")
        assert isinstance(exc, IgnitionCLIError)
        assert exc.exit_code == 2

    def test_auth_error(self):
        exc = AuthenticationError("denied")
        assert isinstance(exc, IgnitionCLIError)
        assert exc.exit_code == 3

    def test_not_found_error(self):
        exc = NotFoundError("missing")
        assert isinstance(exc, IgnitionCLIError)
        assert exc.exit_code == 4

    def test_conflict_error(self):
        exc = ConflictError("conflict")
        assert isinstance(exc, IgnitionCLIError)
        assert exc.exit_code == 5

    def test_configuration_error(self):
        exc = ConfigurationError("no url")
        assert isinstance(exc, IgnitionCLIError)
        assert exc.exit_code == 6

    def test_validation_error(self):
        exc = ValidationError("name too long")
        assert isinstance(exc, IgnitionCLIError)
        assert exc.exit_code == 7
        assert "name too long" in str(exc)

    def test_validation_error_empty(self):
        exc = ValidationError()
        assert "Validation error" in str(exc)

    def test_api_error(self):
        exc = GatewayAPIError(500, "server error")
        assert isinstance(exc, IgnitionCLIError)
        assert exc.status_code == 500
        assert "500" in str(exc)
        assert "server error" in str(exc)


class TestErrorHandler:
    def test_catches_ignition_error(self):
        @error_handler
        def raises_auth():
            raise AuthenticationError("bad token")

        with pytest.raises(SystemExit) as exc_info:
            raises_auth()
        assert exc_info.value.code == 3

    def test_catches_configuration_error(self):
        @error_handler
        def raises_config():
            raise ConfigurationError("no url")

        with pytest.raises(SystemExit) as exc_info:
            raises_config()
        assert exc_info.value.code == 6

    def test_passes_through_normal_return(self):
        @error_handler
        def returns_value():
            return 42

        assert returns_value() == 42

    def test_does_not_catch_other_exceptions(self):
        @error_handler
        def raises_type_error():
            raise TypeError("bad type")

        with pytest.raises(TypeError):
            raises_type_error()
