from typing import Any
from urllib.parse import urljoin

import requests  # type: ignore[import-untyped]
from requests import Session

from unihttp.clients.base import BaseSyncClient
from unihttp.exceptions import NetworkError, RequestTimeoutError
from unihttp.http.request import HTTPRequest
from unihttp.http.response import HTTPResponse
from unihttp.middlewares.base import Middleware
from unihttp.serialize import RequestDumper, ResponseLoader


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
            response = self._session.request(
                method=request.method,
                url=urljoin(self.base_url, request.url),
                headers=request.header,
                params=request.query,
                files=request.file,
                data=content,
            )
        except requests.exceptions.ConnectionError as e:
            raise NetworkError(str(e)) from e
        except requests.exceptions.Timeout as e:
            raise RequestTimeoutError(str(e)) from e

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

    def close(self) -> None:
        self._session.close()
