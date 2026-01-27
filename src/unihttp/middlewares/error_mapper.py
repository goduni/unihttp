"""Error mapper middleware for status-based exception mapping."""

from collections.abc import Callable

from unihttp.http.request import HTTPRequest
from unihttp.http.response import HTTPResponse
from unihttp.middlewares.base import AsyncHandler, AsyncMiddleware, Handler, Middleware

ErrorFactory = type[Exception] | Callable[[HTTPResponse], Exception]
StatusKey = int | range | tuple[int, ...]


class DefaultErrorMapperMiddleware:
    def __init__(self, mapping: dict[StatusKey, ErrorFactory]) -> None:
        self.mapping = mapping

    def _check_status(self, response: HTTPResponse) -> None:
        for key, factory in self.mapping.items():
            if self._matches(response.status_code, key):
                raise self._make_exception(factory, response)

    def _matches(self, status: int, key: StatusKey) -> bool:
        if isinstance(key, int):
            return status == key
        if isinstance(key, range):
            return status in key
        if isinstance(key, tuple):
            return status in key
        return False

    def _make_exception(
            self, factory: ErrorFactory, response: HTTPResponse
    ) -> Exception:
        if callable(factory) and not isinstance(factory, type):
            return factory(response)
        return factory(f"HTTP {response.status_code}", response)


class SyncErrorMapperMiddleware(DefaultErrorMapperMiddleware, Middleware):
    """Middleware to map HTTP status codes to custom exceptions.

    Example:
        SyncErrorMapperMiddleware({
            404: NotFoundError,
            range(500, 600): ServerError,
            429: lambda r: RateLimitError(r.headers.get("Retry-After")),
        })
    """

    def handle(self, request: HTTPRequest, next_handler: Handler) -> HTTPResponse:
        response = next_handler(request)
        self._check_status(response)
        return response


class AsyncErrorMapperMiddleware(DefaultErrorMapperMiddleware, AsyncMiddleware):
    """Middleware to map HTTP status codes to custom exceptions.

    Example:
        AsyncErrorMapperMiddleware({
            404: NotFoundError,
            range(500, 600): ServerError,
            429: lambda r: RateLimitError(r.headers.get("Retry-After")),
        })
    """

    async def handle(
            self, request: HTTPRequest, next_handler: AsyncHandler
    ) -> HTTPResponse:
        response = await next_handler(request)
        self._check_status(response)
        return response
