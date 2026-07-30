import json
from collections.abc import Callable, Mapping
from typing import Any, Literal, cast, overload
from urllib.parse import urljoin

import niquests
from niquests import AsyncResponse, AsyncSession, Response, Session

from unihttp.clients.base import BaseAsyncClient, BaseSyncClient
from unihttp.exceptions import NetworkError, RequestTimeoutError
from unihttp.http import UploadFile
from unihttp.http.request import HTTPRequest
from unihttp.http.response import HTTPResponse
from unihttp.http.stream import AsyncChunkStream, ChunkStream
from unihttp.middlewares.base import AsyncMiddleware, Middleware
from unihttp.serialize import RequestDumper, ResponseLoader


class _NiquestsChunkStream(ChunkStream):
    def __init__(self, response: Response, chunk_size: int) -> None:
        super().__init__()
        self._response = response
        self._iter = response.iter_content(chunk_size=chunk_size)

    def _fetch_chunk(self) -> bytes:
        try:
            return next(self._iter)
        except niquests.exceptions.ConnectionError as e:
            raise NetworkError(str(e)) from e
        except niquests.exceptions.Timeout as e:
            raise RequestTimeoutError(str(e)) from e
        except niquests.exceptions.RequestException as e:
            raise NetworkError(str(e)) from e

    def _close_response(self) -> None:
        self._response.close()


class _NiquestsAsyncChunkStream(AsyncChunkStream):
    """Async counterpart of `_NiquestsChunkStream`.

    Unlike the other backends, the chunk iterator itself must be awaited to
    obtain (see `NiquestsAsyncClient.stream_make_request`), so it's passed
    in already built rather than constructed here.
    """

    def __init__(self, response: AsyncResponse, chunk_iter: Any) -> None:
        super().__init__()
        self._response = response
        self._iter = chunk_iter

    async def _fetch_chunk(self) -> bytes:
        try:
            return await anext(self._iter)
        except niquests.exceptions.ConnectionError as e:
            raise NetworkError(str(e)) from e
        except niquests.exceptions.Timeout as e:
            raise RequestTimeoutError(str(e)) from e
        except niquests.exceptions.RequestException as e:
            raise NetworkError(str(e)) from e

    async def _close_response(self) -> None:
        await self._response.close()


class NiquestsSyncClient(BaseSyncClient):
    """Synchronous client implementation using the `niquests` library."""

    def __init__(
        self,
        base_url: str,
        request_dumper: RequestDumper,
        response_loader: ResponseLoader,
        middleware: list[Middleware] | None = None,
        session: Session | None = None,
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
            self._session = Session()
        else:
            self._session = session

    def _convert_files(self, files: dict[str, Any]) -> list[tuple[str, Any]]:
        """Convert files to a format suitable for niquests."""
        converted_files = {}
        for key, value in files.items():
            if isinstance(value, list):
                pass
            elif isinstance(value, UploadFile):
                converted_files[key] = value.to_tuple()
            else:
                converted_files[key] = value

        file_list = []
        for key, value in files.items():
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, UploadFile):
                        file_list.append((key, item.to_tuple()))
                    else:
                        file_list.append((key, item))
            elif isinstance(value, UploadFile):
                file_list.append((key, value.to_tuple()))
            else:
                file_list.append((key, value))
        return file_list

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

        try:
            files = self._convert_files(request.file) if request.file else None
            return self._session.request(
                method=request.method,
                url=urljoin(self.base_url, request.url),
                headers=request.header,
                params=request.query,
                files=files,
                data=content,
                stream=stream,
            )
        except niquests.exceptions.ConnectionError as e:
            raise NetworkError(str(e)) from e
        except niquests.exceptions.Timeout as e:
            raise RequestTimeoutError(str(e)) from e
        except niquests.exceptions.RequestException as e:
            raise NetworkError(str(e)) from e

    def make_request(self, request: HTTPRequest) -> HTTPResponse:
        response = self._do_request(request, stream=False)

        response_data: Any = None
        if response.content:
            try:
                response_data = self.json_loads(response.content)
            except (ValueError, TypeError):
                response_data = response.content

        return HTTPResponse(
            status_code=response.status_code or 0,
            headers=dict(response.headers),
            cookies=cast(Mapping[str, Any], response.cookies),
            data=response_data,
            raw_response=response,
        )

    def stream_make_request(
        self, request: HTTPRequest, chunk_size: int = 65536
    ) -> HTTPResponse[ChunkStream]:
        response = self._do_request(request, stream=True)

        return HTTPResponse(
            status_code=response.status_code or 0,
            headers=dict(response.headers),
            cookies=cast(Mapping[str, Any], response.cookies),
            data=_NiquestsChunkStream(response, chunk_size),
            raw_response=response,
        )

    def close(self) -> None:
        self._session.close()


class NiquestsAsyncClient(BaseAsyncClient):
    """Asynchronous client implementation using the `niquests` library."""

    def __init__(
        self,
        base_url: str,
        request_dumper: RequestDumper,
        response_loader: ResponseLoader,
        middleware: list[AsyncMiddleware] | None = None,
        session: AsyncSession | None = None,
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
            self._session = AsyncSession()
        else:
            self._session = session

    def _convert_files(self, files: dict[str, Any]) -> list[tuple[str, Any]]:
        """Convert files to a list of tuples for niquests."""
        file_list = []
        for key, value in files.items():
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, UploadFile):
                        file_list.append((key, item.to_tuple()))
                    else:
                        file_list.append((key, item))
            elif isinstance(value, UploadFile):
                file_list.append((key, value.to_tuple()))
            else:
                file_list.append((key, value))
        return file_list

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

    @overload
    async def _do_request(
        self, request: HTTPRequest, *, stream: Literal[False]
    ) -> Response: ...
    @overload
    async def _do_request(
        self, request: HTTPRequest, *, stream: Literal[True]
    ) -> AsyncResponse: ...

    async def _do_request(
        self, request: HTTPRequest, *, stream: bool
    ) -> Response | AsyncResponse:
        # `stream` must stay a *literal* at each `self._session.request(...)`
        # call site: niquests overloads that call on it (Response vs
        # AsyncResponse, whose `.content` is sync vs a coroutine), and a
        # plain `bool` can't select between them.
        content = self._build_content(request)
        files = self._convert_files(request.file) if request.file else None

        try:
            if stream:
                return await self._session.request(
                    method=request.method,
                    url=urljoin(self.base_url, request.url),
                    headers=request.header,
                    params=request.query,
                    files=files,
                    data=content,
                    stream=True,
                )
            return await self._session.request(
                method=request.method,
                url=urljoin(self.base_url, request.url),
                headers=request.header,
                params=request.query,
                files=files,
                data=content,
                stream=False,
            )
        except niquests.exceptions.ConnectionError as e:
            raise NetworkError(str(e)) from e
        except niquests.exceptions.Timeout as e:
            raise RequestTimeoutError(str(e)) from e
        except niquests.exceptions.RequestException as e:
            raise NetworkError(str(e)) from e

    async def make_request(self, request: HTTPRequest) -> HTTPResponse:
        response = await self._do_request(request, stream=False)

        response_data: Any = None
        if response.content:
            try:
                response_data = self.json_loads(response.content)
            except (ValueError, TypeError):
                response_data = response.content

        return HTTPResponse(
            status_code=response.status_code or 0,
            headers=dict(response.headers),
            cookies=cast(Mapping[str, Any], response.cookies),
            data=response_data,
            raw_response=response,
        )

    async def stream_make_request(
        self, request: HTTPRequest, chunk_size: int = 65536
    ) -> HTTPResponse[AsyncChunkStream]:
        response = await self._do_request(request, stream=True)

        # niquests builds the chunk iterator asynchronously (unlike the
        # other backends' iter_bytes/iter_content, which are plain sync
        # calls even on an async response) — await it once, up front.
        chunk_iter = await response.iter_content(chunk_size=chunk_size)

        return HTTPResponse(
            status_code=response.status_code or 0,
            headers=dict(response.headers),
            cookies=cast(Mapping[str, Any], response.cookies),
            data=_NiquestsAsyncChunkStream(response, chunk_iter),
            raw_response=response,
        )

    async def close(self) -> None:
        await self._session.close()
