---
title: Configure and write middleware
description: Write sync and async unihttp middleware, attach it to a client or an individual call, and understand execution order.
---

# Configure and write middleware

Middleware adds behavior around a request without changing your endpoint
definitions. Use it to attach authentication, measure request time, retry a
failure, or inspect a response.

## Write a middleware

Let's measure how long a request takes and log its status code.
The middleware calls `next_handler(request)` to continue the request, then
works with the response before returning it to the client.

=== "Sync"

    ```python
    import logging
    from time import perf_counter

    from unihttp.http.request import HTTPRequest
    from unihttp.http.response import HTTPResponse
    from unihttp.middlewares import Handler, Middleware

    logger = logging.getLogger("unihttp.timing")


    --8<-- "examples/middleware_sync.py:19:30"
    ```

=== "Async"

    ```python
    import logging
    from time import perf_counter

    from unihttp.http.request import HTTPRequest
    from unihttp.http.response import HTTPResponse
    from unihttp.middlewares import AsyncHandler, AsyncMiddleware

    logger = logging.getLogger("unihttp.timing")


    --8<-- "examples/middleware_async.py:20:33"
    ```

The code before `next_handler` runs on the way out; the code after it runs on
the way back. Return the response so the client can finish processing it.
For async clients, use `AsyncMiddleware` and await the handler.

This example logs only requests for which the inner handler returns a response.
If the transport or a response hook raises, the exception passes through
unchanged. It does not log credentials, URLs, or response bodies.

## Attach it to a client

Continue with `UserClient` from the [sync quickstart](../getting-started/quickstart.md)
or [async quickstart](../getting-started/async.md), using the matching middleware
above. Import the serializers alongside your other imports:

```python
from unihttp.serializers.adaptix import DEFAULT_RETORT, AdaptixDumper, AdaptixLoader
```

Pass your API's base URL to `main`; the default below points to the local demo API:

=== "Sync"

    ```python
    --8<-- "examples/middleware_sync.py:54:63"
    ```

=== "Async"

    ```python
    --8<-- "examples/middleware_async.py:57:66"
    ```

Every call through this client now passes through the timing middleware.
It works with any backend that supports the selected sync or async mode.

If your application has not configured logging, enable INFO messages once at
startup with `logging.basicConfig(level=logging.INFO)`. An example message is
`GET → 200 in 42.1 ms`; the measured time will vary.

## Choose where it runs

Use the client constructor for behavior shared by every endpoint. To apply
middleware to just one call, pass it to `call_method` instead:

=== "Sync"

    ```python
    user = client.call_method(
        GetUser(user_id=1),
        middleware=[TimingMiddleware()],
    )
    ```

=== "Async"

    ```python
    user = await client.call_method(
        GetUser(user_id=1),
        middleware=[AsyncTimingMiddleware()],
    )
    ```

These snippets use the quickstart's `GetUser` and an open client. Per-call
middleware is **added to**, not substituted for, client-level middleware.
Do not register the timing middleware at both levels unless you want two
measurements.

To run it whenever a particular bound method is called, add it to that binding:

=== "Sync"

    ```python
    get_user = bind_method(GetUser, middleware=[TimingMiddleware()])
    ```

=== "Async"

    ```python
    get_user = bind_method(GetUser, middleware=[AsyncTimingMiddleware()])
    ```

Replace the `get_user` declaration inside your client class with this line.
A direct `client.call_method(GetUser(...))` does not use middleware attached to
the binding. The same per-call mechanism is available on `call_method_stream`.

## Scope and ordering

Middleware runs in list order on the request and in reverse order on the
response. Client-level middleware wraps per-call or bound-method middleware:

```text
Request:   client middleware → call/binding middleware → transport
Response:  client middleware ← call/binding middleware ← transport
```

For a list `[A, B]`, A runs first and receives B's response. This matters when
combining [retries](../recipes/retries.md) with
[error mapping](errors.md#map-statuses-across-endpoints): an outer error mapper can act
on the final response after an inner retry middleware has finished.

Response validation and error hooks run inside the chain. The final
`make_response` step, which loads the declared return type, runs after
middleware returns. For streaming calls, timing ends when the stream is
returned, not when the caller has consumed the download.

## Built-in middleware

You do not need to write your own middleware for these common tasks:

| Purpose | Sync | Async |
| --- | --- | --- |
| Status mapping | `SyncErrorMapperMiddleware` | `AsyncErrorMapperMiddleware` |
| Retries | `RetryMiddleware` | `AsyncRetryMiddleware` |
| Logging | `LoggingMiddleware` | `AsyncLoggingMiddleware` |

Import these from `unihttp.middlewares`. See [error handling](errors.md) and
[retries](../recipes/retries.md) for configuration, or
[authentication](../recipes/authentication.md) for a middleware that adds a token.

When modifying headers, use `request.header` (singular) for the outgoing
request and `response.headers` (plural) for the response. Avoid logging
credentials or sensitive payloads.

## Run the standalone examples

The repository's middleware examples each contain their own model, method,
client, and entry point. They do not import another example. Install
`unihttp[httpx,adaptix]`, then start the demo API in a separate terminal:

```bash
python examples/demo_api.py
```

Run either timing example:

=== "Sync"

    ```bash
    python examples/middleware_sync.py
    ```

=== "Async"

    ```bash
    python examples/middleware_async.py
    ```

Each prints the user and logs the request's status and elapsed time.

For a concrete scoping example, run `python examples/middleware_scope.py`.
It adds a fresh `X-Request-ID` to every request and sets `Cache-Control: no-cache`
only on the bound method and the explicit call that opts in. A direct call
without that middleware receives only the request ID. `no-cache` asks caches
to revalidate a stored response; it does not prohibit storing it.
