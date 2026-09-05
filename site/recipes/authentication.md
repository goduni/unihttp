---
title: Add bearer authentication
description: Attach bearer tokens to unihttp requests with a typed middleware and keep credentials out of method declarations.
---

# Add bearer authentication

Use middleware to attach a token to every request. This excerpt needs
`HTTPRequest` from `unihttp.http.request`, `HTTPResponse` from
`unihttp.http.response`, and `Handler, Middleware` from
`unihttp.middlewares.base`.

```python
--8<-- "examples/recipes.py:auth"
```

Pass `middleware=[BearerAuth(token)]` to your client constructor, where
`token` comes from your application's configuration or credential provider.
For a reusable SDK, accept the token in its client constructor and attach the
middleware there.

For async clients, subclass `AsyncMiddleware`, use `AsyncHandler`, make
`handle` async, and return `await next_handler(request)`.

For authentication on a single endpoint, bind that method with its own
middleware. See [scope and ordering](../guides/middleware.md).

This recipe attaches a token; it does not implement OAuth token refresh.
If refresh is needed, design expiry, synchronization, and replay behavior
around the remote API's authentication contract.
