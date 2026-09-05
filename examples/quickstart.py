"""Run with: uv run --group docs python examples/quickstart.py."""

from dataclasses import dataclass

import httpx
from unihttp.bind_method import bind_method
from unihttp.clients.httpx import HTTPXSyncClient
from unihttp.markers import Path
from unihttp.method import BaseMethod
from unihttp.serializers.adaptix import DEFAULT_RETORT, AdaptixDumper, AdaptixLoader


# --8<-- [start:overview]
@dataclass
class User:
    id: int
    name: str


@dataclass
class GetUser(BaseMethod[User]):
    __url__ = "/users/{user_id}"
    __method__ = "GET"

    user_id: Path[int]


class UserClient(HTTPXSyncClient):
    get_user = bind_method(GetUser)
    # --8<-- [end:overview]


def mock_api(request: httpx.Request) -> httpx.Response:
    """An in-process API, so the example needs no server or credentials."""
    if request.method == "GET" and request.url.path == "/users/1":
        return httpx.Response(200, json={"id": 1, "name": "Ada"})
    return httpx.Response(404, json={"error": "User not found"})


def main() -> User:
    with UserClient(
        base_url="https://api.example.com",
        request_dumper=AdaptixDumper(DEFAULT_RETORT),
        response_loader=AdaptixLoader(DEFAULT_RETORT),
        session=httpx.Client(transport=httpx.MockTransport(mock_api)),
    ) as client:
        user = client.get_user(user_id=1)
        print(user)  # User(id=1, name='Ada')
        return user


if __name__ == "__main__":
    main()
