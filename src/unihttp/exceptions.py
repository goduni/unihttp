"""Unified exceptions for unihttp."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from unihttp.http.response import HTTPResponse


class UniHTTPError(Exception):
    """Base exception for all unihttp errors."""


# Transport errors (network level)
class NetworkError(UniHTTPError):
    """Connection failed, DNS error, etc."""


class RequestTimeoutError(UniHTTPError):
    """Request timed out."""


# Application errors (HTTP status based)
class HTTPStatusError(UniHTTPError):
    """Raised for HTTP error responses."""

    def __init__(self, message: str, response: HTTPResponse) -> None:
        super().__init__(message)
        self.response = response
        self.status_code = response.status_code


class ClientError(HTTPStatusError):
    """4xx client errors."""


class ServerError(HTTPStatusError):
    """5xx server errors."""
