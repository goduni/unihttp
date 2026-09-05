"""Return a loaded model together with HTTP status and a response header."""

from dataclasses import dataclass
from operator import itemgetter

import httpx
from adaptix import Chain, loader
from unihttp.bind_method import bind_method
from unihttp.clients.httpx import HTTPXSyncClient
from unihttp.exceptions import ClientError, ServerError
from unihttp.http.response import HTTPResponse
from unihttp.markers import Path
from unihttp.method import BaseMethod
from unihttp.middlewares import SyncErrorMapperMiddleware
from unihttp.serialize import ResponseLoader
from unihttp.serializers.adaptix import DEFAULT_RETORT, AdaptixDumper, AdaptixLoader


# --8<-- [start:model]
@dataclass
class User:
    id: int
    name: str
    # --8<-- [end:model]


# --8<-- [start:metadata]
@dataclass
class UserResponse:
    user: User
    status_code: int
    request_id: str | None


@dataclass
class GetUser(BaseMethod[UserResponse]):
    __url__ = "/users/{user_id}"
    __method__ = "GET"

    user_id: Path[int]

    def make_response(
        self, response: HTTPResponse, response_loader: ResponseLoader
    ) -> UserResponse:
        return UserResponse(
            user=response_loader.load(response.data, User),
            status_code=response.status_code,
            request_id=response.headers.get("X-Request-ID"),
        )

    # --8<-- [end:metadata]


# --8<-- [start:list]
@dataclass
class ListUsers(BaseMethod[list[User]]):
    __url__ = "/users"
    __method__ = "GET"
    # --8<-- [end:list]


# --8<-- [start:envelope]
@dataclass
class GetWrappedUser(BaseMethod[User]):
    __url__ = "/users/{user_id}"
    __method__ = "GET"

    user_id: Path[int]
    # --8<-- [end:envelope]


# --8<-- [start:envelope-loader]
envelope_retort = DEFAULT_RETORT.extend(
    recipe=[
        loader(User, itemgetter("data"), chain=Chain.FIRST),
    ],
)
envelope_loader = AdaptixLoader(envelope_retort)
# --8<-- [end:envelope-loader]


class UserClient(HTTPXSyncClient):
    get_user = bind_method(
        GetUser,
        middleware=[
            SyncErrorMapperMiddleware({
                range(400, 500): ClientError,
                range(500, 600): ServerError,
            }),
        ],
    )


def mock_api(request: httpx.Request) -> httpx.Response:
    return httpx.Response(
        200, json={"id": 1, "name": "Ada"}, headers={"X-Request-ID": "request-123"}
    )


def main() -> UserResponse:
    with UserClient(
        base_url="https://api.example.com",
        request_dumper=AdaptixDumper(DEFAULT_RETORT),
        response_loader=AdaptixLoader(DEFAULT_RETORT),
        session=httpx.Client(transport=httpx.MockTransport(mock_api)),
    ) as client:
        result = client.get_user(user_id=1)
        print(result.user.name, result.status_code, result.request_id)
        return result


if __name__ == "__main__":
    main()
