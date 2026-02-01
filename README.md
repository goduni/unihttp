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
- [Quick Start](#quick-start)
  - [1. Define Methods](#1-define-methods)
  - [2. Client Implementation Strategies](#2-client-implementation-strategies)
- [Markers Reference](#markers-reference)
- [Middleware](#middleware)
- [Error Handling](#error-handling)
  - [1. Method-Level Handling](#1-method-level-handling)
  - [2. Client-Level Handling](#2-client-level-handling)
  - [3. Middleware-Level Handling](#3-middleware-level-handling)
  - [4. Response Body Validation](#4-response-body-validation)
- [Custom JSON Serialization](#custom-json-serialization)
- [Powered by Adaptix](#powered-by-adaptix)

## Features

- **Declarative**: Define API methods using standard Python type hints.
- **Type-Safe**: Full support for static type checking.
- **Backend Agnostic**: Works with `httpx`, `aiohttp`, `requests` and `niquests`.
- **Extensible**: Powerful middleware and error handling systems.

## Installation

```bash
pip install unihttp
```

To include a specific HTTP backend (recommended):

```bash
pip install "unihttp[httpx]"    # For HTTPX (Sync/Async) support
# OR
pip install "unihttp[niquests]"  # For niquests (Sync/Async) support
# OR
pip install "unihttp[requests]" # For Requests (Sync) support
# OR
pip install "unihttp[aiohttp]"  # For Aiohttp (Async) support
```

## Quick Start

### 1. Define Methods

`unihttp` uses markers to map method arguments to HTTP request components.

```python
from dataclasses import dataclass
from unihttp import BaseMethod, Path, Query, Body, Header, Form, File


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
> **PyCharm Users**: There is currently a known issue with displaying type hints for descriptors like `bind_method` (see [PY-51768](https://youtrack.jetbrains.com/issue/PY-51768)). This is expected to be fixed in the **2026.1** version.

```python
from unihttp import bind_method
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

If you need more control, need to preprocess arguments, or simply prefer explicit method definitions, you can define methods in the client and use `call_method`.

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
  - `UploadFile`: A wrapper for file uploads that allows specifying a filename and content type (e.g., `UploadFile(b"content", filename="test.txt")`).
## Middleware

Middleware allows you to intercept requests and responses globally. This is useful for logging, authentication, or modifying requests on the fly.

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

## Error Handling

`unihttp` offers a layered approach to error handling, giving you control at multiple levels.

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
Override `handle_error` in your Client class to catch errors that weren't handled by the method. This is great for global concerns like token expiration.

```python
class MyClient(HTTPXSyncClient):
    def handle_error(self, response: HTTPResponse, method):
        if response.status_code == 401:
            raise MyAuthException("Session expired, please log in again.")
```

### 3. Middleware-Level Handling
You can wrap the execution in a try/except block or inspect the response within a middleware. This is useful for logging exceptions or global error reporting.

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
Sometimes APIs return `200 OK` but the body contains an error message. You can override `validate_response` to handle this.

```python
# In your Method or Client
def validate_response(self, response: HTTPResponse):
    if "error" in response.data:
        raise ApiError(response.data["error"])
```

## Custom JSON Serialization

You can use high-performance JSON libraries like `orjson` or `ujson` by passing custom `json_dumps` and `json_loads` to the client.

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

`unihttp` leverages [adaptix](https://github.com/reagento/adaptix) for all data serialization and validation tasks. `adaptix` is a powerful and extremely fast library that allows you to:

- **Validate data** strictly against your type hints.
- **Serialize/Deserialize** complex data structures (dataclasses, TypedDicts, etc.) with high performance.
- **Customize** serialization logic (field renaming, value transformation) using `Retort`.

Crucially, you can customize serialization down to **individual fields in each method**, giving you granular control over how your data is processed.

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