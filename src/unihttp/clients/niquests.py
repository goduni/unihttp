import json
from collections.abc import Callable, Mapping
from typing import Any, cast
from urllib.parse import urljoin

import niquests
from niquests import AsyncSession, Session

from unihttp.clients.base import BaseAsyncClient, BaseSyncClient
from unihttp.exceptions import NetworkError, RequestTimeoutError
from unihttp.http import UploadFile
from unihttp.http.request import HTTPRequest
from unihttp.http.response import HTTPResponse
from unihttp.middlewares.base import AsyncMiddleware, Middleware
from unihttp.serialize import RequestDumper, ResponseLoader


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

    def make_request(self, request: HTTPRequest) -> HTTPResponse:
        content = None

        if request.form:
            content = request.form

        if request.body:
            if request.form or request.file:
                raise ValueError(
                    "Cannot use Body with Form or File. "
                    "Use Form for fields in multipart requests."
                )

            content = self.json_dumps(request.body)
            if "Content-Type" not in request.header:
                request.header["Content-Type"] = "application/json"

        try:
            files = self._convert_files(request.file) if request.file else None
            response = self._session.request(
                method=request.method,
                url=urljoin(self.base_url, request.url),
                headers=request.header,
                params=request.query,
                files=files,
                data=content,
            )
        except niquests.exceptions.ConnectionError as e:
            raise NetworkError(str(e)) from e
        except niquests.exceptions.Timeout as e:
            raise RequestTimeoutError(str(e)) from e
        except niquests.exceptions.RequestException as e:
            raise NetworkError(str(e)) from e

        response_data = None
        if response.content:
            response_data = self.json_loads(response.content)

        return HTTPResponse(
            status_code=response.status_code or 0,
            headers=dict(response.headers),
            cookies=cast(Mapping[str, Any], response.cookies),
            data=response_data,
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

    async def make_request(self, request: HTTPRequest) -> HTTPResponse:
        content = None

        if request.form:
            content = request.form

        if request.body:
            if request.form or request.file:
                raise ValueError(
                    "Cannot use Body with Form or File. "
                    "Use Form for fields in multipart requests."
                )

            content = self.json_dumps(request.body)
            if "Content-Type" not in request.header:
                request.header["Content-Type"] = "application/json"

        try:
            files = self._convert_files(request.file) if request.file else None
            response = await self._session.request(
                method=request.method,
                url=urljoin(self.base_url, request.url),
                headers=request.header,
                params=request.query,
                files=files,
                data=content,
            )
        except niquests.exceptions.ConnectionError as e:
            raise NetworkError(str(e)) from e
        except niquests.exceptions.Timeout as e:
            raise RequestTimeoutError(str(e)) from e
        except niquests.exceptions.RequestException as e:
            raise NetworkError(str(e)) from e

        response_data = None
        if response.content:
            response_data = self.json_loads(response.content)

        return HTTPResponse(
            status_code=response.status_code or 0,
            headers=dict(response.headers),
            cookies=cast(Mapping[str, Any], response.cookies),
            data=response_data,
            raw_response=response,
        )

    async def close(self) -> None:
        await self._session.close()
