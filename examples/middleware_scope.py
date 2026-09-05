"""Scope request headers; start examples/demo_api.py before running this file."""

from dataclasses import dataclass
from uuid import uuid4

from unihttp.bind_method import bind_method
from unihttp.clients.httpx import HTTPXSyncClient
from unihttp.http.request import HTTPRequest
from unihttp.http.response import HTTPResponse
from unihttp.markers import Path
from unihttp.method import BaseMethod
from unihttp.middlewares import Handler, Middleware
from unihttp.serializers.adaptix import DEFAULT_RETORT, AdaptixDumper, AdaptixLoader


class RequestIDMiddleware(Middleware):
    def handle(self, request: HTTPRequest, next_handler: Handler) -> HTTPResponse:
        request.header["X-Request-ID"] = uuid4().hex
        return next_handler(request)


class NoCacheMiddleware(Middleware):
    def handle(self, request: HTTPRequest, next_handler: Handler) -> HTTPResponse:
        request.header["Cache-Control"] = "no-cache"
        return next_handler(request)


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


class UserClient(HTTPXSyncClient):
    get_user = bind_method(GetUser, middleware=[NoCacheMiddleware()])


def main(base_url: str = "http://127.0.0.1:8000") -> None:
    with UserClient(
        base_url=base_url,
        request_dumper=AdaptixDumper(DEFAULT_RETORT),
        response_loader=AdaptixLoader(DEFAULT_RETORT),
        middleware=[RequestIDMiddleware()],
    ) as client:
        # Both the client and bound-method middleware run.
        print(client.get_user(user_id=1))

        # Only the client middleware runs.
        print(client.call_method(GetUser(user_id=1)))

        # Add Cache-Control to this explicit call too.
        user = client.call_method(GetUser(user_id=1), middleware=[NoCacheMiddleware()])
        print(user)


if __name__ == "__main__":
    main()
