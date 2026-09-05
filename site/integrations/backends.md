---
title: Choose an HTTP backend
description: Compare unihttp sync and async client classes and installation extras for HTTPX, aiohttp, requests, niquests, zapros, and urllib.
---

# Choose an HTTP backend

The endpoint dataclasses are independent of the HTTP client. Select a backend
that fits your application and install its extra alongside your serializer.

| Backend module | Sync class | Async class | HTTP extra |
| --- | --- | --- | --- |
| `unihttp.clients.httpx` | `HTTPXSyncClient` | `HTTPXAsyncClient` | `httpx` |
| `unihttp.clients.httpx2` | `HTTPX2SyncClient` | `HTTPX2AsyncClient` | `httpx2` |
| `unihttp.clients.aiohttp` | — | `AiohttpAsyncClient` | `aiohttp` |
| `unihttp.clients.requests` | `RequestsSyncClient` | — | `requests` |
| `unihttp.clients.niquests` | `NiquestsSyncClient` | `NiquestsAsyncClient` | `niquests` |
| `unihttp.clients.zapros` | `ZaprosSyncClient` | `ZaprosAsyncClient` | `zapros` |
| `unihttp.clients.urllib` | `UrllibSyncClient` | — | None |

HTTPX is used in the tutorials because it supports both sync and async clients
and an in-process mock transport. Use aiohttp in an existing aiohttp application,
or retain requests when integrating with a synchronous requests-based codebase.

The urllib transport uses the standard library. That removes an HTTP dependency,
but model serialization may still require a serializer dependency.

## Transport configuration

Backend-specific constructor arguments are listed in the
[client reference](../reference/clients.md). Where a session argument is
available, use it for backend configuration such as connection limits and
timeouts. Do not assume every backend accepts identical session parameters or
supports identical HTTP protocol versions.

HTTPX clients close supplied sessions as well as internally created sessions.
Check the selected client's lifecycle before sharing a session with other code.

## Switching backends

Keep method definitions, then change the client base class, installed extra,
and any backend-specific session setup. When moving between sync and async,
also change context managers, awaits, and middleware variants.

The shared API does not make all wire behavior identical. In particular,
verify query encoding, multipart uploads, exception translation, and streaming
against your API. The repository's integration tests cover common behavior;
they are not a guarantee for every transport option.
