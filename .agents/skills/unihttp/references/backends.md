# Backends reference

`unihttp` is backend-agnostic: your `BaseMethod` definitions and models are the
same regardless of which HTTP library actually sends the request. Only the client
base class and the install extra change.

## Client matrix

| Backend   | Sync class           | Async class           | Install extra        |
| --------- | -------------------- | --------------------- | -------------------- |
| aiohttp   | —                    | `AiohttpAsyncClient`  | `unihttp[aiohttp]`   |
| httpx     | `HTTPXSyncClient`    | `HTTPXAsyncClient`    | `unihttp[httpx]`     |
| httpx 2.x | `HTTPX2SyncClient`   | `HTTPX2AsyncClient`   | `unihttp[httpx2]`    |
| requests  | `RequestsSyncClient` | —                     | `unihttp[requests]`  |
| niquests  | `NiquestsSyncClient` | `NiquestsAsyncClient` | `unihttp[niquests]`  |
| zapros    | `ZaprosSyncClient`   | `ZaprosAsyncClient`   | `unihttp[zapros]`    |

Import the class from its module, e.g.
`from unihttp.clients.aiohttp import AiohttpAsyncClient`.

## Choosing

- **Default async: `aiohttp`** (`AiohttpAsyncClient`). Mature async stack, good
  for I/O-bound clients and concurrency.
- **Default sync: `requests`** (`RequestsSyncClient`). Ubiquitous, simplest for
  scripts and sync apps.
- **`httpx`** when you want one library that does both sync and async, or HTTP/2.
- **`niquests`** as a drop-in `requests` successor with sync + async.
- **`zapros`** when the project already standardizes on it.

## Sync vs async consequences

- Async clients: `call_method` is a coroutine; `bind_method` returns an awaitable;
  middleware must be `AsyncMiddleware`; **close the session** (use `async with`).
- Sync clients: everything is blocking; middleware is `Middleware`; the client is
  a regular context manager (`with client:`).

## Constructor

All clients share the same core constructor (async clients additionally accept a
backend-specific `session`/transport):

```python
Client(
    base_url: str,
    request_dumper: RequestDumper,
    response_loader: ResponseLoader,
    # sync clients: list[Middleware] | None ; async clients: list[AsyncMiddleware] | None
    # (list is invariant — annotate with the exact element type, not a union)
    middleware: list[AsyncMiddleware] | None = None,
    json_dumps=json.dumps,
    json_loads=json.loads,
)
```

`AiohttpAsyncClient` also takes `session: aiohttp.ClientSession | None` — pass one
to share connection pooling, or let it create (and close) its own.
