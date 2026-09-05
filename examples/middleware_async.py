"""Measure async request time; start examples/demo_api.py before running this file."""

import asyncio
import logging
from dataclasses import dataclass
from time import perf_counter

from unihttp.bind_method import bind_method
from unihttp.clients.httpx import HTTPXAsyncClient
from unihttp.http.request import HTTPRequest
from unihttp.http.response import HTTPResponse
from unihttp.markers import Path
from unihttp.method import BaseMethod
from unihttp.middlewares import AsyncHandler, AsyncMiddleware
from unihttp.serializers.adaptix import DEFAULT_RETORT, AdaptixDumper, AdaptixLoader

logger = logging.getLogger("unihttp.timing")


class AsyncTimingMiddleware(AsyncMiddleware):
    async def handle(
        self, request: HTTPRequest, next_handler: AsyncHandler
    ) -> HTTPResponse:
        started = perf_counter()
        response = await next_handler(request)
        elapsed_ms = (perf_counter() - started) * 1000
        logger.info(
            "%s → %s in %.1f ms",
            request.method,
            response.status_code,
            elapsed_ms,
        )
        return response


@dataclass
class User:
    id: int
    name: str


@dataclass
class GetUser(BaseMethod[User]):
    __url__ = "/users/{user_id}"
    __method__ = "GET"

    user_id: Path[int]

    def on_error(self, response: HTTPResponse) -> None:
        response.raise_for_status()


class UserClient(HTTPXAsyncClient):
    get_user = bind_method(GetUser)


async def main(base_url: str = "http://127.0.0.1:8000") -> User:
    async with UserClient(
        base_url=base_url,
        request_dumper=AdaptixDumper(DEFAULT_RETORT),
        response_loader=AdaptixLoader(DEFAULT_RETORT),
        middleware=[AsyncTimingMiddleware()],
    ) as client:
        user = await client.get_user(user_id=1)
        print(user)
        return user


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
