---
title: Serialization
description: Choose Adaptix, Pydantic, or msgspec for unihttp. Configure field names, custom value conversion, typed responses, and the HTTP JSON codec.
---

# Serialization

**Adaptix is the recommended serializer for new unihttp clients.** It works
with plain dataclasses and TypedDicts, keeps conversion rules outside your
models, and supports field-name mapping and raw request bodies.

If your application already uses Pydantic or msgspec models, reuse them with
the matching integration. Adaptix is a recommendation, not an automatic default:
you explicitly configure a `request_dumper` and a `response_loader`.

| Integration | Choose it when |
| --- | --- |
| **Adaptix — recommended** | You want dataclasses or TypedDicts and configurable request/response conversion. |
| Pydantic | You already use `BaseModel` response models and their validation rules. |
| msgspec | You already use `msgspec.Struct` response models. |

## Connect a serializer

The **dumper** converts a method instance into request components such as
query parameters and body fields. The **loader** converts a parsed response
body into the method's declared result type.

Choose the serializer extra alongside your HTTP backend in
[Installation](../getting-started/installation.md). The following alternatives
all describe the same endpoint: send a user name and receive a typed `User`.
Method declarations remain dataclasses in every variant.

=== "Adaptix"

    ```python
    --8<-- "examples/serialization/adaptix.py:setup"
    ```

=== "Pydantic"

    ```python
    --8<-- "examples/serialization/pydantic.py:setup"
    ```

=== "msgspec"

    ```python
    --8<-- "examples/serialization/msgspec.py:setup"
    ```

Pass `request_dumper` and `response_loader` to your client constructor, as in
the [quickstart](../getting-started/quickstart.md). You can bind `CreateUser`
with `bind_method` or pass an instance to `call_method`.

In all three variants:

- `CreateUser(user_name="Ada")` produces the body fields `{"user_name": "Ada"}`.
- A response `{"id": 1, "user_name": "Ada"}` becomes a `User` instance.
- The serializer choice does not depend on the HTTP backend or sync/async mode.

<span id="adaptix-serialization"></span>

## Customize Adaptix

A **retort** holds Adaptix's loading and dumping rules. Start from unihttp's
`DEFAULT_RETORT`: it includes support for request markers, omitted fields,
uploads, and raw request bodies. By default it also ignores extra response
fields, so your DTO can model only the data your application needs.

Use `DEFAULT_RETORT.extend(recipe=[...])` to add rules while retaining these
integrations. It returns a new retort without modifying the original.
Create it once during client setup and reuse it for subsequent calls.

The examples below use `User` and `CreateUser` from the **Adaptix** tab above.

### Rename fields without changing Python names

Suppose the API uses `userName`, but your Python fields use `user_name`.
Import `name_mapping` from `adaptix` and configure both directions:

```python
--8<-- "examples/serialization/customization.py:global-mapping"
```

Now `CreateUser(user_name="Ada")` produces `{"userName": "Ada"}`, and
`{"id": 1, "userName": "Ada"}` loads as `User(id=1, user_name="Ada")`.

This rule applies to every model and method field named `user_name` handled
by that retort. If only these two types use the API's spelling, scope the rule:

```python
--8<-- "examples/serialization/customization.py:scoped-mapping"
```

Use `AdaptixDumper(scoped_retort)` and `AdaptixLoader(scoped_retort)` with this
variant. Mapping the response model alone does not rename fields declared on
the request method: both classes need a rule.

### Transform a value before sending it

You can also change a field's value without changing the method definition.
For example, trim surrounding whitespace from a user name before sending it.
Import `P` and `dumper` from `adaptix`:

```python
--8<-- "examples/serialization/customization.py:normalize"
```

`P[CreateUser].user_name` selects that field on that method only.
The new retort extends the name-mapping example, so
`CreateUser(user_name="  Ada  ")` produces `{"userName": "Ada"}`.

The method instance is not mutated. This is a dumping rule: it does not trim
names when loading a response. Use a `loader` rule for input conversion.

### Read and write a custom wire format

Suppose an events API sends Unix timestamps, while your Python code uses
timezone-aware `datetime` values. Add these imports:

```python
from datetime import UTC, datetime

from adaptix import P, dumper, loader
```

Define the response model and request method using the Python type:

```python
--8<-- "examples/serialization/customization.py:event-models"
```

Then configure the response field's loader and the request field's dumper:

```python
--8<-- "examples/serialization/customization.py:timestamps"
```

| Direction | Input | Converted value |
| --- | --- | --- |
| Response → model | `{"id": 1, "starts_at": 1704067200}` | `Event(id=1, starts_at=datetime(2024, 1, 1, tzinfo=UTC))` |
| Method → body | `CreateEvent(starts_at=datetime(2024, 1, 1, tzinfo=UTC))` | `{"starts_at": 1704067200.0}` |

Use aware datetimes so the timestamp does not depend on the machine's local
timezone. Custom conversion functions are responsible for accepting and
validating the API's wire format; these rules do not change unrelated fields.

For more recipes and selection rules, see the official
[Adaptix loading and dumping tutorial](https://adaptix.readthedocs.io/en/latest/loading-and-dumping/tutorial.html)
and [name-mapping reference](https://adaptix.readthedocs.io/en/latest/loading-and-dumping/extended-usage.html#name-mapping).

## What is shared, and what differs

### Optional and nested fields

All three integrations support ordinary marked request fields. With the
documented `Omittable[T] = Omitted()` pattern, they omit the field instead of
sending the sentinel. See [Optional fields and Omitted](../recipes/partial-updates.md)
for query, header, and body examples; omission is not specific to PATCH.

A field such as `user: Body[User]` produces a nested `user` object.
It does not flatten the model into the outer request body.

### Validation errors

Response model validation or conversion errors propagate from the chosen
serialization library. A successful HTTP status does not guarantee that the
response matches your model. See [error handling](errors.md) for where
validation and response loading occur in the request pipeline.

<span id="pydantic-serialization"></span>

### Pydantic specifics

The loader uses Pydantic's `TypeAdapter` to validate the declared response
type, including your `BaseModel` configuration. The request dumper uses
the method dataclass's field names as request keys. An alias on a response
model does not rename a separate method field.

See [Pydantic's documentation](https://docs.pydantic.dev/latest/) for model
validation and aliases.

<span id="msgspec-serialization"></span>

### msgspec specifics

The request dumper converts field values with `msgspec.to_builtins`; the loader
uses `msgspec.convert` to construct your declared response type.
Selecting these classes does not switch the HTTP client's JSON codec to
`msgspec.json`.

See [msgspec's documentation](https://jcristharif.com/msgspec/) for model
configuration and conversion behavior.

### Raw request bodies

Adaptix supports `Raw` fields. The Pydantic and msgspec dumpers currently
populate path, query, header, body, file, and form data, but not `raw`.
For raw payloads, use Adaptix or implement your own
[request dumper](../reference/serializers.md).

## Unwrap a response envelope

If an API wraps its payload in `data`, configure an Adaptix loader with
`Chain.FIRST` to extract it before model loading. This keeps the transformation
in the Retort instead of repeating it in each method's `make_response`.
See [Unwrap a JSON envelope](responses.md#unwrap-a-json-envelope) for the recipe,
client configuration, and type-scoping considerations.

## JSON codec versus model serialization

`json_dumps` and `json_loads` control the HTTP transport's JSON encoding and
decoding. They do not replace the dumper that extracts request fields or the
loader that constructs your response model.

For example, install `orjson`, import it, and add these arguments to your
existing client constructor:

```python
--8<-- "examples/json_codec.py:codec"
```

Keep the same `request_dumper` and `response_loader`. The dump callable must
return a string, which is why the example decodes the bytes returned by
`orjson.dumps`.

An empty response may be represented as `None`, and non-JSON response handling
depends on the backend. Make your method's response handling match the API;
choosing a JSON codec does not turn arbitrary response bytes into a typed model.
For binary downloads, use [streaming](streaming.md). For response headers and
status alongside a model, see [Response data and metadata](responses.md).
