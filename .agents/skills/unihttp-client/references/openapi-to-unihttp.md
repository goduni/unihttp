# OpenAPI → unihttp mapping

How to translate an OpenAPI 3.x document into unihttp client code. The client
consumes the API, so an OpenAPI *response* becomes a method's return type and an
OpenAPI *request* becomes the method's marked fields.

## Operations

| OpenAPI                          | unihttp                                             |
| -------------------------------- | --------------------------------------------------- |
| Path + HTTP method               | One `BaseMethod` subclass                            |
| `operationId`                    | Class name (PascalCase) and bound method name (snake)|
| Path template `/pets/{petId}`    | `__url__ = "/pets/{petId}"`                          |
| HTTP verb                        | `__method__ = "GET"` (uppercase)                     |
| Success response schema          | Generic arg: `BaseMethod[Pet]`                       |
| `204` with no response body      | `BaseMethod[None]`                                   |
| `200`/`204` returning `{}`        | `BaseMethod[dict[str, Any]]` — NOT `None` (see note) |
| `tags[0]` / first path segment   | Grouping into modules/subpackages, or a name prefix  |

Bind every operation on the client with `bind_method`. Use a hand-written
`call_method` method only when the call needs real extra logic.

> **Return type vs. `make_response`.** A method's `make_response` *always*
> deserializes `response.data` into the declared return type — it never special-
> cases `None`. So `BaseMethod[None]` works only when the body is genuinely empty
> (a real `204` with no content). If an endpoint returns an empty JSON object `{}`
> (common for `DELETE` — JSONPlaceholder does this), use
> `BaseMethod[dict[str, Any]]`; `BaseMethod[None]` then raises
> `TypeLoadError: expected_type=None, input_value={}`.

## Parameters and bodies

| OpenAPI parameter `in` / body            | Marker                       |
| ---------------------------------------- | ---------------------------- |
| `in: path`                               | `Path[T]`                    |
| `in: query`                              | `Query[T]`                   |
| `in: header`                             | `Header[T]`                  |
| `requestBody` `application/json`         | `Body[T]`                    |
| `application/x-www-form-urlencoded`      | `Form[T]`                    |
| `multipart/form-data` file part          | `File[UploadFile]`           |
| `multipart/form-data` scalar part        | `Form[T]`                    |
| `in: cookie`                             | not a marker — set via header/middleware |

Rules:

- Each `{placeholder}` in the path needs a matching `Path` field with the same name.
- **Optional `query`/`header` params that must disappear when not supplied: use
  `Query[Omittable[T]] = Omitted()` (from `unihttp.omitted`), NOT a plain
  `= None`.** A `None` default is serialized literally — it sends `?param=None`,
  and the aiohttp backend raises `TypeError: Invalid variable type ... got None`.
  The `Omitted` sentinel is dropped from the request entirely. Same for optional
  body fields: `Body[Omittable[T]] = Omitted()`. It must be the direct
  `= Omitted()` default — `field(default_factory=Omitted)` is **not** recognised as
  the omit default and leaks the sentinel into the request. (`= Omitted()` trips
  ruff `RUF009`; that is a false positive — the generated `ruff.toml` ignores it.)
- A single `Body[Model]` field nests the model under the field name:
  `payload: Body[PostCreate]` serialises to `{"payload": {...}}`, not a bare
  object. For a **flat** JSON body (the common REST case), use scalar `Body`
  fields named after the schema's properties (e.g. `title: Body[str]`,
  `user_id: Body[int]`). The wire key is the *Python* field name — `user_id` is
  sent as `"user_id"` unless you add wire-name mapping (see "Wire names" below).
  For a camelCase API you **must** map `user_id → userId`, or the create body is
  silently wrong.
- `Body` cannot coexist with `Form`/`File` on one method.

## Schemas → DTOs

| OpenAPI schema                       | Python (adaptix + dataclasses)            |
| ------------------------------------ | ----------------------------------------- |
| `type: object`                       | `@dataclass`                              |
| `enum`                               | `enum.StrEnum` (strings) / `enum.IntEnum` |
| `type: string` / `integer` / etc.    | `str` / `int` / `float` / `bool`          |
| `format: date-time` / `date`         | `datetime.datetime` / `datetime.date`     |
| `format: uuid`                       | `uuid.UUID`                               |
| `format: byte` / `binary`            | `bytes`                                   |
| `type: number` needing exactness     | `decimal.Decimal` (else `float`)          |
| `type: array, items: X`              | `list[X]`                                 |
| `additionalProperties: X`            | `dict[str, X]`                            |
| `nullable: true` / `oneOf [X, null]` | `X \| None`                               |
| `oneOf` / `anyOf`                    | `X \| Y` (`Union`)                        |
| `allOf`                              | merge fields into one dataclass, or compose |
| `$ref`                               | reuse the referenced dataclass (do not duplicate) |

Guidance:

- **Wire names.** Keep Python fields snake_case; map non-Pythonic wire names with
  adaptix `name_mapping` in the client's `Retort` instead of renaming attributes.
  Two things the request side depends on:
  - `name_mapping` applies to **`BaseMethod` subclasses too**, not just response
    models. The camelCase wire names (`userId`, `postId`, …) live on your methods'
    `Body`/`Query` fields, so those classes need mapping as well — mapping only the
    response models leaves create/update bodies and query filters wrong.
  - For an all-camelCase API, prefer **one global** `name_mapping(map={...})` with
    **no class predicate**: it renames the listed fields across every model,
    request body, and query filter at once — far simpler than one mapping per
    class. E.g. `DEFAULT_RETORT.extend(recipe=[name_mapping(map={"user_id":`
    `"userId", "post_id": "postId", "album_id": "albumId", "thumbnail_url":`
    `"thumbnailUrl", "catch_phrase": "catchPhrase"})])`.
  - Caveat: a global map renames **`Path` fields too**. A `post_id: Path[int]` for
    `/posts/{post_id}/...` then breaks at request build with
    `KeyError: 'post_id'` — the path key becomes `postId` while the template still
    says `{post_id}`. Keep `Path` field names equal to their `{placeholder}` and
    out of the global map: name a nested route's path param `id`, or write the
    placeholder using the wire name.
- **Split request vs response models** when the response carries server-owned
  fields the request must not send (`id`, `created_at`, `*_url`, tokens). Name
  them e.g. `PetCreate` (request) and `Pet` (response).
- Encode constraints (defaults, enums) where the serializer expresses them
  cleanly; do not invent validation the spec does not state.
- **Field types work out of the box.** `DEFAULT_RETORT` loads and dumps
  `datetime`/`date` (ISO-8601, including a trailing `Z`/UTC offset), `UUID`,
  `Decimal`, `bytes`, and `Enum` with no extra config — just annotate the field
  with the Python type. A `StrEnum`/`IntEnum` in a `Query`/`Body` field is sent as
  its `.value` (`State.open` → `"open"`).
- **Request vs response enums.** Legal values can differ between a request filter
  and a response field (e.g. an issue `state` *filter* allows `open|closed|all`
  while a returned issue is only `open|closed`). Model them as two enums when they
  diverge.
- **Unions.** adaptix resolves untagged `oneOf`/`anyOf` by trying each member, so
  distinct shapes work as-is: `Dog | Cat`, `int | str`, `X | None`. Switch that
  client to the pydantic serializer only when union members **overlap ambiguously**
  or the spec uses a real **discriminator** you must honor.

## Security → auth

| OpenAPI security scheme              | Client wiring                                          |
| ------------------------------------ | ------------------------------------------------------ |
| `apiKey` in header                   | `Header[str]` field, or an auth middleware setting it  |
| `apiKey` in query                    | `Query[str]` field, or a middleware setting it each call |
| `http` `bearer`                      | middleware adding `Authorization: Bearer <token>`      |
| `http` `basic`                       | middleware adding the `Authorization: Basic ...` header|
| `oauth2` / `openIdConnect`           | leave a `TODO` for the token flow; inject the resulting access token as a bearer header |

Prefer a single auth middleware (`AsyncMiddleware` for async clients,
`Middleware` for sync) over repeating a `Header` field on every method.

## Errors

- Map documented non-2xx status codes to exceptions with
  `AsyncErrorMapperMiddleware` / `SyncErrorMapperMiddleware`
  (`{HTTPStatus.NOT_FOUND: NotFound, ...}`), or override the client's
  `handle_error`.
- If the API has a structured error body, model it as a dataclass and raise a
  typed exception carrying it.
- Reuse the built-in exceptions where they fit:
  `unihttp.exceptions.{ClientError, ServerError, HTTPStatusError, NetworkError, RequestTimeoutError}`.

## Pagination

unihttp has no built-in pagination — model it explicitly:

- **Page/offset query params**: expose them as optional `Query` fields
  (`page: Query[Omittable[int]] = Omitted()`, `per_page: ...`) and let the caller
  loop. Don't hide them.
- **Envelope responses** (`{"data": [...], "next": "...", "total": N}`): model the
  envelope as a DTO holding a `list[Item]` plus the cursor/total fields, and return
  `BaseMethod[PageOfItem]` — NOT `BaseMethod[list[Item]]` (the body is an object,
  not a bare array).
- **Cursor / `Link`-header pagination**: the cursor lives in a *response header*,
  but `bind_method` exposes only the body. Override the method's `make_response` to
  read `response.headers["Link"]` and return a page-wrapper DTO
  (`BaseMethod[IssuePage]` holding `items` + `next_link`) — see "Read response
  headers" in the companion `unihttp` skill. Add an async-generator helper that
  loops only if the user asks; otherwise leave a `TODO`. Do not invent auto-paging.

## Worked snippet

OpenAPI:

```yaml
/pets/{petId}:
  get:
    operationId: getPet
    parameters:
      - name: petId
        in: path
        required: true
        schema: { type: integer }
    responses:
      "200":
        content:
          application/json:
            schema: { $ref: "#/components/schemas/Pet" }
```

unihttp method (`methods/get_pet.py`):

```python
from dataclasses import dataclass

from unihttp.method import BaseMethod
from unihttp.markers import Path

from petstore_client.models.pet import Pet


@dataclass
class GetPet(BaseMethod[Pet]):
    __url__ = "/pets/{petId}"
    __method__ = "GET"

    petId: Path[int]  # noqa: N815 — matches the path placeholder
```

If you prefer a snake_case field, rename the placeholder too
(`/pets/{pet_id}` + `pet_id: Path[int]`) — keep the field name and the
placeholder identical.
