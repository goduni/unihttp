from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass
class HTTPResponse:
    """Unified HTTP response structure.

    Attributes:
        status_code: The HTTP status code of the response.
        headers: Dictionary of response headers.
        data: The parsed response data (usually JSON).
        cookies: Dictionary of response cookies.
        raw_response: The original response object from the underlying client
                      (e.g., httpx.Response).
    """
    status_code: int

    headers: Mapping[str, Any]
    data: Any
    cookies: Mapping[str, Any]

    raw_response: Any

    @property
    def ok(self) -> bool:
        """Check if response status code is 2xx."""
        return 200 <= self.status_code < 300

    @property
    def is_client_error(self) -> bool:
        """Check if response status code is 4xx."""
        return 400 <= self.status_code < 500

    @property
    def is_server_error(self) -> bool:
        """Check if response status code is 5xx."""
        return 500 <= self.status_code < 600
