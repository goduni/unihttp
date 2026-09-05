---
title: Build an async API client
description: Run async unihttp clients with HTTPX, aiohttp, HTTPX2, niquests, or zapros, typed methods, and async context managers.
---

# Build an async API client

Choose an async HTTP backend below. Every variant uses the same dataclasses and
Adaptix serializer, awaits the bound call, and constructs the client inside a
running event loop.

First start the [local demo API](quickstart.md#demo-api) in a separate terminal.
Then install the dependencies from your tab, save the Python code as
`async_client.py`, and run `python async_client.py`.
Each variant prints `User(id=1, name='Ada')`.

=== "HTTPX"

    ```bash
    pip install "unihttp[httpx,adaptix]"
    ```

    ```python
    --8<-- "examples/backends/httpx_async.py"
    ```

=== "aiohttp"

    ```bash
    pip install "unihttp[aiohttp,adaptix]"
    ```

    ```python
    --8<-- "examples/backends/aiohttp_async.py"
    ```

=== "HTTPX2"

    ```bash
    pip install "unihttp[httpx2,adaptix]"
    ```

    ```python
    --8<-- "examples/backends/httpx2_async.py"
    ```

=== "niquests"

    ```bash
    pip install "unihttp[niquests,adaptix]"
    ```

    ```python
    --8<-- "examples/backends/niquests_async.py"
    ```

=== "zapros"

    ```bash
    pip install "unihttp[zapros,adaptix]"
    ```

    ```python
    --8<-- "examples/backends/zapros_async.py"
    ```

## Lifecycle and middleware

Use `async with` to close the client. Reuse an open client for related requests
instead of constructing one per call. If you supply a session, check the selected
[backend's lifecycle](../integrations/backends.md#transport-configuration) before
sharing it with other code.

An async client requires `AsyncMiddleware` implementations and async variants
of built-in middleware. See [middleware](../guides/middleware.md).

In a notebook or an application with an existing event loop, use
`await main()` instead of nesting `asyncio.run()`.

For multiple independent calls, schedule them with the concurrency primitives
of your application and keep the client open until all calls finish. Set
concurrency limits appropriate to the remote API.

To use a real API, replace `base_url`, adapt the endpoint and response model,
and configure [error handling](../guides/errors.md).
requests and urllib are sync-only; see the [sync quickstart](quickstart.md).

## Next steps

Continue with [methods and request parameters](../guides/methods.md), or choose
your next task in the [user guide](../guides/index.md).
This tutorial is an alternative to the sync quickstart; you do not need both.
