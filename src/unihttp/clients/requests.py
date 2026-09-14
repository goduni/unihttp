from typing import Any
from urllib.parse import urljoin

import requests
from requests import Response, Session

from unihttp.clients.base import BaseSyncClient
from unihttp.clients.errors import ErrorMap, translate_errors
from unihttp.exceptions import (
    NetworkError,
    NonRetryableError,
    RequestTimeoutError,
    UniHTTPError,
)
from unihttp.http.request import HTTPRequest
from unihttp.http.response import HTTPResponse
from unihttp.http.stream import ChunkStream
from unihttp.middlewares.base import Middleware
from unihttp.serialize import RequestDumper, ResponseLoader

# Timeout first: ConnectTimeout is also a ConnectionError.
_ERROR_MAP: ErrorMap = {
    RequestTimeoutError: requests.exceptions.Timeout,
    NonRetryableError: (
        requests.exceptions.MissingSchema,
        requests.exceptions.InvalidSchema,
        requests.exceptions.InvalidURL,
        requests.exceptions.InvalidHeader,
        requests.exceptions.InvalidJSONError,
        requests.exceptions.URLRequired,
        requests.exceptions.TooManyRedirects,
        requests.exceptions.ContentDecodingError,
        requests.exceptions.UnrewindableBodyError,
    ),
    # Explicit: status and misuse errors must fall through to plain UniHTTPError.
    NetworkError: (
        requests.exceptions.ConnectionError,
        requests.exceptions.ChunkedEncodingError,
        requests.exceptions.RetryError,
    ),
    UniHTTPError: requests.exceptions.RequestException,
}


class _RequestsChunkStream(ChunkStream):
    def __init__(self, response: Response, chunk_size: int) -> None:
        super().__init__()
        self._response = response
        self._iter = response.iter_content(chunk_size=chunk_size)

    def _fetch_chunk(self) -> bytes:
        with translate_errors(_ERROR_MAP):
            return next(self._iter)

    def _close_response(self) -> None:
        self._response.close()


class RequestsSyncClient(BaseSyncClient):
    def __init__(
        self,
        base_url: str,
        request_dumper: RequestDumper,
        response_loader: ResponseLoader,
        middleware: list[Middleware] | None = None,
        session: Session | None = None,
    ):
        super().__init__(
            base_url=base_url,
            request_dumper=request_dumper,
            response_loader=response_loader,
            middleware=middleware,
        )

        if session is None:
            self._session = Session()
        else:
            self._session = session

    def _build_content(self, request: HTTPRequest) -> Any:
        """Resolve the request body: raw takes priority, then JSON body, then form."""
        content = None
        if request.raw is not None:
            content = request.raw
        elif request.body:
            content = self.json_dumps(request.body)
            if "Content-Type" not in request.header:
                request.header["Content-Type"] = "application/json"
        elif request.form:
            content = request.form
        return content

    def _do_request(self, request: HTTPRequest, *, stream: bool) -> Response:
        content = self._build_content(request)

        with translate_errors(_ERROR_MAP):
            return self._session.request(
                method=request.method,
                url=urljoin(self.base_url, request.url),
                headers=request.header,
                params=request.query,
                files=request.file,
                data=content,
                stream=stream,
            )

    def make_request(self, request: HTTPRequest) -> HTTPResponse:
        response = self._do_request(request, stream=False)

        response_data: Any = None
        if response.content:
            try:
                response_data = self.json_loads(response.content)
            except (ValueError, TypeError):
                response_data = response.content

        return HTTPResponse(
            status_code=response.status_code,
            headers=response.headers,
            cookies=response.cookies,
            data=response_data,
            raw_response=response,
        )

    def stream_make_request(
        self, request: HTTPRequest, chunk_size: int = 65536
    ) -> HTTPResponse[ChunkStream]:
        response = self._do_request(request, stream=True)

        return HTTPResponse(
            status_code=response.status_code,
            headers=response.headers,
            cookies=response.cookies,
            data=_RequestsChunkStream(response, chunk_size),
            raw_response=response,
        )

    def close(self) -> None:
        self._session.close()
