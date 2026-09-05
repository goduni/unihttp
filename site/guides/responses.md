---
title: Work with response data and metadata
description: Return typed models and lists, unwrap JSON envelopes, and include HTTP status codes and headers in unihttp results.
---

# Work with response data and metadata

A regular, buffered call returns your declared Python result. You work with a
`User` or `list[User]`, rather than an HTTP response object.

This page builds on the [quickstart](../getting-started/quickstart.md). Configure
[HTTP error handling](errors.md#map-statuses-across-endpoints) before loading
responses: unihttp does not raise for unsuccessful statuses by default.

## Return a typed model or list

Given a response model:

```python
from dataclasses import dataclass

--8<-- "examples/response_metadata.py:model"
```

A `BaseMethod[User]` returns a `User`. For a JSON array such as
`[{"id": 1, "name": "Ada"}]`, declare `list[User]` instead:

```python
from unihttp.method import BaseMethod

--8<-- "examples/response_metadata.py:list"
```

Bind it with `list_users = bind_method(ListUsers)` on your client:

=== "Sync"

    ```python
    users = client.list_users()
    for user in users:
        print(user.name)
    ```

=== "Async"

    ```python
    users = await client.list_users()
    for user in users:
        print(user.name)
    ```

The configured response loader converts the body into the declared type.
See [serialization](serialization.md) for model support and field conversions.
Changing the return type does not change what the remote API sends.

## Unwrap a JSON envelope

If the API returns `{"data": {"id": 1, "name": "Ada"}}`, but callers should
receive just `User`, configure the response serializer once. With Adaptix, add
a loader that extracts `data` before normal model loading:

```python
from operator import itemgetter

from adaptix import Chain, loader
from unihttp.serializers.adaptix import DEFAULT_RETORT, AdaptixLoader

--8<-- "examples/response_metadata.py:envelope-loader"
```

Pass `response_loader=envelope_loader` when constructing the client. Keep your
request dumper unchanged. `Chain.FIRST` passes the extracted payload to Adaptix's
existing `User` loader, preserving its field conversion and validation.

The method only declares the result type; it does not need `make_response`:

```python
from unihttp.markers import Path

--8<-- "examples/response_metadata.py:envelope"
```

Bind `GetWrappedUser` as usual. The same response loader works with sync and async
clients and any method returning this wrapped `User`.

The rule targets **the type, not a particular endpoint**: every `User` loaded
by this Retort must have a `data` wrapper, including users nested in other models
or lists. It does not unwrap an envelope around an entire `list[User]`. If the
same API also returns plain users, use a separate response type for wrapped users
or a separate client/loader configuration. The plain array example above uses
the default loader, not `envelope_loader`.

This loader changes loading only; it does not add a wrapper when dumping `User`.
For the underlying mechanism, see Adaptix's
[provider chaining](https://adaptix.readthedocs.io/en/latest/loading-and-dumping/tutorial.html#provider-chaining).
Handle API-specific error envelopes with
[`validate_response`](errors.md#validate-an-error-inside-http-200) before loading.

## Return a model with response metadata

When callers need the status or a header alongside the body, declare a wrapper
as the method's result. Unlike a JSON envelope, HTTP metadata is not part of the
body passed to the serializer, so this is a use case for `make_response`.
Here the API returns plain user JSON and the client uses the default response
loader from the quickstart, without the envelope recipe above:

```python
from unihttp.http.response import HTTPResponse
from unihttp.serialize import ResponseLoader

--8<-- "examples/response_metadata.py:metadata"
```

The hook loads the body into `User`, then adds the status and `X-Request-ID`
header. A missing header becomes `None`. After binding this `GetUser`:

=== "Sync"

    ```python
    result = client.get_user(user_id=1)
    print(result.user.name, result.status_code, result.request_id)
    ```

=== "Async"

    ```python
    result = await client.get_user(user_id=1)
    print(result.user.name, result.status_code, result.request_id)
    ```

`HTTPResponse` also exposes `.cookies` and `.data`; see
[HTTP types](../reference/http.md) for all fields.

## How custom response loading works

`make_response` remains a regular `def`, even on async clients. Keep the parameter
name `response_loader`: the client passes it by keyword.

This hook runs after validation, error handling, and the middleware chain.
Exceptions from the final conversion propagate to the caller; middleware does
not intercept or retry them. See [the response pipeline](errors.md#understand-the-pipeline)
for the complete order.

## When the response is a stream

Streaming calls return `HTTPResponse` directly, with a stream in `.data`.
They do not call `make_response` or the buffered response loader. See
[streaming downloads](streaming.md) for reading and closing them safely.
