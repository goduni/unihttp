"""Msgspec setup for the shared serialization guide."""

# --8<-- [start:setup]
from dataclasses import dataclass

import msgspec
from unihttp.markers import Body
from unihttp.method import BaseMethod
from unihttp.serializers.msgspec import MsgspecDumper, MsgspecLoader


class User(msgspec.Struct):
    id: int
    user_name: str


@dataclass
class CreateUser(BaseMethod[User]):
    __url__ = "/users"
    __method__ = "POST"

    user_name: Body[str]


request_dumper = MsgspecDumper()
response_loader = MsgspecLoader()
# --8<-- [end:setup]
