"""Customize Adaptix for API field names, normalized input, and Unix timestamps."""

from dataclasses import dataclass
from datetime import UTC, datetime

from adaptix import P, dumper, loader, name_mapping
from unihttp.markers import Body
from unihttp.method import BaseMethod
from unihttp.serializers.adaptix import DEFAULT_RETORT, AdaptixDumper, AdaptixLoader

from examples.serialization.adaptix import CreateUser, User

# --8<-- [start:global-mapping]
global_retort = DEFAULT_RETORT.extend(
    recipe=[name_mapping(map={"user_name": "userName"})],
)
request_dumper = AdaptixDumper(global_retort)
response_loader = AdaptixLoader(global_retort)
# --8<-- [end:global-mapping]

# --8<-- [start:scoped-mapping]
scoped_retort = DEFAULT_RETORT.extend(
    recipe=[
        name_mapping(User, map={"user_name": "userName"}),
        name_mapping(CreateUser, map={"user_name": "userName"}),
    ],
)
# --8<-- [end:scoped-mapping]

# --8<-- [start:normalize]
normalized_retort = global_retort.extend(
    recipe=[dumper(P[CreateUser].user_name, str.strip)],
)
request_dumper = AdaptixDumper(normalized_retort)
# --8<-- [end:normalize]


# --8<-- [start:event-models]
@dataclass
class Event:
    id: int
    starts_at: datetime


@dataclass
class CreateEvent(BaseMethod[Event]):
    __url__ = "/events"
    __method__ = "POST"

    starts_at: Body[datetime]
    # --8<-- [end:event-models]


# --8<-- [start:timestamps]
timestamp_retort = DEFAULT_RETORT.extend(
    recipe=[
        loader(P[Event].starts_at, lambda value: datetime.fromtimestamp(value, tz=UTC)),
        dumper(P[CreateEvent].starts_at, lambda value: value.timestamp()),
    ],
)
request_dumper = AdaptixDumper(timestamp_retort)
response_loader = AdaptixLoader(timestamp_retort)
# --8<-- [end:timestamps]
