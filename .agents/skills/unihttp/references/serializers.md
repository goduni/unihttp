# Serializers reference

A client needs a `request_dumper` (serializes method instances into request
parts) and a `response_loader` (deserializes responses into the declared return
type). Both are `Protocol`s (`unihttp.serialize.RequestDumper` /
`ResponseLoader`), so any object with the right `dump` / `load` method works.

`unihttp` ships three serializer backends. Install the matching extra.

## Choosing a backend

| Backend  | Model types               | When to use                                            |
| -------- | ------------------------- | ------------------------------------------------------ |
| adaptix  | dataclasses, TypedDict    | **Default.** Fast, no runtime dep inside models, flexible name mapping |
| msgspec  | `msgspec.Struct`          | Maximum JSON speed; models already defined as structs  |
| pydantic | `pydantic.BaseModel`      | Rich validation, custom validators, familiar API       |

Pick one per client. You can mix model styles only if the serializer supports them.

## adaptix (default)

```python
from unihttp.serializers.adaptix import DEFAULT_RETORT, AdaptixDumper, AdaptixLoader

client = UserClient(
    base_url="https://api.example.com",
    request_dumper=AdaptixDumper(DEFAULT_RETORT),
    response_loader=AdaptixLoader(DEFAULT_RETORT),
)
```

`DEFAULT_RETORT` already knows how to handle `Omitted` sentinels, unwrap marker
type hints, and dump `UploadFile`. It also **skips unknown keys when loading**, so
a partial response DTO that models only the fields you need is safe against
verbose / superset responses. Extend it for per-API customization instead of
replacing it:

```python
from adaptix import P, dumper, name_mapping

# Extend DEFAULT_RETORT (keyword-only `recipe`) to keep its built-in providers
# (Omitted sentinel, marker unwrapping, UploadFile). Do NOT do
# `Retort(recipe=[...]).extend(DEFAULT_RETORT)` — `extend` takes no positional
# retort argument.
retort = DEFAULT_RETORT.extend(
    recipe=[
        # snake_case in Python <-> camelCase on the wire
        name_mapping(CreateUser, map={"user_name": "userName"}),
        # transform a single field on dump
        dumper(P[CreateUser].email, lambda value: value.lower()),
    ],
)
```

Customization can target individual fields of individual methods, which keeps
models clean. See https://github.com/reagento/adaptix for the full recipe API.

## msgspec

```python
import msgspec
from unihttp.serializers.msgspec import MsgspecDumper, MsgspecLoader


class User(msgspec.Struct):
    id: int
    name: str


client = UserClient(
    base_url="https://api.example.com",
    request_dumper=MsgspecDumper(),
    response_loader=MsgspecLoader(),
)
```

## pydantic

```python
from pydantic import BaseModel
from unihttp.serializers.pydantic import PydanticDumper, PydanticLoader


class User(BaseModel):
    id: int
    name: str


client = UserClient(
    base_url="https://api.example.com",
    request_dumper=PydanticDumper(),
    response_loader=PydanticLoader(),
)
```

## Optional values: `Omitted`

To distinguish "field not sent" from "field sent as null", use the `Omittable`
type and the `Omitted` sentinel from `unihttp.omitted`; adaptix's
`DEFAULT_RETORT` drops `Omitted` fields from the serialized output. This works for
`Query` and `Header` too — prefer it over a plain `= None` default, which is
serialized literally (e.g. `?param=None`, which the aiohttp backend rejects).

```python
from unihttp.omitted import Omitted, Omittable

@dataclass
class UpdateUser(BaseMethod[User]):
    __url__ = "/users/{id}"
    __method__ = "PATCH"

    id: Path[int]
    name: Body[Omittable[str]] = Omitted()       # only sent when provided
    fields: Query[Omittable[str]] = Omitted()    # query param dropped when absent
```

Two gotchas: it must be the direct `= Omitted()` default —
`field(default_factory=Omitted)` is **not** treated as the omit default and leaks
the `<Omitted>` sentinel into the request. And `= Omitted()` trips ruff `RUF009`
("function call in dataclass default"); that is a false positive (`Omitted` is a
singleton), so add `RUF009` to your ruff `ignore`.
