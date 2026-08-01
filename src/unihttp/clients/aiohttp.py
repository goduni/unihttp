import json
from collections.abc import Callable
from typing import Any
from urllib.parse import urljoin

import aiohttp
from aiohttp import ClientResponse, ClientSession, FormData

from unihttp.clients.base import BaseAsyncClient
from unihttp.exceptions import NetworkError, RequestTimeoutError
from unihttp.http import UploadFile
from unihttp.http.request import HTTPRequest
from unihttp.http.response import HTTPResponse
from unihttp.http.stream import AsyncChunkStream
from unihttp.middlewares.base import AsyncMiddleware
from unihttp.serialize import RequestDumper, ResponseLoader


class _AiohttpChunkStream(AsyncChunkStream):
    def __init__(self, response: ClientResponse, chunk_size: int) -> None:
        super().__init__()
        self._response = response
        self._iter = response.content.iter_chunked(chunk_size)

    async def _fetch_chunk(self) -> bytes:
        try:
            return await anext(self._iter)
        except aiohttp.ClientConnectionError as e:
            raise NetworkError(str(e)) from e
        except TimeoutError as e:
            raise RequestTimeoutError(str(e)) from e

    async def _close_response(self) -> None:
        self._response.close()


class AiohttpAsyncClient(BaseAsyncClient):
    def __init__(
        self,
        base_url: str,
        request_dumper: RequestDumper,
        response_loader: ResponseLoader,
        middleware: list[AsyncMiddleware] | None = None,
        session: ClientSession | None = None,
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
            session = ClientSession()

        self._session = session

    def _build_form_data(self, request: HTTPRequest) -> FormData:
        """Build FormData from request form and files."""
        form_data = FormData()

        if request.form:
            for key, value in request.form.items():
                form_data.add_field(key, str(value))

        for field_name, file_info in request.file.items():
            if isinstance(file_info, tuple):
                if len(file_info) == 2:
                    filename, content = file_info
                    form_data.add_field(field_name, content, filename=filename)
                else:
                    filename, content, content_type = file_info
                    form_data.add_field(
                        field_name, content, filename=filename, content_type=content_type
                    )

            elif isinstance(file_info, UploadFile):
                filename, content, content_type = file_info.to_tuple()
                form_data.add_field(
                    field_name, content, filename=filename, content_type=content_type
                )

            else:
                form_data.add_field(field_name, file_info)

        return form_data

    def _build_data(self, request: HTTPRequest) -> FormData | str | bytes | None:
        """Resolve the request payload: raw, then multipart/form, then JSON body."""
        if request.raw is not None:
            return request.raw
        if request.form or request.file:
            return self._build_form_data(request)
        if request.body:
            data = self.json_dumps(request.body)
            if "Content-Type" not in request.header:
                request.header["Content-Type"] = "application/json"
            return data
        return None

    async def _do_request(self, request: HTTPRequest) -> ClientResponse:
        data = self._build_data(request)

        try:
            return await self._session.request(
                method=request.method,
                url=urljoin(self.base_url, request.url),
                headers=request.header,
                params=request.query,
                data=data,
            )
        except aiohttp.ClientConnectionError as e:
            raise NetworkError(str(e)) from e
        except TimeoutError as e:
            raise RequestTimeoutError(str(e)) from e

    async def make_request(self, request: HTTPRequest) -> HTTPResponse:
        response = await self._do_request(request)

        response_data: Any = None
        try:
            content = await response.read()
        except aiohttp.ClientConnectionError as e:
            response.close()
            raise NetworkError(str(e)) from e
        except TimeoutError as e:
            response.close()
            raise RequestTimeoutError(str(e)) from e
        if content:
            try:
                response_data = self.json_loads(content)
            except (ValueError, TypeError):
                response_data = content

        return HTTPResponse(
            status_code=response.status,
            headers=response.headers,
            cookies=response.cookies,
            data=response_data,
            raw_response=response,
        )

    async def stream_make_request(
        self, request: HTTPRequest, chunk_size: int = 65536
    ) -> HTTPResponse[AsyncChunkStream]:
        response = await self._do_request(request)

        return HTTPResponse(
            status_code=response.status,
            headers=response.headers,
            cookies=response.cookies,
            data=_AiohttpChunkStream(response, chunk_size),
            raw_response=response,
        )

    async def close(self) -> None:
        await self._session.close()
