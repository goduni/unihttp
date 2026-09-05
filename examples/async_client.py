"""A standalone async version of the first-client example."""

import asyncio
from dataclasses import dataclass

import httpx
from unihttp.bind_method import bind_method
from unihttp.clients.httpx import HTTPXAsyncClient
from unihttp.markers import Path
from unihttp.method import BaseMethod
from unihttp.serializers.adaptix import DEFAULT_RETORT, AdaptixDumper, AdaptixLoader


@dataclass
class User:
    id: int
    name: str


@dataclass
class GetUser(BaseMethod[User]):
    __url__ = "/users/{user_id}"
    __method__ = "GET"

    user_id: Path[int]


class UserClient(HTTPXAsyncClient):
    get_user = bind_method(GetUser)


def mock_api(request: httpx.Request) -> httpx.Response:
    return httpx.Response(
        200, json={"id": int(request.url.path.rsplit("/", 1)[1]), "name": "Ada"}
    )


async def main() -> User:
    async with UserClient(
        base_url="https://api.example.com",
        request_dumper=AdaptixDumper(DEFAULT_RETORT),
        response_loader=AdaptixLoader(DEFAULT_RETORT),
        session=httpx.AsyncClient(transport=httpx.MockTransport(mock_api)),
    ) as client:
        user = await client.get_user(user_id=1)
        print(user)  # User(id=1, name='Ada')
        return user


if __name__ == "__main__":
    asyncio.run(main())
