---
title: Build a sync API client
description: Run a typed unihttp client with HTTPX, requests, HTTPX2, niquests, zapros, or urllib, using dataclasses and Adaptix.
---

# Build a sync API client

Choose your HTTP library below. Each tab contains its installation command and a
complete script: the models and endpoint are the same, while the client class
and import match your backend. All variants use Adaptix for serialization.

Need aiohttp or asynchronous calls? Use the [async quickstart](async.md).

## Start a local demo API {#demo-api}

All tabs call the same local API, so you need no API account or credentials.
Save the following as `demo_api.py` and run `python demo_api.py` in a separate
terminal. Keep it running while trying the clients; stop it with Ctrl+C.

<details markdown="1">
<summary>demo_api.py — standard-library demo server</summary>

```python
--8<-- "examples/demo_api.py"
```

</details>

The server listens only on `127.0.0.1:8000` and returns
`{"id": 1, "name": "Ada"}` for `GET /users/1`. This is a local teaching server,
not a production API.

## Choose your client

In a second terminal, install the dependencies from your tab. Save its Python
code as `quickstart.py`, then run `python quickstart.py`.
Every variant prints `User(id=1, name='Ada')`.

=== "HTTPX"

    ```bash
    pip install "unihttp[httpx,adaptix]"
    ```

    ```python
    --8<-- "examples/backends/httpx_sync.py"
    ```

=== "requests"

    ```bash
    pip install "unihttp[requests,adaptix]"
    ```

    ```python
    --8<-- "examples/backends/requests_sync.py"
    ```

=== "HTTPX2"

    ```bash
    pip install "unihttp[httpx2,adaptix]"
    ```

    ```python
    --8<-- "examples/backends/httpx2_sync.py"
    ```

=== "niquests"

    ```bash
    pip install "unihttp[niquests,adaptix]"
    ```

    ```python
    --8<-- "examples/backends/niquests_sync.py"
    ```

=== "zapros"

    ```bash
    pip install "unihttp[zapros,adaptix]"
    ```

    ```python
    --8<-- "examples/backends/zapros_sync.py"
    ```

=== "urllib"

    ```bash
    pip install "unihttp[adaptix]"
    ```

    ```python
    --8<-- "examples/backends/urllib_sync.py"
    ```

## What each part does

- `User` is the response model.
- `GetUser(BaseMethod[User])` declares the endpoint and its result type.
- `user_id: Path[int]` fills `{user_id}` in the URL.
- `bind_method(GetUser)` exposes `get_user(user_id=...)` on the client.
- `AdaptixDumper` handles request parameters; `AdaptixLoader` builds the result.
- `with` closes the client when the block finishes.

The bound method's argument types come from the method dataclass constructor.
Its result is `User`, not an `HTTPResponse`. Editor presentation of descriptors
can vary; the [binding reference](../reference/methods.md) explains the contract.

## Connect to a real API

Replace `base_url` with your API origin, adjust the endpoint and models to its
contract, and configure [error handling](../guides/errors.md).
The selected client creates its underlying HTTP session automatically.

Session settings such as timeouts are backend-specific; see
[transport configuration](../integrations/backends.md#transport-configuration).
Do not pass an HTTPX session to a requests, niquests, or other backend.

## Next steps

Continue with [methods and request parameters](../guides/methods.md), or choose
your next task in the [user guide](../guides/index.md).
The [async quickstart](async.md) is an alternative to this tutorial, not a
required next step.
