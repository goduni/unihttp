"""Backend-independent optional request fields for the documentation."""

# --8<-- [start:setup]
from dataclasses import dataclass

from unihttp.markers import Body, Header, Query
from unihttp.method import BaseMethod
from unihttp.omitted import Omittable, Omitted


@dataclass
class User:
    id: int
    name: str
    nickname: str | None = None
    # --8<-- [end:setup]


# --8<-- [start:query]
@dataclass
class ListUsers(BaseMethod[list[User]]):
    __url__ = "/users"
    __method__ = "GET"

    name: Query[Omittable[str]] = Omitted()
    limit: Query[Omittable[int]] = Omitted()
    accept: Header[Omittable[str]] = Omitted()
    # --8<-- [end:query]


# --8<-- [start:body]
@dataclass
class CreateUser(BaseMethod[User]):
    __url__ = "/users"
    __method__ = "POST"

    name: Body[str]
    nickname: Body[Omittable[str | None]] = Omitted()
    # --8<-- [end:body]
