"""Adaptix setup for the shared serialization guide."""

# --8<-- [start:setup]
from dataclasses import dataclass

from unihttp.markers import Body
from unihttp.method import BaseMethod
from unihttp.serializers.adaptix import DEFAULT_RETORT, AdaptixDumper, AdaptixLoader


@dataclass
class User:
    id: int
    user_name: str


@dataclass
class CreateUser(BaseMethod[User]):
    __url__ = "/users"
    __method__ = "POST"

    user_name: Body[str]


request_dumper = AdaptixDumper(DEFAULT_RETORT)
response_loader = AdaptixLoader(DEFAULT_RETORT)
# --8<-- [end:setup]
