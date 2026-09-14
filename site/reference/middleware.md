---
title: Middleware and exceptions
description: Middleware handlers, retry and status-mapping configuration, logging, and the unihttp exception hierarchy.
---

# Middleware and exceptions

Sync `Handler` and async `AsyncHandler` are callable aliases exported by `unihttp.middlewares`. Match the middleware variant to the client. See [middleware ordering](../guides/middleware.md) and [retry behavior](../recipes/retries.md).

`HTTPStatusError` exposes `response` and `status_code`. Status errors require explicit handling; default response hooks do not raise automatically. Every client backend translates its own exceptions into `NetworkError`, `RequestTimeoutError`, `NonRetryableError`, or plain `UniHTTPError`, keeping the original as `__cause__`.

::: unihttp.middlewares.base.Middleware

::: unihttp.middlewares.base.AsyncMiddleware

::: unihttp.middlewares.error_mapper.SyncErrorMapperMiddleware

::: unihttp.middlewares.error_mapper.AsyncErrorMapperMiddleware

::: unihttp.middlewares.retry.RetryMiddleware

::: unihttp.middlewares.retry.AsyncRetryMiddleware

::: unihttp.middlewares.logging.LoggingMiddleware

::: unihttp.middlewares.logging.AsyncLoggingMiddleware

::: unihttp.exceptions
