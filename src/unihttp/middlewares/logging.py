import logging

from unihttp.http.request import HTTPRequest
from unihttp.http.response import HTTPResponse
from unihttp.middlewares.base import AsyncHandler, AsyncMiddleware, Handler, Middleware


class LoggingMiddleware(Middleware):
    def __init__(self, logger: logging.Logger | None = None):
        self.logger = logger or logging.getLogger("unihttp")

    def handle(self, request: HTTPRequest, next_handler: Handler) -> HTTPResponse:
        self.logger.info("Request: %s %s", request.method, request.url)
        response = next_handler(request)
        self.logger.info("Response: %s", response.status_code)
        return response


class AsyncLoggingMiddleware(AsyncMiddleware):
    def __init__(self, logger: logging.Logger | None = None):
        self.logger = logger or logging.getLogger("unihttp")

    async def handle(
            self, request: HTTPRequest, next_handler: AsyncHandler
    ) -> HTTPResponse:
        self.logger.info("Request: %s %s", request.method, request.url)
        response = await next_handler(request)
        self.logger.info("Response: %s", response.status_code)
        return response
