from dataclasses import dataclass
from typing import Any


@dataclass
class HTTPRequest:
    """Unified HTTP request structure.

    Attributes:
        url: The URL for the request.
        method: The HTTP method (e.g., 'GET', 'POST').
        header: Dictionary of HTTP headers.
        path: Dictionary of path parameters.
        query: Dictionary of query parameters.
        body: Dictionary of body parameters (JSON/Form).
        file: Dictionary of files to upload.
        form: Dictionary of form_data parameters.
    """
    url: str
    method: str

    header: dict[str, str]
    path: dict[str, str]
    query: dict[str, Any]
    body: Any
    file: dict[str, Any]
    form: Any
