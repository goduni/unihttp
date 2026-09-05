---
title: unihttp – modern library for creating declarative API clients
description: Build declarative Python API clients with unihttp, typed methods, sync and async HTTP backends, and your preferred serializer.
hide:
  - toc
  - path
---

<div class="uh-overview" markdown="1">

<div class="uh-hero" markdown="1">

Python API clients, thoughtfully structured.
{ .uh-eyebrow }

# unihttp – modern library for creating declarative API clients

Describe an endpoint once. Call it as a typed Python method.
Keep your HTTP transport and response models separate.
{ .uh-lead }

<div class="uh-actions" markdown="1">

[Build your first client](getting-started/quickstart.md){ .md-button .md-button--primary }
[Installation & extras →](getting-started/installation.md){ .uh-secondary }

</div>

Sync & async clients · Explicit request parameters · Pluggable serializers
{ .uh-summary }

</div>

<div class="uh-example" markdown="1">

<div class="uh-example-intro" markdown="1">

## An endpoint you can read.

The URL, parameters, and result type live together in a small dataclass.
`bind_method` exposes it on your client with a typed call signature.

1. **Declare the result.** `User` describes the response your code receives.
2. **Describe the request.** `Path[int]` places `user_id` in the URL.
3. **Bind the method.** `get_user(user_id=1)` returns a `User` with the configured response loader; await the call with async clients.

Choose an HTTP library in the tabs. The models stay the same; the client changes.
These excerpts omit shared imports and configuration. See the complete
[sync](getting-started/quickstart.md) or [async](getting-started/async.md) example
to run against a local demo API. aiohttp is async-only.
{ .uh-caption }

</div>

<div class="uh-code" markdown="1">

Endpoint & client · Python
{ .uh-code-label }

=== "HTTPX"

    ```python
    --8<-- "examples/backends/httpx_sync.py:backend-import"

    --8<-- "examples/backends/httpx_sync.py:models"


    --8<-- "examples/backends/httpx_sync.py:binding"
    ```

=== "requests"

    ```python
    --8<-- "examples/backends/requests_sync.py:backend-import"

    --8<-- "examples/backends/requests_sync.py:models"


    --8<-- "examples/backends/requests_sync.py:binding"
    ```

=== "aiohttp"

    ```python
    --8<-- "examples/backends/aiohttp_async.py:backend-import"

    --8<-- "examples/backends/aiohttp_async.py:models"


    --8<-- "examples/backends/aiohttp_async.py:binding"
    ```

=== "HTTPX2"

    ```python
    --8<-- "examples/backends/httpx2_sync.py:backend-import"

    --8<-- "examples/backends/httpx2_sync.py:models"


    --8<-- "examples/backends/httpx2_sync.py:binding"
    ```

=== "niquests"

    ```python
    --8<-- "examples/backends/niquests_sync.py:backend-import"

    --8<-- "examples/backends/niquests_sync.py:models"


    --8<-- "examples/backends/niquests_sync.py:binding"
    ```

=== "zapros"

    ```python
    --8<-- "examples/backends/zapros_sync.py:backend-import"

    --8<-- "examples/backends/zapros_sync.py:models"


    --8<-- "examples/backends/zapros_sync.py:binding"
    ```

=== "urllib"

    ```python
    --8<-- "examples/backends/urllib_sync.py:backend-import"

    --8<-- "examples/backends/urllib_sync.py:models"


    --8<-- "examples/backends/urllib_sync.py:binding"
    ```


</div>

</div>

<div class="uh-stack" markdown="1">

## Your API contract. Your stack.

Method definitions describe the API, not the transport. Choose an HTTP client
for your application and a serializer for your models.

<div class="uh-stack-options" markdown="1">

<div markdown="1">

### HTTP transport

HTTPX, aiohttp, requests, niquests, zapros, or the standard-library urllib.
Use a sync or async client where supported by the backend.

[Compare HTTP backends →](integrations/backends.md)

</div>

<div markdown="1">

### Model serialization

Use dataclasses with Adaptix, or integrate your Pydantic and msgspec models.
Configure request dumping and response loading explicitly.

[Choose a serializer →](guides/serialization.md)

</div>

</div>

</div>

<div class="uh-next" markdown="1">

## Build beyond the first request.

<div class="uh-routes" markdown="1">

[**Define your API** <span>Map query parameters, JSON bodies, headers, and files.</span> <span aria-hidden="true">→</span>](guides/methods.md)

[**Go asynchronous** <span>Use async clients, context managers, and middleware.</span> <span aria-hidden="true">→</span>](getting-started/async.md)

[**Handle failures** <span>Choose how HTTP errors become application exceptions.</span> <span aria-hidden="true">→</span>](guides/errors.md)

[**Add authentication** <span>Apply a bearer token through request middleware.</span> <span aria-hidden="true">→</span>](recipes/authentication.md)

[**Stream a response** <span>Read downloads incrementally and close streams safely.</span> <span aria-hidden="true">→</span>](guides/streaming.md)

[**Look up the API** <span>Find exact signatures, types, and extension points.</span> <span aria-hidden="true">→</span>](reference/index.md)

</div>

[Browse the user guide →](guides/index.md)

</div>

<div class="uh-fit" markdown="1">

**When unihttp fits**

Use it for a reusable API client or SDK with explicit endpoint contracts.
For a one-off request, calling your HTTP library directly may be sufficient.

</div>

</div>
