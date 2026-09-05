---
title: Define methods and request parameters
description: Map typed dataclass fields to HTTP paths, query strings, headers, JSON, forms, files, and raw request bodies.
---

# Define methods and request parameters

Import from submodules, such as `unihttp.method` and `unihttp.markers`.
The top-level `unihttp` package does not re-export these names.

A method is a dataclass subclass of `BaseMethod[Result]`. Set `__url__` and
`__method__`, then mark each parameter with its HTTP location.

## JSON request bodies

This excerpt defines a method returning a `User`. Import `dataclass` from
`dataclasses`, `Body` from `unihttp.markers`, and `BaseMethod` from
`unihttp.method`.

```python
--8<-- "examples/recipes.py:models"
```

Binding it with `create_user = bind_method(CreateUser)` gives a method that
accepts `name="Ada"` and sends `{"name": "Ada"}`.

A field `user: Body[User]` sends a **nested** object
`{"user": {"id": 1, "name": "Ada"}}`. Do not assume it flattens the model.

## Marker reference

| Marker | Location | Example |
| --- | --- | --- |
| `Path[T]` | URL placeholder | `user_id: Path[int]` |
| `Query[T]` | Query string | `page: Query[int] = 1` |
| `Header[T]` | Request header | `authorization: Header[str]` |
| `Body[T]` | JSON object field | `name: Body[str]` |
| `Form[T]` | Form field | `caption: Form[str]` |
| `File[T]` | Multipart file | `avatar: File[UploadFile]` |
| `Raw[T]` | Entire raw body | `content: Raw[bytes]` |

Every URL placeholder needs a matching path field. Missing placeholders fail
when building the request. Header wire names and camelCase fields can be
configured with [Adaptix name mapping](serialization.md#rename-fields-without-changing-python-names).

`Body` cannot be combined with `Form` or `File`. `Raw` cannot be combined
with any of those three. Use `Form` for the scalar fields of a multipart request.

**Raw bodies currently require Adaptix or a custom dumper.** The Pydantic and
msgspec dumpers do not emit a raw body. See [serialization](serialization.md).

For an entire byte payload, import `Raw` from `unihttp.markers` and define:

```python
--8<-- "examples/recipes.py:raw"
```

This method sends bytes and expects a JSON acknowledgement such as
`{"size": 7}`. `Raw` controls the **request body only**; the response still passes
through the configured loader. Set an appropriate `Content-Type` header for the
remote endpoint; a raw body does not imply a JSON content type.

For a binary response, use [streaming](streaming.md), which bypasses response
deserialization, or explicitly customize response processing. Declaring
`BaseMethod[bytes]` alone is not sufficient with the default Adaptix loader:
it expects a base64 string when loading bytes, not a raw HTTP byte payload.

## Binding and custom methods

Prefer `bind_method` for a direct endpoint. When you need preprocessing,
compose a normal client method that calls
`self.call_method(CreateUser(name=name.strip()))`.

`call_method` accepts a method instance and returns the declared result.
It is awaitable on async clients. Streaming uses
[StreamMethod](streaming.md) and `call_method_stream`.

<span id="url-joining-and-optional-fields"></span>

## URL joining

All built-in unihttp backends combine `base_url` with the method's URL using
`urllib.parse.urljoin` before passing the result to the HTTP library. This is
unihttp's URL handling, not the underlying library's `base_url` behavior.

With `base_url="https://example.com/api/"`:

- `/users` resolves to `https://example.com/users`, replacing the `/api/` prefix.
- `users` resolves to `https://example.com/api/users`, preserving the prefix.

To preserve a path prefix, keep the trailing slash on `base_url` and omit the
leading slash from the method's URL. Without the trailing slash,
`https://example.com/api` combined with `users` resolves to
`https://example.com/users`.

## Optional fields

Use [Omitted](../recipes/partial-updates.md) to distinguish an absent parameter
from an explicit `None`. Query encoding of booleans and lists is
backend-dependent; verify it against the target API.
