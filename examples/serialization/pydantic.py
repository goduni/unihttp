"""Pydantic setup for the shared serialization guide."""

# --8<-- [start:setup]
from dataclasses import dataclass

from pydantic import BaseModel
from unihttp.markers import Body
from unihttp.method import BaseMethod
from unihttp.serializers.pydantic import PydanticDumper, PydanticLoader


class User(BaseModel):
    id: int
    user_name: str


@dataclass
class CreateUser(BaseMethod[User]):
    __url__ = "/users"
    __method__ = "POST"

    user_name: Body[str]


request_dumper = PydanticDumper()
response_loader = PydanticLoader()
# --8<-- [end:setup]
