---
title: Optional fields and Omitted
description: Omit optional query parameters, headers, and body fields with unihttp Omittable and Omitted, independently of the HTTP method.
---

<span id="omit-fields-in-partial-updates"></span>

# Optional fields and Omitted

Use `Omitted()` when a request field should not be sent. It is independent of
the HTTP method: an optional GET filter, a POST body field, and a PATCH update
all use the same mechanism. The field's marker determines its location;
`Omitted()` determines whether it is included.

## Omitted is not None

`Omittable[T]` is an alias for `T | Omitted`. It allows the sentinel as a value;
the default `= Omitted()` also lets callers leave the argument out.

- `Omittable[str]` accepts a string or omission; it does not include `None`.
- `Omittable[str | None]` additionally allows an explicit `None`.
- `str | None` alone allows null, but does not express omission.

For a JSON body field, `None` becomes JSON `null`, while `Omitted()` leaves the
key out. An empty string or zero is still a supplied value, not omission.
Whether the server applies a default, clears a value, or rejects an absent or
null field is part of the endpoint's contract, not determined by unihttp.

## Optional query parameters and headers

These examples share the following imports and response model:

```python
--8<-- "examples/optional_fields.py:setup"
```

For a GET endpoint, make filters and per-request headers omittable:

```python
--8<-- "examples/optional_fields.py:query"
```

`ListUsers()` adds no query parameters or method-level headers.
`ListUsers(name="Ada", limit=10, accept="application/json")` includes both
filters and the `Accept` header. Middleware or the HTTP session may still add
headers of their own.

Use `Omitted()`, not `None`, to leave out query parameters and headers. These
locations have no JSON null representation: the HTTP backend may encode or
reject `None` differently. Required URL placeholders still need concrete
`Path` values; omission does not make a path segment optional.

## Optional JSON body fields

The same pattern works for a POST endpoint. Here `name` is required, while
`nickname` can be omitted, set to a string, or explicitly set to null:

```python
--8<-- "examples/optional_fields.py:body"
```

| Method instance | Serialized body fields |
| --- | --- |
| `CreateUser(name="Ada")` | `{"name": "Ada"}` |
| `CreateUser(name="Ada", nickname=None)` | `{"name": "Ada", "nickname": null}` |
| `CreateUser(name="Ada", nickname="Countess")` | `{"name": "Ada", "nickname": "Countess"}` |

These method definitions are backend-independent and work with sync or async
clients. Bind them with `bind_method` or pass an instance to `call_method`, as
described in [methods and parameters](../guides/methods.md#binding-and-custom-methods).

## Example: partial updates with PATCH

PATCH is one application of omission, not a requirement for it. For an API
that treats missing fields as unchanged and null as clearing a value, an
update method can look like this. Import `Path` from `unihttp.markers` and use
the imports and `User` model above:

```python
--8<-- "examples/recipes.py:partial"
```

| Call arguments | Serialized body fields |
| --- | --- |
| `user_id=1, name="Ada"` | `{"name": "Ada"}` |
| `user_id=1, name=None` | `{"name": null}` |
| `user_id=1` | No body fields |

The `User` response model above has a non-nullable `name`; make it nullable
if this endpoint returns null after clearing the name.

An entirely empty body dictionary may become no request body at the transport
layer, rather than a literal JSON `{}`. Check what your API accepts.

## Serializer setup

The examples work with `AdaptixDumper(DEFAULT_RETORT)`, `PydanticDumper()`, and
`MsgspecDumper()`. Omission is handled during request serialization, before the
HTTP backend sends the request. A custom dumper must implement omission itself.

Use the direct `= Omitted()` default for consistency across integrations;
do not substitute `field(default_factory=Omitted)`, which Adaptix's omission
provider does not treat as the same default. When customizing Adaptix, extend
`DEFAULT_RETORT` to retain its omission support.

See [serialization](../guides/serialization.md) for serializer configuration.
