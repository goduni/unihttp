import asyncio
import random
import time

from unihttp.http.request import HTTPRequest
from unihttp.http.response import HTTPResponse
from unihttp.middlewares.base import AsyncHandler, AsyncMiddleware, Handler, Middleware


class RetryMiddleware(Middleware):
    def __init__(
            self,
            retries: int = 3,
            backoff: float = 1.0,
            status_codes: list[int] | None = None,
            exceptions: list[type[Exception]] | None = None,
            jitter: bool = True,
    ):
        self.retries = retries
        self.backoff = backoff
        self.status_codes = status_codes or [500, 502, 503, 504]
        self.exceptions = exceptions or ()
        self.jitter = jitter

    def handle(self, request: HTTPRequest, next_handler: Handler) -> HTTPResponse:
        attempt = 0
        while True:
            try:
                response = next_handler(request)
                if response.status_code in self.status_codes and attempt < self.retries:
                    self._sleep(attempt)
                    attempt += 1
                    continue
            except Exception as e:
                # If exception is retryable
                if (
                    self.exceptions and
                    isinstance(e, tuple(self.exceptions)) and
                    attempt < self.retries
                ):
                    self._sleep(attempt)
                    attempt += 1
                    continue
                raise

            return response

    def _sleep(self, attempt: int) -> None:
        sleep_time = self.backoff * (2 ** attempt)
        if self.jitter:
            sleep_time += random.uniform(0, 1)
        time.sleep(sleep_time)


class AsyncRetryMiddleware(AsyncMiddleware):
    def __init__(
            self,
            retries: int = 3,
            backoff: float = 1.0,
            status_codes: list[int] | None = None,
            exceptions: list[type[Exception]] | None = None,
            jitter: bool = True,
    ):
        self.retries = retries
        self.backoff = backoff
        self.status_codes = status_codes or [500, 502, 503, 504]
        self.exceptions = exceptions or ()
        self.jitter = jitter

    async def handle(
        self, request: HTTPRequest, next_handler: AsyncHandler
    ) -> HTTPResponse:
        attempt = 0
        while True:
            try:
                response = await next_handler(request)
                if response.status_code in self.status_codes and attempt < self.retries:
                    await self._sleep(attempt)
                    attempt += 1
                    continue
            except Exception as e:
                if (
                    self.exceptions and
                    isinstance(e, tuple(self.exceptions)) and
                    attempt < self.retries
                ):
                    await self._sleep(attempt)
                    attempt += 1
                    continue
                raise

            return response

    async def _sleep(self, attempt: int) -> None:
        sleep_time = self.backoff * (2 ** attempt)
        if self.jitter:
            sleep_time += random.uniform(0, 1)
        await asyncio.sleep(sleep_time)
