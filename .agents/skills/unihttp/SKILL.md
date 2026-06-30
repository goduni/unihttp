---
name: unihttp
description: Write the best unihttp client code possible with all the recommended best practices, avoiding common mistakes. Use when defining API methods, building clients, choosing a serializer or HTTP backend, handling errors, or writing middleware with unihttp.
---

# unihttp skill

`unihttp` is a library for building **declarative, type-safe API clients**. You
define API endpoints as typed `BaseMethod` subclasses and bind them to a client
backed by `httpx`, `aiohttp`, `requests`, `niquests`, or `zapros`.

Here is a list of best practices for different parts of a unihttp client. For
deeper reference material, see:

- [references/markers.md](references/markers.md) — every marker and how it maps to the request
- [references/serializers.md](references/serializers.md) — choosing and customizing adaptix / pydantic / msgspec
- [references/backends.md](references/backends.md) — choosing an HTTP backend and sync vs async

## Imports

### Import from submodules, never from the top-level `unihttp` package

The top-level `unihttp/__init__.py` is intentionally empty — it re-exports
**nothing**. Importing names from `unihttp` directly raises `ImportError` at
runtime, even though some README snippets show it.

Wrong:

```python
# Raises: ImportError: cannot import name 'BaseMethod' from 'unihttp'
from unihttp import BaseMethod, Path, Query, Body, bind_method
```

Correct:

```python
from unihttp.method import BaseMethod
from unihttp.markers import Body, File, Form, Header, Path, Query
from unihttp.bind_method import bind_method
from unihttp.http import UploadFile  # for multipart uploads
```

The only packages that DO re-export a public API are the serializer subpackages
and `unihttp.http` / `unihttp.middlewares` / `unihttp.exceptions`:

```python
from unihttp.serializers.adaptix import DEFAULT_RETORT, AdaptixDumper, AdaptixLoader
from unihttp.clients.aiohttp import AiohttpAsyncClient
from unihttp.exceptions import ClientError, ServerError
```

## Defining methods

### Define endpoints as `@dataclass` subclasses of `BaseMethod[ReturnType]`

The return type goes in the generic parameter — that is what the client returns
and what the response is deserialized into. Declare `__url__` and `__method__`
as class attributes, and annotate fields with markers.

Wrong:

```python
from unihttp.method import BaseMethod
from unihttp.markers import Path


class GetUser(BaseMethod):  # no return type — client returns `Any`
    url = "/users/{id}"     # wrong attribute name
    method = "GET"          # wrong attribute name
    id: int                 # no marker — adaptix cannot place it in the request
```

Correct:

```python
from dataclasses import dataclass

from unihttp.method import BaseMethod
from unihttp.markers import Path


@dataclass
class GetUser(BaseMethod[User]):
    __url__ = "/users/{id}"
    __method__ = "GET"

    id: Path[int]
```

`__returning__` is filled automatically from the generic argument, so
`client.get_user(id=1)` is statically typed as `User`.

### Every `{placeholder}` in `__url__` must have a matching `Path` field

`__url__.format(**path_data)` fails with `KeyError` at request time if a
placeholder has no corresponding `Path` field.

Wrong:

```python
@dataclass
class GetUserPost(BaseMethod[Post]):
    __url__ = "/users/{user_id}/posts/{post_id}"
    __method__ = "GET"

    user_id: Path[int]
    # post_id is missing -> KeyError: 'post_id' when the request is built
```

Correct:

```python
@dataclass
class GetUserPost(BaseMethod[Post]):
    __url__ = "/users/{user_id}/posts/{post_id}"
    __method__ = "GET"

    user_id: Path[int]
    post_id: Path[int]
```

## Binding methods to a client

### Prefer `bind_method` for the common case

`bind_method` is a descriptor that exposes the method on the client with the
exact typed signature of its constructor — sync clients return the value, async
clients return an awaitable. Reach for it whenever an endpoint needs no extra
per-call logic.

Wrong (hand-written passthrough that duplicates the signature and loses typing):

```python
class UserClient(AiohttpAsyncClient):
    async def get_user(self, id: int) -> User:
        return await self.call_method(GetUser(id=id))
```

Correct:

```python
from unihttp.bind_method import bind_method


class UserClient(AiohttpAsyncClient):
    get_user = bind_method(GetUser)
```

### Use `call_method` only when an endpoint needs real custom logic

When you must preprocess arguments, combine calls, or adapt names, write an
explicit method and call `call_method`. Do not use it just to rename parameters
that `bind_method` already handles.

Correct:

```python
class UserClient(AiohttpAsyncClient):
    create_user = bind_method(CreateUser)  # plain endpoint -> bind_method

    async def register(self, email: str) -> User:
        # genuine extra logic -> call_method
        normalized = email.strip().lower()
        return await self.call_method(CreateUser(email=normalized))
```

## Markers

### Pick the marker that matches the wire location; never put a body field in the query

See [references/markers.md](references/markers.md) for the full table. The
common mistakes:

- JSON request body -> `Body`, not `Query`.
- `application/x-www-form-urlencoded` fields -> `Form`.
- Multipart file uploads -> `File` (wrap content in `UploadFile` to set filename
  and content type).
- `Body` cannot be combined with `Form`/`File` on the same method — the clients
  raise `ValueError`. Use `Form` for the scalar fields of a multipart request.

Wrong:

```python
@dataclass
class CreateUser(BaseMethod[User]):
    __url__ = "/users"
    __method__ = "POST"

    name: Query[str]   # this belongs in the JSON body, not the query string
    email: Query[str]
```

Correct:

```python
from unihttp.markers import Body


@dataclass
class CreateUser(BaseMethod[User]):
    __url__ = "/users"
    __method__ = "POST"

    name: Body[str]
    email: Body[str]
```

## Serializers

### Prefer adaptix + dataclasses by default

For plain dataclasses / TypedDicts, adaptix is the recommended default: fast, no
runtime dependency inside your model classes, and field-level customization.
Choose `msgspec` when raw speed matters and `pydantic` when you need its rich
validation. See [references/serializers.md](references/serializers.md).

Pass the serializer explicitly with `AdaptixDumper` / `AdaptixLoader`:

```python
from unihttp.serializers.adaptix import DEFAULT_RETORT, AdaptixDumper, AdaptixLoader

client = UserClient(
    base_url="https://api.example.com",
    request_dumper=AdaptixDumper(DEFAULT_RETORT),
    response_loader=AdaptixLoader(DEFAULT_RETORT),
)
```

### Map wire names with a `Retort` instead of renaming your Python fields

When an API uses camelCase (or any non-Pythonic naming), keep idiomatic
snake_case fields and let adaptix translate them. Do not pollute your dataclasses
with `userName`-style attributes.

Wrong:

```python
@dataclass
class User:
    userName: str  # noqa: N815 — leaks the wire format into Python field names
    emailAddress: str  # noqa: N815
```

Correct:

```python
from dataclasses import dataclass

from adaptix import name_mapping

from unihttp.serializers.adaptix import DEFAULT_RETORT, AdaptixDumper, AdaptixLoader


@dataclass
class User:
    user_name: str
    email_address: str


# Define the model first, then extend DEFAULT_RETORT (keyword-only `recipe`) so
# its built-in providers are kept and `name_mapping` can reference the class.
retort = DEFAULT_RETORT.extend(
    recipe=[name_mapping(User, map={"user_name": "userName", "email_address": "emailAddress"})],
)


client = UserClient(
    base_url="https://api.example.com",
    request_dumper=AdaptixDumper(retort),
    response_loader=AdaptixLoader(retort),
)
```

`name_mapping` also applies to **`BaseMethod` subclasses** — a method's `Body` and
`Query` fields are renamed the same way, so map the method classes too, not only
the response models. When many classes share the same snake↔camel fields, use one
global `name_mapping(map={...})` with **no class predicate**; it renames those
fields everywhere (models, request bodies, query filters) in a single recipe
entry.

## Backends, sync and async

### Match the client class to sync/async and to the installed backend

Async backends need an async client class and `await`; sync backends a sync one.
Install the matching extra (`unihttp[aiohttp]`, `unihttp[requests]`, …). See
[references/backends.md](references/backends.md) for the full matrix.

Correct (async):

```python
from unihttp.clients.aiohttp import AiohttpAsyncClient

class UserClient(AiohttpAsyncClient):
    get_user = bind_method(GetUser)

# bind_method returns an awaitable on async clients
user = await client.get_user(id=1)
```

Correct (sync):

```python
from unihttp.clients.requests import RequestsSyncClient

class UserClient(RequestsSyncClient):
    get_user = bind_method(GetUser)

user = client.get_user(id=1)
```

### Always close async clients — prefer `async with`

Async clients own an HTTP session that must be closed, or you leak connections.
The base async client implements `__aenter__`/`__aexit__`, so use a context
manager. Construct the client inside a running event loop.

Wrong:

```python
client = UserClient(base_url=..., request_dumper=..., response_loader=...)
user = await client.get_user(id=1)
# session never closed -> "Unclosed client session" warnings, leaked sockets
```

Correct:

```python
async with UserClient(
    base_url="https://api.example.com",
    request_dumper=AdaptixDumper(DEFAULT_RETORT),
    response_loader=AdaptixLoader(DEFAULT_RETORT),
) as client:
    user = await client.get_user(id=1)
```

## Error handling

`unihttp` handles errors in layers — pick the narrowest one that fits.

### Map status codes to exceptions with the error-mapper middleware, not ad-hoc `if`s

For "turn HTTP status N into exception X" rules that apply across endpoints, use
the error-mapper middleware instead of repeating status checks. Match the
sync/async variant to your client.

Wrong:

```python
class UserClient(AiohttpAsyncClient):
    async def get_user(self, id: int) -> User:
        user = await self.call_method(GetUser(id=id))
        # status handling buried in every method, duplicated everywhere
        return user
```

Correct:

```python
from http import HTTPStatus

from unihttp.middlewares import AsyncErrorMapperMiddleware

client = UserClient(
    base_url="https://api.example.com",
    request_dumper=AdaptixDumper(DEFAULT_RETORT),
    response_loader=AdaptixLoader(DEFAULT_RETORT),
    middleware=[
        AsyncErrorMapperMiddleware({
            HTTPStatus.NOT_FOUND: UserNotFound,
            HTTPStatus.UNAUTHORIZED: SessionExpired,
        }),
    ],
)
```

Keys may be an `int`/`HTTPStatus`, a `range`, or a tuple of codes. An exception
**class** is instantiated as `ExcClass(message, response)` (so it must accept those
two positional args — a plain `Exception` subclass does). Pass `lambda r: ...` when
you need custom construction, e.g. `429: lambda r: RateLimited(r.headers["Retry-After"])`.

### Override `on_error` (method) or `handle_error` (client) for targeted handling

Use a method's `on_error` to raise an endpoint-specific exception, and the
client's `handle_error` for cross-cutting concerns like auth. `on_error` is a
*raise-or-pass* hook: **its return value is ignored**, so `return None` does
**not** make the call return `None` — it just lets the pipeline fall through and
deserialize the error body. To turn a 404 into a `None` result, override
`make_response` or wrap the call in a `call_method` method that catches the error.

```python
@dataclass
class GetUser(BaseMethod[User]):
    __url__ = "/users/{id}"
    __method__ = "GET"
    id: Path[int]

    def on_error(self, response: HTTPResponse) -> None:
        if response.status_code == 404:
            raise UserNotFound(self.id)  # endpoint-specific error
        return super().on_error(response)
```

### Validate "200 OK but error in body" with `validate_response`

Some APIs return `200` with `{"ok": false}`. Override `validate_response` (on the
method or client) instead of leaking that check into business code.

```python
def validate_response(self, response: HTTPResponse) -> None:
    if isinstance(response.data, dict) and response.data.get("ok") is False:
        raise ApiError(response.data.get("error", "unknown error"))
```

### Read response headers/status by overriding `make_response`

`bind_method` returns only the deserialized **body** — headers, status code, and
cookies are invisible to callers by default. When you need them (a `Link`
pagination header, a rate-limit header, a `Location`), override the method's
`make_response`; it receives the full `HTTPResponse` (`.headers`, `.status_code`,
`.cookies`, `.data`). The return type then becomes your wrapper, not the bare body.

```python
from unihttp.http.response import HTTPResponse
from unihttp.serialize import ResponseLoader


@dataclass
class ListIssues(BaseMethod[IssuePage]):  # IssuePage wraps items + next_link
    __url__ = "/repos/{owner}/{repo}/issues"
    __method__ = "GET"
    owner: Path[str]
    repo: Path[str]

    def make_response(
        self,
        response: HTTPResponse,
        response_loader: ResponseLoader,
    ) -> IssuePage:
        # The base method's parameter is `response_loader` and the client calls it
        # by keyword — keep that exact name or the override raises TypeError.
        items = response_loader.load(response.data, list[Issue])
        return IssuePage(items=items, next_link=parse_link(response.headers.get("Link")))
```

## Middleware

### Match middleware sync/async type to the client, and call `next_handler`

Sync clients take `Middleware` (sync `handle`); async clients take
`AsyncMiddleware` (async `handle`). Always pass the request to `next_handler` and
return its response, unless you deliberately short-circuit.

Correct (async client -> async middleware):

```python
from unihttp.middlewares import AsyncHandler, AsyncMiddleware
from unihttp.http.request import HTTPRequest
from unihttp.http.response import HTTPResponse


class AuthMiddleware(AsyncMiddleware):
    def __init__(self, token: str) -> None:
        self._token = token

    async def handle(
        self,
        request: HTTPRequest,
        next_handler: AsyncHandler,
    ) -> HTTPResponse:
        request.header["Authorization"] = f"Bearer {self._token}"
        return await next_handler(request)
```

Type `next_handler` (`AsyncHandler` for async, `Handler` for sync — both from
`unihttp.middlewares`); leaving it unannotated only passes mypy because the
generated `mypy.ini` mutes `no-untyped-def`. Note the field name asymmetry: a
**request** carries `request.header` (singular), a **response** uses
`response.headers` (plural). For bearer/API-key auth, take the token as a client
`__init__` parameter and attach this middleware there. For transient failures,
prefer the built-in `RetryMiddleware` / `AsyncRetryMiddleware` over a hand-rolled
retry loop.

## Custom JSON

### Swap in a faster JSON codec via `json_dumps` / `json_loads`

```python
import orjson

client = UserClient(
    base_url="https://api.example.com",
    request_dumper=AdaptixDumper(DEFAULT_RETORT),
    response_loader=AdaptixLoader(DEFAULT_RETORT),
    json_dumps=lambda obj: orjson.dumps(obj).decode(),
    json_loads=orjson.loads,
)
```
