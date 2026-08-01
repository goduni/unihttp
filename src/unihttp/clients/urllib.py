import http.client
import json
import urllib.error
import urllib.request
import uuid
from collections.abc import Callable
from http.cookies import SimpleCookie
from typing import Any
from urllib.parse import urlencode, urljoin

from unihttp.clients.base import BaseSyncClient
from unihttp.exceptions import NetworkError, RequestTimeoutError
from unihttp.http import UploadFile
from unihttp.http.request import HTTPRequest
from unihttp.http.response import HTTPResponse
from unihttp.http.stream import ChunkStream
from unihttp.middlewares.base import Middleware
from unihttp.serialize import RequestDumper, ResponseLoader

_UrllibResponse = http.client.HTTPResponse | urllib.error.HTTPError


class _UrllibChunkStream(ChunkStream):
    def __init__(self, raw: _UrllibResponse, chunk_size: int) -> None:
        super().__init__()
        self._raw = raw
        self._chunk_size = chunk_size

    def _fetch_chunk(self) -> bytes:
        try:
            chunk = self._raw.read(self._chunk_size)
        except TimeoutError as e:
            raise RequestTimeoutError(str(e)) from e
        except (OSError, http.client.HTTPException) as e:
            raise NetworkError(str(e)) from e
        if not chunk:
            raise StopIteration
        return chunk

    def _close_response(self) -> None:
        self._raw.close()


class UrllibSyncClient(BaseSyncClient):
    """Synchronous client implementation using the standard library `urllib`.

    Requires no third-party HTTP dependency — handy for constrained or
    dependency-free environments. For anything demanding, prefer a real backend
    such as `requests`, `httpx` or `niquests`.
    """

    def __init__(
        self,
        base_url: str,
        request_dumper: RequestDumper,
        response_loader: ResponseLoader,
        middleware: list[Middleware] | None = None,
        opener: urllib.request.OpenerDirector | None = None,
        timeout: float | None = None,
        json_dumps: Callable[[Any], str] = json.dumps,
        json_loads: Callable[[str | bytes | bytearray], Any] = json.loads,
    ):
        super().__init__(
            base_url=base_url,
            request_dumper=request_dumper,
            response_loader=response_loader,
            middleware=middleware,
            json_dumps=json_dumps,
            json_loads=json_loads,
        )

        self._opener = opener if opener is not None else urllib.request.build_opener()
        self._timeout = timeout

    def _normalize_file(self, key: str, item: Any) -> tuple[str, str | None, bytes, str]:
        """Normalize a single file entry to (field, filename, content, type)."""
        filename: str | None = None
        content_type = "application/octet-stream"

        if isinstance(item, UploadFile):
            filename, content, content_type = item.to_tuple()
        elif isinstance(item, tuple):
            if len(item) == 2:
                filename, content = item
            else:
                filename, content, content_type = item
        else:
            content = item

        if hasattr(content, "read"):
            content = content.read()
        if isinstance(content, str):
            content = content.encode()

        return key, filename, content, content_type

    def _encode_multipart(self, form: Any, files: dict[str, Any]) -> tuple[bytes, str]:
        """Encode form fields and files into a multipart/form-data body."""
        boundary = uuid.uuid4().hex
        boundary_bytes = boundary.encode()
        lines: list[bytes] = []

        if form:
            for key, value in form.items():
                lines.extend((
                    b"--" + boundary_bytes,
                    f'Content-Disposition: form-data; name="{key}"'.encode(),
                    b"",
                    str(value).encode(),
                ))

        for key, value in files.items():
            items = value if isinstance(value, list) else [value]
            for item in items:
                field, filename, content, content_type = self._normalize_file(key, item)
                disposition = f'Content-Disposition: form-data; name="{field}"'
                if filename:
                    disposition += f'; filename="{filename}"'
                lines.extend((
                    b"--" + boundary_bytes,
                    disposition.encode(),
                    f"Content-Type: {content_type}".encode(),
                    b"",
                    content,
                ))

        lines.extend((b"--" + boundary_bytes + b"--", b""))

        body = b"\r\n".join(lines)
        return body, f"multipart/form-data; boundary={boundary}"

    def _extract_cookies(self, headers: Any) -> dict[str, str]:
        """Parse Set-Cookie response headers into a simple mapping."""
        cookies: dict[str, str] = {}
        for raw in headers.get_all("Set-Cookie") or []:
            parsed: SimpleCookie = SimpleCookie()
            parsed.load(raw)
            for name, morsel in parsed.items():
                cookies[name] = morsel.value
        return cookies

    def _build_url(self, request: HTTPRequest) -> str:
        url = urljoin(self.base_url, request.url)
        if request.query:
            query_string = urlencode(request.query, doseq=True)
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}{query_string}"
        return url

    def _prepare_body(
        self, request: HTTPRequest, headers: dict[str, str]
    ) -> bytes | None:
        """Encode the request payload and set the matching Content-Type header."""
        if request.raw is not None:
            return request.raw.encode() if isinstance(request.raw, str) else request.raw

        if request.file:
            body, content_type = self._encode_multipart(request.form, request.file)
            headers.setdefault("Content-Type", content_type)
            return body
        if request.form:
            headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
            return urlencode(request.form, doseq=True).encode()
        if request.body:
            headers.setdefault("Content-Type", "application/json")
            return self.json_dumps(request.body).encode()
        return None

    def _do_request(self, request: HTTPRequest) -> _UrllibResponse:
        headers = dict(request.header)
        body = self._prepare_body(request, headers)

        req = urllib.request.Request(  # noqa: S310  # base_url is developer-controlled
            url=self._build_url(request),
            data=body,
            headers=headers,
            method=request.method,
        )

        try:
            return self._opener.open(req, timeout=self._timeout)
        except urllib.error.HTTPError as e:
            # HTTPError is itself a valid response object for non-2xx statuses.
            return e
        except urllib.error.URLError as e:
            if isinstance(e.reason, TimeoutError):
                raise RequestTimeoutError(str(e)) from e
            raise NetworkError(str(e)) from e
        except TimeoutError as e:
            raise RequestTimeoutError(str(e)) from e

    def make_request(self, request: HTTPRequest) -> HTTPResponse:
        raw = self._do_request(request)

        try:
            content = raw.read()
        except TimeoutError as e:
            raw.close()
            raise RequestTimeoutError(str(e)) from e
        except (OSError, http.client.HTTPException) as e:
            raw.close()
            raise NetworkError(str(e)) from e

        response_data: Any = None
        if content:
            try:
                response_data = self.json_loads(content)
            except (ValueError, TypeError):
                response_data = content

        return HTTPResponse(
            status_code=raw.status or 0,
            headers=dict(raw.headers.items()),
            cookies=self._extract_cookies(raw.headers),
            data=response_data,
            raw_response=raw,
        )

    def stream_make_request(
        self, request: HTTPRequest, chunk_size: int = 65536
    ) -> HTTPResponse[ChunkStream]:
        raw = self._do_request(request)

        return HTTPResponse(
            status_code=raw.status or 0,
            headers=dict(raw.headers.items()),
            cookies=self._extract_cookies(raw.headers),
            data=_UrllibChunkStream(raw, chunk_size),
            raw_response=raw,
        )
