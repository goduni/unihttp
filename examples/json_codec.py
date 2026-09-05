"""Use orjson for HTTP JSON encoding while Adaptix handles typed models."""

from dataclasses import dataclass

import httpx
import orjson
from unihttp.clients.httpx import HTTPXSyncClient
from unihttp.markers import Body
from unihttp.method import BaseMethod
from unihttp.serializers.adaptix import DEFAULT_RETORT, AdaptixDumper, AdaptixLoader


@dataclass
class User:
    id: int
    name: str


@dataclass
class CreateUser(BaseMethod[User]):
    __url__ = "/users"
    __method__ = "POST"

    name: Body[str]


def mock_api(request: httpx.Request) -> httpx.Response:
    body = orjson.loads(request.content)
    return httpx.Response(201, json={"id": 1, "name": body["name"]})


def main() -> User:
    with HTTPXSyncClient(
        base_url="https://api.example.com",
        request_dumper=AdaptixDumper(DEFAULT_RETORT),
        response_loader=AdaptixLoader(DEFAULT_RETORT),
        # --8<-- [start:codec]
        json_dumps=lambda value: orjson.dumps(value).decode("utf-8"),
        json_loads=orjson.loads,
        # --8<-- [end:codec]
        session=httpx.Client(transport=httpx.MockTransport(mock_api)),
    ) as client:
        user = client.call_method(CreateUser(name="Ada"))
        print(user)
        return user


if __name__ == "__main__":
    main()
