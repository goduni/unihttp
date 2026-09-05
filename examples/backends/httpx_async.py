"""HTTPX async quickstart; start examples/demo_api.py first."""

import asyncio
from dataclasses import dataclass

from unihttp.bind_method import bind_method

# --8<-- [start:backend-import]
from unihttp.clients.httpx import HTTPXAsyncClient

# --8<-- [end:backend-import]
from unihttp.markers import Path
from unihttp.method import BaseMethod
from unihttp.serializers.adaptix import DEFAULT_RETORT, AdaptixDumper, AdaptixLoader


# --8<-- [start:models]
@dataclass
class User:
    id: int
    name: str


@dataclass
class GetUser(BaseMethod[User]):
    __url__ = "/users/{user_id}"
    __method__ = "GET"

    user_id: Path[int]
    # --8<-- [end:models]


# --8<-- [start:binding]
class UserClient(HTTPXAsyncClient):
    get_user = bind_method(GetUser)
    # --8<-- [end:binding]


async def main(base_url: str = "http://127.0.0.1:8000") -> User:
    async with UserClient(
        base_url=base_url,
        request_dumper=AdaptixDumper(DEFAULT_RETORT),
        response_loader=AdaptixLoader(DEFAULT_RETORT),
    ) as client:
        user = await client.get_user(user_id=1)
        print(user)  # User(id=1, name='Ada')
        return user


if __name__ == "__main__":
    asyncio.run(main())
