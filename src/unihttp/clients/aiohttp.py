import json
from collections.abc import Callable
from typing import Any
from urllib.parse import urljoin

import aiohttp
from aiohttp import ClientSession, FormData

from unihttp.clients.base import BaseAsyncClient
from unihttp.exceptions import NetworkError, RequestTimeoutError
from unihttp.http import UploadFile
from unihttp.http.request import HTTPRequest
from unihttp.http.response import HTTPResponse
from unihttp.middlewares.base import AsyncMiddleware
from unihttp.serialize import RequestDumper, ResponseLoader


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

    async def make_request(self, request: HTTPRequest) -> HTTPResponse:
        data: FormData | str | None = None

        if request.form or request.file:
            data = self._build_form_data(request)

        if request.body:
            if request.form or request.file:
                raise ValueError(
                    "Cannot use Body with Form or File. "
                    "Use Form for fields in multipart requests."
                )

            data = self.json_dumps(request.body)
            if "Content-Type" not in request.header:
                request.header["Content-Type"] = "application/json"

        try:
            async with self._session.request(
                    method=request.method,
                    url=urljoin(self.base_url, request.url),
                    headers=request.header,
                    params=request.query,
                    data=data,
            ) as response:
                response_data: Any = None
                content = await response.read()
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
        except aiohttp.ClientConnectionError as e:
            raise NetworkError(str(e)) from e
        except TimeoutError as e:
            raise RequestTimeoutError(str(e)) from e

    async def close(self) -> None:
        await self._session.close()
