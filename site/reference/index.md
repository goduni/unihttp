---
title: API reference
description: Find unihttp public client classes, method binding, parameter markers, HTTP types, serializer protocols, middleware, and exceptions.
---

# API reference

Public signatures and types, generated from the library source.
For explanations and worked examples, use the [user guide](../guides/index.md).
For your first request, start with a [quickstart](../getting-started/quickstart.md).

| Looking for | Reference | Usage guide |
| --- | --- | --- |
| `BaseMethod`, `StreamMethod`, `bind_method` | [Methods and binding](methods.md) | [Declare requests](../guides/methods.md) |
| Client constructors and lifecycle hooks | [Clients](clients.md) | [Choose an HTTP backend](../integrations/backends.md) |
| `Path`, `Query`, `Body`, `Omitted` | [Markers and omitted values](markers.md) | [Optional fields](../recipes/partial-updates.md) |
| `HTTPRequest`, `HTTPResponse`, uploads and streams | [HTTP types](http.md) | [Response metadata](../guides/responses.md), [streaming](../guides/streaming.md) |
| `RequestDumper`, `ResponseLoader`, integrations | [Serializers](serializers.md) | [Serialization](../guides/serialization.md) |
| Handlers, retries, logging and exceptions | [Middleware and exceptions](middleware.md) | [Middleware](../guides/middleware.md), [errors](../guides/errors.md) |

Import symbols from their documented submodules, not from the top-level
`unihttp` package. Install the matching optional dependency before importing a
backend or serializer integration.
