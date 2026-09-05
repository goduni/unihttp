---
title: Clients
description: Public sync and async client constructors and request lifecycle hooks.
---

# Clients

Install the appropriate backend extra before importing its module. The base classes describe the shared lifecycle; concrete constructors list backend-specific settings. HTTPX clients close supplied sessions. See [HTTP backends](../integrations/backends.md) before switching transports.

::: unihttp.clients.base.BaseClient

::: unihttp.clients.base.BaseSyncClient

::: unihttp.clients.base.BaseAsyncClient

::: unihttp.clients.httpx.HTTPXSyncClient

::: unihttp.clients.httpx.HTTPXAsyncClient

::: unihttp.clients.httpx2.HTTPX2SyncClient

::: unihttp.clients.httpx2.HTTPX2AsyncClient

::: unihttp.clients.aiohttp.AiohttpAsyncClient

::: unihttp.clients.requests.RequestsSyncClient

::: unihttp.clients.niquests.NiquestsSyncClient

::: unihttp.clients.niquests.NiquestsAsyncClient

::: unihttp.clients.zapros.ZaprosSyncClient

::: unihttp.clients.zapros.ZaprosAsyncClient

::: unihttp.clients.urllib.UrllibSyncClient
