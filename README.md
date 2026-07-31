# unihttp

[![codecov](https://codecov.io/gh/goduni/unihttp/branch/master/graph/badge.svg)](https://codecov.io/gh/goduni/unihttp)
[![PyPI version](https://img.shields.io/pypi/v/unihttp.svg)](https://pypi.org/project/unihttp)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/unihttp)
![PyPI - Downloads](https://img.shields.io/pypi/dm/unihttp)
![GitHub License](https://img.shields.io/github/license/goduni/unihttp)
![GitHub Repo stars](https://img.shields.io/github/stars/goduni/unihttp)
[![Telegram](https://img.shields.io/badge/💬-Telegram-blue)](https://t.me/+OsmQESHc1xU1MGVi)

**unihttp** is a modern library for creating declarative API clients.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Serialization Backends](#serialization-backends)
- [Quick Start](#quick-start)
    - [1. Define Methods](#1-define-methods)
    - [2. Client Implementation Strategies](#2-client-implementation-strategies)
- [Markers Reference](#markers-reference)
- [Streaming Methods](#streaming-methods)
- [Middleware](#middleware)
    - [Per-Call and Per-Method Middleware](#per-call-and-per-method-middleware)
- [Error Handling](#error-handling)
    - [1. Method-Level Handling](#1-method-level-handling)
    - [2. Client-Level Handling](#2-client-level-handling)
    - [3. Middleware-Level Handling](#3-middleware-level-handling)
    - [4. Response Body Validation](#4-response-body-validation)
- [Custom JSON Serialization](#custom-json-serialization)
- [Powered by Adaptix](#powered-by-adaptix)
- [Pydantic Integration](#pydantic-integration)
- [msgspec Integration](#msgspec-integration)
- [Agent Skills](#agent-skills)

## Features

- **Declarative**: Define API methods using standard Python type hints.
- **Type-Safe**: Full support for static type checking.
- **Backend Agnostic**: Works with `httpx`, `httpx2`, `aiohttp`, `requests`, `niquests`, `zapros` and the standard library `urllib`.
- **Extensible**: Powerful middleware and error handling systems.

## Installation

```bash
pip install unihttp
```

To include a specific HTTP backend (recommended):

```bash
pip install "unihttp[httpx]"    # For HTTPX (Sync/Async) support
# OR
pip install "unihttp[httpx2]"   # For HTTPX2 (Sync/Async) support
# OR
pip install "unihttp[niquests]"  # For niquests (Sync/Async) support
# OR
pip install "unihttp[requests]" # For Requests (Sync) support
# OR
pip install "unihttp[aiohttp]"  # For Aiohttp (Async) support
# OR
pip install "unihttp[zapros]"   # For Zapros (Sync/Async) support
```

The standard library `urllib` backend (`UrllibSyncClient`) requires no extra —
it works out of the box with a plain `pip install unihttp`, which is handy for
dependency-free environments.

## Serialization Backends

`unihttp` allows you to choose your preferred serialization framework:

1. **Adaptix** (recommended): High-performance serialization for standard Python types (dataclasses, TypedDict).
2. **Pydantic**: Native support for Pydantic models.
3. **msgspec**: Native support for `msgspec.Struct` models — ideal if you already define your models as structs and want them serialized directly.

You will need to pass the appropriate `request_dumper` and `response_loader` when initializing your client.
See [Powered by Adaptix](#powered-by-adaptix), [Pydantic Integration](#pydantic-integration) or
[msgspec Integration](#msgspec-integration) for configuration details.

## Quick Start

### 1. Define Methods

`unihttp` uses markers to map method arguments to HTTP request components.

```python
from dataclasses import dataclass
from unihttp.markers import Path, Query, Body, Header, Form, File
from unihttp.method import BaseMethod


@dataclass
class User:
    id: int
    name: str
    email: str


@dataclass
class GetUser(BaseMethod[User]):
    __url__ = "/users/{id}"
    __method__ = "GET"

    id: Path[int]
    compact: Query[bool] = False


@dataclass
class CreateUser(BaseMethod[User]):
    __url__ = "/users"
    __method__ = "POST"

    name: Body[str]
    email: Body[str]
```

### 2. Client Implementation Strategies

You can choose between a purely declarative style using `bind_method` or a more imperative style using `call_method`.

#### Option A: Declarative Client (via `bind_method`)

This is the most concise way to define your client. You simply bind the methods to the client class.

> [!NOTE]
> **PyCharm Users**: There is currently a known issue with displaying type hints for descriptors like `bind_method` (
> see [PY-51768](https://youtrack.jetbrains.com/issue/PY-51768)). This is expected to be fixed in the **2026.1** version.

```python
from unihttp.bind_method import bind_method
from unihttp.clients.httpx import HTTPXSyncClient
from unihttp.serializers.adaptix import DEFAULT_RETORT


class UserClient(HTTPXSyncClient):
    get_user = bind_method(GetUser)
    create_user = bind_method(CreateUser)


client = UserClient(
    base_url="https://api.example.com",
    request_dumper=DEFAULT_RETORT,
    response_loader=DEFAULT_RETORT
)
user = client.get_user(id=123)
```

#### Option B: Imperative Client (via `call_method`)

If you need more control, need to preprocess arguments, or simply prefer explicit method definitions, you can define
methods in the client and use `call_method`.

```python
class UserClient(HTTPXSyncClient):
    def get_user(self, user_id: int) -> User:
        # You can add custom logic here before the call
        return self.call_method(GetUser(id=user_id))

    def create_user(self, name: str, email: str) -> User:
        return self.call_method(CreateUser(name=name, email=email))
```

## Markers Reference

`unihttp` provides several markers to define how arguments are serialized:

- `Path`: Substitutes placeholders in the `__url__` (e.g., `/users/{id}`).
- `Query`: Adds parameters to the URL query string.
- `Body`: Sends data as the JSON request body.
- `Header`: Adds HTTP headers to the request.
- `Form`: Sends data as form-encoded (`application/x-www-form-urlencoded`).
- `File`: Used for multipart file uploads.
    - `UploadFile` (from `unihttp.http`): A wrapper for file uploads that allows specifying a filename and content
      type (e.g., `UploadFile(b"content", filename="test.txt")`).
- `Raw`: Sends a pre-built `bytes`/`str` value as the request body, bypassing serialization entirely. Mutually
  exclusive with `Body` and with `Form`/`File` — combining `Raw` with either raises a `ValueError`.

## Streaming Methods

For endpoints whose body you want to read incrementally (downloads, SSE, large payloads) instead of buffering it
fully, subclass `StreamMethod` instead of `BaseMethod`. There is no `response_loader` step — the body is never
fully read.

```python
from dataclasses import dataclass
from unihttp.method import StreamMethod
from unihttp.markers import Path


@dataclass
class DownloadFile(StreamMethod):
    __url__ = "/files/{id}"
    __method__ = "GET"

    id: Path[int]
```

Either way, the call returns immediately with `status_code`/`headers` available; `.data` is an unconsumed
`ChunkStream` (or `AsyncChunkStream`) — use it as a context manager so the underlying connection is released even if
you stop iterating early.

#### Option A: Declarative Client (via `bind_method`)

`bind_method` detects `StreamMethod` subclasses automatically and routes them through `call_method_stream`.

```python
class FileClient(HTTPXSyncClient):
    download_file = bind_method(DownloadFile)


client = FileClient(base_url="https://api.example.com", ...)

with client.download_file(id=123).data as stream:
    for chunk in stream:
        f.write(chunk)

# Async client, note the extra `await`
async with (await client.download_file(id=123)).data as stream:
    async for chunk in stream:
        await f.write(chunk)
```

#### Option B: Imperative Client (via `call_method_stream`)

```python
with client.call_method_stream(DownloadFile(id=123)).data as stream:
    for chunk in stream:
        f.write(chunk)

# Async client, note the extra `await`
async with (await client.call_method_stream(DownloadFile(id=123))).data as stream:
    async for chunk in stream:
        await f.write(chunk)
```

Use `__chunk_size__` on the method to control how many bytes are read per chunk (defaults to 65536).

## Middleware

Middleware allows you to intercept requests and responses globally. This is useful for logging, authentication, or
modifying requests on the fly.

```python
from unihttp.middlewares.base import Middleware
from unihttp.http.request import HTTPRequest
from unihttp.http.response import HTTPResponse


class LoggingMiddleware(Middleware):
    def handle(self, request: HTTPRequest, next_handler) -> HTTPResponse:
        print(f"Requesting {request.url}")

        # Call the next handler in the chain
        response = next_handler(request)

        print(f"Status: {response.status_code}")
        return response


client = HTTPXSyncClient(
    # ...
    middleware=[LoggingMiddleware()]
)
```

### Per-Call and Per-Method Middleware

Client-level middleware runs for every call. To scope middleware to a single request or a single bound method, pass
`middleware` to `call_method`/`call_method_stream` or `bind_method`. Chain order is outermost-first: client
`self.middleware`, then these.

```python
# Per-call, via call_method
client.call_method(GetUser(id=123), middleware=[AuthMiddleware()])

# Per-method, via bind_method
class UserClient(HTTPXSyncClient):
    get_user = bind_method(GetUser, middleware=[AuthMiddleware()])
```

## Error Handling

`unihttp` offers a layered approach to error handling, giving you control at multiple levels.

Every `HTTPResponse` has a `raise_for_status()` method that raises `ClientError` (4xx) or `ServerError` (5xx),
each carrying the original `response`:

```python
response = client.call_method(GetUser(id=123))
response.raise_for_status()
```

### 1. Method-Level Handling

Override `on_error` in your Method class to handle specific status codes for that endpoint.

```python
@dataclass
class GetUser(BaseMethod[User]):
    # ...
    def on_error(self, response):
        if response.status_code == 404:
            return None  # Return None (or a default object) instead of raising
        return super().on_error(response)
```

### 2. Client-Level Handling

Override `handle_error` in your Client class to catch errors that weren't handled by the method. This is great for
global concerns like token expiration.

```python
class MyClient(HTTPXSyncClient):
    def handle_error(self, response: HTTPResponse, method):
        if response.status_code == 401:
            raise MyAuthException("Session expired, please log in again.")
```

### 3. Middleware-Level Handling

You can wrap the execution in a try/except block or inspect the response within a middleware. This is useful for logging
exceptions or global error reporting.

```python
class ErrorReportingMiddleware(Middleware):
    def handle(self, request: HTTPRequest, next_handler):
        try:
            return next_handler(request)
        except Exception as e:
            # Report exception to external service
            sentry_sdk.capture_exception(e)
            raise
```

### 4. Response Body Validation

Sometimes APIs return `200 OK` but the body contains an error message. You can override `validate_response` to handle
this.

```python
# In your Method or Client
def validate_response(self, response: HTTPResponse):
    if "error" in response.data:
        raise ApiError(response.data["error"])
```

## Custom JSON Serialization

You can use high-performance JSON libraries like `orjson` or `ujson` by passing custom `json_dumps` and `json_loads` to
the client.

```python
import orjson
from unihttp.clients.httpx import HTTPXSyncClient

client = HTTPXSyncClient(
    # ...
    json_dumps=lambda x: orjson.dumps(x).decode(),
    json_loads=orjson.loads
)
```

## Powered by Adaptix

`unihttp` leverages [adaptix](https://github.com/reagento/adaptix) for all data serialization and validation tasks.
`adaptix` is a powerful and extremely fast library that allows you to:

First, install the optional dependency:

```bash
pip install "unihttp[adaptix]"
```

- **Validate data** strictly against your type hints.
- **Serialize/Deserialize** complex data structures (dataclasses, TypedDicts, etc.) with high performance.
- **Customize** serialization logic (field renaming, value transformation) using `Retort`.

Crucially, you can customize serialization down to **individual fields in each method**, giving you granular control
over how your data is processed.

```python
from adaptix import Retort, name_mapping, P
from unihttp.serializers.adaptix import AdaptixDumper, AdaptixLoader, DEFAULT_RETORT

# Create a Retort that renames specific fields (e.g., camelCase for external API)
retort = Retort(
    recipe=[
        name_mapping(map={"user_name": "userName"}),
        dumper(P[CreateUser].email, lambda x: x.lower()),
    ]
)
retort.extend(DEFAULT_RETORT)

client = UserClient(
    # ...
    request_dumper=AdaptixDumper(retort),
    response_loader=AdaptixLoader(retort),
)
```

## Pydantic Integration

While `unihttp` works great with standard Python types and dataclasses (via `adaptix`), you can also natively use *
*Pydantic** models.

First, install the optional dependency:

```bash
pip install "unihttp[pydantic]"
```

Then, configure your client to use the Pydantic serializers:

```python
from dataclasses import dataclass

from pydantic import BaseModel
from unihttp.clients.requests import RequestsSyncClient
from unihttp.markers import Body
from unihttp.method import BaseMethod
from unihttp.serializers.pydantic import PydanticDumper, PydanticLoader


class User(BaseModel):
    id: int
    name: str


@dataclass
class CreateUser(BaseMethod[User]):
    __url__ = "/users"
    __method__ = "POST"

    user: Body[User]


# Initialize serializers
dumper = PydanticDumper()
loader = PydanticLoader()

client = RequestsSyncClient(
    base_url="https://api.example.org",
    request_dumper=dumper,
    response_loader=loader
)

# Now standard Pydantic models are serialized/validated automatically
client.call_method(CreateUser(user=User(id=1, name="Alice")))
```

## msgspec Integration

If your models are already defined as [`msgspec`](https://github.com/jcrist/msgspec) structs, `unihttp` can serialize and validate them directly — no need to duplicate them as Pydantic or adaptix models.

First, install the optional dependency:

```bash
pip install "unihttp[msgspec]"
```

Then, configure your client to use the msgspec serializers:

```python
from dataclasses import dataclass

import msgspec
from unihttp.clients.requests import RequestsSyncClient
from unihttp.markers import Body
from unihttp.method import BaseMethod
from unihttp.serializers.msgspec import MsgspecDumper, MsgspecLoader


class User(msgspec.Struct):
    id: int
    name: str


@dataclass
class CreateUser(BaseMethod[User]):
    __url__ = "/users"
    __method__ = "POST"

    user: Body[User]


# Initialize serializers
dumper = MsgspecDumper()
loader = MsgspecLoader()

client = RequestsSyncClient(
    base_url="https://api.example.org",
    request_dumper=dumper,
    response_loader=loader
)

# Now msgspec structs are serialized/validated automatically
client.call_method(CreateUser(user=User(id=1, name="Alice")))
```

## Agent Skills

`unihttp` ships **agent skills** that teach AI coding agents (Claude Code, Codex,
etc.) to write idiomatic unihttp code and to **generate a fully typed, packaged
client SDK** from an OpenAPI 3.x spec or a plain API description. They live in
[`.agents/skills/`](.agents/skills/) and are packaged as a Claude Code plugin.

The bundle adds two skills:

- **`unihttp`** — best practices for idiomatic, type-safe unihttp clients: imports,
  markers, serializers, error handling, middleware, and the async client lifecycle.
- **`unihttp-client`** — scaffold a packaged unihttp API client (typed models,
  methods, a client, `ruff`/`mypy` config, and tests) from an OpenAPI spec or an
  API description.

### Quick install (recommended)

One command installs both skills for whatever agent you use — Claude Code, Codex,
and many others. Run it from your project root, then restart the agent:

```bash
npx skills add goduni/unihttp
```

It clones the repo and writes the skills into `.agents/skills/` (symlinking them
into Claude Code's skills directory), so the same command works cross-agent.

### Claude Code plugin

Prefer a managed plugin? Install the packaged version instead:

```bash
claude plugin marketplace add goduni/unihttp
claude plugin install unihttp@unihttp
```

(or run `/plugin` inside Claude Code for the interactive installer). Verify with
`claude plugin details unihttp` — you should see `Skills (2)`.

### Manual install

Skills are just directories containing a `SKILL.md`, so you can also copy them into
whatever folder your agent scans:

```bash
git clone https://github.com/goduni/unihttp /tmp/unihttp

# Codex and most agents — per-project .agents/skills/ (or user-wide ~/.agents/skills/):
mkdir -p .agents/skills
cp -r /tmp/unihttp/.agents/skills/unihttp        .agents/skills/
cp -r /tmp/unihttp/.agents/skills/unihttp-client .agents/skills/

# Claude Code personal skills:
mkdir -p ~/.claude/skills
cp -r /tmp/unihttp/.agents/skills/unihttp        ~/.claude/skills/
cp -r /tmp/unihttp/.agents/skills/unihttp-client ~/.claude/skills/
```

Restart the agent (or reload its skills) and both skills become available.