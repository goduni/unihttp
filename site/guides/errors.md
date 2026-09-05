---
title: Handle HTTP and response validation errors
description: Configure HTTP status exceptions, catch request failures, handle endpoint-specific errors, and validate error bodies in unihttp.
---

# Handle HTTP and response validation errors

**unihttp does not raise HTTP status errors automatically.** Without explicit
handling, a `404` or `503` continues to response loading, which may fail because
the error body does not match your model.

Use status mapping for general HTTP errors and method hooks for endpoint-specific
rules. Catch exceptions around the client call.

## Handle an endpoint-specific error

This method uses `User` from the [quickstart](../getting-started/quickstart.md).
It treats a missing user specially and leaves other statuses to the mapper below:

```python
from dataclasses import dataclass

from unihttp.http.response import HTTPResponse
from unihttp.markers import Path
from unihttp.method import BaseMethod

--8<-- "examples/recipes.py:errors"
```

There is deliberately no catch-all `raise_for_status()` here. Letting `5xx`
responses reach middleware allows [status-based retries](../recipes/retries.md)
to run before an exception is raised.

## Map statuses across endpoints

Use `ClientError` for `4xx` and `ServerError` for `5xx`. Both inherit from
`HTTPStatusError` and expose `.status_code` and `.response` (the unihttp
`HTTPResponse`, not the backend's raw response).

These HTTPX examples attach the mapper to the bound method. The same pattern
works with another [client backend](../integrations/backends.md).

```python
from unihttp.bind_method import bind_method
from unihttp.exceptions import ClientError, ServerError
```

=== "Sync"

    ```python
    from unihttp.clients.httpx import HTTPXSyncClient
    from unihttp.middlewares import SyncErrorMapperMiddleware

    --8<-- "examples/response_errors.py:sync"
    ```

=== "Async"

    ```python
    from unihttp.clients.httpx import HTTPXAsyncClient
    from unihttp.middlewares import AsyncErrorMapperMiddleware

    --8<-- "examples/response_errors.py:async"
    ```

Construct the client with your base URL and serializers as in the quickstart.
To apply the policy to **all endpoints**, pass `middleware=[status_errors]`
(or `[async_status_errors]`) to the client constructor instead of repeating it
on each binding. Client-level middleware wraps method-level middleware.

Mapping keys accept an integer, a range, or a tuple of integers. An exception
class receives `(message, response)`; use a factory for another constructor,
for example `404: lambda response: UserNotFound("User does not exist")`.
The first matching mapping wins.

The mapper only sees responses that return from the inner handler. A validation
or error hook that has already raised bypasses status mapping. In this example,
`404` raises `UserNotFound` in the method; other `4xx` and `5xx` reach the mapper.
Unfollowed redirects are not covered by these `4xx`/`5xx` mappings.

## Catch failures at the call site

These helpers return `User | None`. They use an already configured client and
the following imports:

```python
import logging

from unihttp.exceptions import HTTPStatusError, NetworkError, RequestTimeoutError

logger = logging.getLogger(__name__)
```

=== "Sync"

    ```python
    --8<-- "examples/response_errors.py:catch-sync"
    ```

=== "Async"

    ```python
    --8<-- "examples/response_errors.py:catch-async"
    ```

Only a missing user becomes `None`. Other failures propagate after logging.
The HTTP error log includes the request ID header, when present, to help trace
the failed call without logging its response body.

The error types describe different stages:

| Failure | What to handle |
| --- | --- |
| Network failure or timeout | `NetworkError` or `RequestTimeoutError`; do not assume an HTTP response exists. |
| Unsuccessful HTTP status | Exceptions configured by your mapper or error hooks. |
| API error inside a successful HTTP response | Your own exception from `validate_response`, as below. |
| Body does not match the declared result | The configured serializer's loading exception; this is not an HTTP status error. |

Avoid treating all of these as “user not found” or retrying every exception.

## Validate an error inside HTTP 200

Some APIs return `{"ok": false, "error": "Account disabled"}` with status `200`.
Use `validate_response` to reject that body before model loading:

```python
--8<-- "examples/response_errors.py:validation"
```

This example checks successful statuses only, so a `503` error body can still
reach retry middleware. On success it expects the ordinary `User` payload.
If your API wraps successful data too, combine validation with
[envelope unwrapping](responses.md#unwrap-a-json-envelope).

For a rule shared by all endpoints, override
`client.validate_response(response, method)` instead. The method hook only takes
`response`. Validation and error hooks remain synchronous `def` methods on
async clients too.

## Return a fallback deliberately

`on_error` is a raise-or-continue hook: its return value is ignored. Returning
`None` there does **not** make the client call return `None`.

Catch a specific exception in application code, as above, or in a regular client
method when the fallback is part of your SDK's public API. A custom
`make_response` can also return a fallback, but only if earlier hooks and
middleware allow that response through.

## Understand the pipeline

For a buffered call:

1. Enter middleware, outermost first: client middleware, then method/call middleware.
2. Send the request and construct `HTTPResponse`.
3. Run `client.validate_response(response, method)`, then `method.validate_response(response)`.
4. If `response.ok` is false, run `method.on_error(response)`, then `client.handle_error(response, method)`.
5. Return through middleware, innermost first.
6. Call `method.make_response(response, response_loader=...)` to produce the public result.

An exception interrupts the sequence and propagates through the enclosing
middleware. The final `make_response` is outside that chain.

`response.raise_for_status()` is useful inside a hook when you want immediate
`ClientError`/`ServerError` for `4xx`/`5xx`, but doing so prevents middleware from
retrying by status. Do not add it to the `GetUser` above when following the
[retry recipe](../recipes/retries.md).

## Return a model with response metadata

For successful results with headers or status, see
[Response data and metadata](responses.md#return-a-model-with-response-metadata).
[Streaming](streaming.md) has a different lifecycle and no buffered validation.
