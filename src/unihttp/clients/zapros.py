import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import zapros
from zapros import AsyncClient, Client, Multipart, Part

from unihttp.clients.base import BaseAsyncClient, BaseSyncClient
from unihttp.exceptions import NetworkError, RequestTimeoutError
from unihttp.http import UploadFile
from unihttp.http.request import HTTPRequest
from unihttp.http.response import HTTPResponse
from unihttp.middlewares.base import AsyncMiddleware, Middleware
from unihttp.serialize import RequestDumper, ResponseLoader


def _stringify_pairs(mapping: Mapping[str, Any]) -> list[tuple[str, str]]:
    """Flatten a mapping into ``[(key, str_value), ...]`` pairs.

    Both ``params=`` and ``form=`` in `zapros` are parsed by
    `pywhatwgurl.URLSearchParams`, which follows the WHATWG URL spec strictly
    and accepts only strings. httpx/requests/niquests auto-coerce
    `int`/`bool`/`None`/sequences for query and form alike — we replicate
    that contract so that markers like `Query[bool]`, `Form[int]` and
    `Query[list[int]]` work uniformly across backends.
    """

    def _value(item: Any) -> str:
        if item is None:
            return ""
        if isinstance(item, bool):
            return "true" if item else "false"
        return str(item)

    return [
        (key, _value(item))
        for key, value in mapping.items()
        for item in (value if isinstance(value, (list, tuple)) else [value])
    ]


def _to_bytes(content: Any) -> bytes:
    """Normalize a file-content value into bytes for `zapros.Part`.

    Accepts `bytes`/`bytearray`/`memoryview`, `pathlib.Path`, and any
    file-like object exposing `.read()` returning bytes. Anything else
    raises `TypeError`.
    """
    if isinstance(content, bytes):
        return content
    if isinstance(content, (bytearray, memoryview)):
        return bytes(content)
    if isinstance(content, Path):
        return content.read_bytes()
    if hasattr(content, "read"):
        data = content.read()
        if not isinstance(data, (bytes, bytearray, memoryview)):
            raise TypeError(
                f"File-like object {type(content).__name__} returned "
                f"{type(data).__name__}, expected bytes.",
            )
        return data if isinstance(data, bytes) else bytes(data)
    raise TypeError(
        f"Unsupported file content type: {type(content).__name__}",
    )


def _add_file_part(multipart: Multipart, key: str, value: Any) -> None:
    if isinstance(value, UploadFile):
        filename, content, content_type = value.to_tuple()
    elif isinstance(value, tuple):
        if len(value) == 2:
            filename, content = value
            content_type = "application/octet-stream"
        else:
            filename, content, content_type = value
    else:
        filename, content, content_type = None, value, "application/octet-stream"

    part = Part(_to_bytes(content)).mime_type(content_type)
    if filename:
        part = part.file_name(filename)
    multipart.part(key, part)


def _build_multipart(
    form: dict[str, Any] | None, files: dict[str, Any] | None
) -> Multipart:
    """Build a `zapros.Multipart` from form fields and file uploads."""
    multipart = Multipart()
    if form:
        for key, value in _stringify_pairs(form):
            multipart.text(key, value)
    if files:
        for key, value in files.items():
            if isinstance(value, list):
                for item in value:
                    _add_file_part(multipart, key, item)
            else:
                _add_file_part(multipart, key, value)
    return multipart


class ZaprosSyncClient(BaseSyncClient):
    """Synchronous client implementation using the `zapros` library."""

    def __init__(
        self,
        base_url: str,
        request_dumper: RequestDumper,
        response_loader: ResponseLoader,
        middleware: list[Middleware] | None = None,
        session: Client | None = None,
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

        if session is None:
            session = Client()

        self._session = session

    def make_request(self, request: HTTPRequest) -> HTTPResponse:
        body: bytes | None = None
        form: Any = None
        multipart: Multipart | None = None

        if request.body:
            if request.form or request.file:
                raise ValueError(
                    "Cannot use Body with Form or File. "
                    "Use Form for fields in multipart requests."
                )
            body = self.json_dumps(request.body).encode("utf-8")
            if "Content-Type" not in request.header:
                request.header["Content-Type"] = "application/json"
        elif request.file:
            multipart = _build_multipart(request.form, request.file)
        elif request.form:
            form = _stringify_pairs(request.form)

        try:
            response = self._session.request(  # type: ignore[call-overload]
                method=request.method,
                url=urljoin(self.base_url, request.url),
                headers=request.header,
                params=_stringify_pairs(request.query),
                form=form,
                body=body,
                multipart=multipart,
            )
        except zapros.TimeoutError as e:
            raise RequestTimeoutError(str(e)) from e
        except zapros.ConnectionError as e:
            raise NetworkError(str(e)) from e

        content = response.read()

        response_data: Any = None
        if content:
            try:
                response_data = self.json_loads(content)
            except (ValueError, TypeError):
                response_data = content

        return HTTPResponse(
            status_code=response.status,
            headers=response.headers,
            cookies={},
            data=response_data,
            raw_response=response,
        )

    def close(self) -> None:
        self._session.close()


class ZaprosAsyncClient(BaseAsyncClient):
    """Asynchronous client implementation using the `zapros` library."""

    def __init__(
        self,
        base_url: str,
        request_dumper: RequestDumper,
        response_loader: ResponseLoader,
        middleware: list[AsyncMiddleware] | None = None,
        session: AsyncClient | None = None,
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

        if session is None:
            session = AsyncClient()

        self._session = session

    async def make_request(self, request: HTTPRequest) -> HTTPResponse:
        body: bytes | None = None
        form: Any = None
        multipart: Multipart | None = None

        if request.body:
            if request.form or request.file:
                raise ValueError(
                    "Cannot use Body with Form or File. "
                    "Use Form for fields in multipart requests."
                )
            body = self.json_dumps(request.body).encode("utf-8")
            if "Content-Type" not in request.header:
                request.header["Content-Type"] = "application/json"
        elif request.file:
            multipart = _build_multipart(request.form, request.file)
        elif request.form:
            form = _stringify_pairs(request.form)

        try:
            response = await self._session.request(  # type: ignore[call-overload]
                method=request.method,
                url=urljoin(self.base_url, request.url),
                headers=request.header,
                params=_stringify_pairs(request.query),
                form=form,
                body=body,
                multipart=multipart,
            )
        except zapros.TimeoutError as e:
            raise RequestTimeoutError(str(e)) from e
        except zapros.ConnectionError as e:
            raise NetworkError(str(e)) from e

        content = await response.aread()

        response_data: Any = None
        if content:
            try:
                response_data = self.json_loads(content)
            except (ValueError, TypeError):
                response_data = content

        return HTTPResponse(
            status_code=response.status,
            headers=response.headers,
            cookies={},
            data=response_data,
            raw_response=response,
        )

    async def close(self) -> None:
        await self._session.aclose()
