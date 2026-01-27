from collections.abc import Awaitable, Callable
from typing import Protocol

from unihttp.http.request import HTTPRequest
from unihttp.http.response import HTTPResponse

Handler = Callable[[HTTPRequest], HTTPResponse]
AsyncHandler = Callable[[HTTPRequest], Awaitable[HTTPResponse]]


class Middleware(Protocol):
    def handle(self, request: HTTPRequest, next_handler: Handler) -> HTTPResponse: ...


class AsyncMiddleware(Protocol):
    async def handle(
        self, request: HTTPRequest, next_handler: AsyncHandler
    ) -> HTTPResponse: ...
