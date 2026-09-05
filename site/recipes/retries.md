---
title: Retry transient failures
description: Safely scope unihttp retries to a buffered GET, combine them with HTTP error handling, and configure backoff for sync and async clients.
---

# Retry transient failures

Retry a call only when the remote operation is safe to repeat. The built-in
middleware does **not** filter by HTTP method: attaching it to an entire client
also retries POSTs and other operations that may create duplicate resources.

## Add retries to one GET method

This example reuses `GetUser`, `status_errors`, and `async_status_errors` from
[Error handling](../guides/errors.md). `GetUser.on_error` only raises for `404`;
it leaves server errors for middleware. `CreateUser` is the POST method from
[methods and parameters](../guides/methods.md).

The mapper is outermost and retry is inside it. Only `get_user` gets retries;
`create_user` still gets status handling, but is sent once.

```python
from unihttp.bind_method import bind_method
from unihttp.exceptions import NetworkError, RequestTimeoutError
```

=== "Sync"

    ```python
    from unihttp.clients.httpx import HTTPXSyncClient
    from unihttp.middlewares import RetryMiddleware

    --8<-- "examples/response_retries.py:sync"
    ```

=== "Async"

    ```python
    from unihttp.clients.httpx import HTTPXAsyncClient
    from unihttp.middlewares import AsyncRetryMiddleware

    --8<-- "examples/response_retries.py:async"
    ```

Construct the client with your base URL and serializers as usual. Calls keep
their normal signatures: `client.get_user(user_id=1)`, or await that call on
an async client. You can also scope middleware to
[one explicit call](../guides/middleware.md).

With this configuration:

- `503 → 503 → 200` returns the loaded user after three attempts.
- Three `503` responses raise `ServerError` after the last attempt.
- `404` immediately raises `UserNotFound`; it is not retried.
- A configured network failure or timeout is retried up to the same limit.
- A failed `create_user` is not repeated.

## Keep error handling outside retries

Middleware lists are outermost-first. `[status_errors, RetryMiddleware(...)]`
lets retry inspect each response before the mapper turns the final status into
an exception. Reversing that order raises too early for status-based retries.

Method and client hooks run inside the request handler. If they call
`raise_for_status()` on a `503`, retry receives a `ServerError`, not a response.
Prefer the mapper arrangement above for HTTP errors. If an existing hook must
raise, configure the specific exception types you intend to retry instead;
do not indiscriminately retry `ClientError`, `HTTPStatusError`, or `Exception`.

Validation exceptions can also interrupt an attempt. The final model conversion
runs outside middleware and is not retried. See
[the response pipeline](../guides/errors.md#understand-the-pipeline).

## Configure attempts and delays

`retries=2` means **up to three attempts**, including the original request.
The default is three retries, or four attempts total.

By default, status retries cover `500`, `502`, `503`, and `504`. Pass a non-empty
`status_codes` list to choose another set. Exceptions are not retried unless
included in `exceptions`; the example opts into `NetworkError` and
`RequestTimeoutError`.

The delay before retry number `attempt + 1` is `backoff * 2**attempt`, starting
at `attempt = 0`. Here the base delays are 0.5 and 1 second. With `jitter=True`,
each delay gets an additional random value between 0 and 1 second.

`429` is not retried by default, and the middleware does not interpret
`Retry-After`. If you need server-directed delays, this configuration alone
does not implement them.

## Retry only calls you can safely repeat

A timeout does not prove the server did nothing. Before enabling retries for a
write, check the API's idempotency guarantees and use its idempotency mechanism
where available. The request body must also be replayable: retry middleware
does not rewind file objects or consumed request streams for you.

Do not attach this buffered-call recipe to streaming downloads. It cannot
resume a partially consumed response, and opening another response can require
additional cleanup. See [streaming](../guides/streaming.md#errors-and-parsing).
