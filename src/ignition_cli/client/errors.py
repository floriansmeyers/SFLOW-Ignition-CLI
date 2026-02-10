"""Typed exceptions and error handling decorator."""

from __future__ import annotations

import functools
from collections.abc import Callable
from typing import Any, TypeVar

from rich.console import Console

F = TypeVar("F", bound=Callable[..., Any])

err_console = Console(stderr=True)


class IgnitionCLIError(Exception):
    """Base exception for ignition-cli."""

    exit_code: int = 1


class GatewayConnectionError(IgnitionCLIError):
    """Cannot connect to the gateway."""

    exit_code = 2


class AuthenticationError(IgnitionCLIError):
    """Authentication failed (401/403)."""

    exit_code = 3


class NotFoundError(IgnitionCLIError):
    """Resource not found (404)."""

    exit_code = 4


class ConflictError(IgnitionCLIError):
    """Resource conflict (409)."""

    exit_code = 5


class ConfigurationError(IgnitionCLIError):
    """Missing or invalid CLI configuration."""

    exit_code = 6


class GatewayAPIError(IgnitionCLIError):
    """Generic API error from the gateway."""

    def __init__(self, status_code: int, detail: str = "") -> None:
        self.status_code = status_code
        super().__init__(f"Gateway returned {status_code}: {detail}")


def error_handler(func: F) -> F:
    """Decorator that catches IgnitionCLIError and prints user-friendly messages."""

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except IgnitionCLIError as exc:
            err_console.print(f"[bold red]Error:[/] {exc}")
            raise SystemExit(exc.exit_code) from exc

    return wrapper  # type: ignore[return-value]
