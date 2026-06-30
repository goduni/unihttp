---
name: unihttp-client
description: Generate a typed, packaged unihttp API client library (SDK) from an OpenAPI 3.x spec or a plain API description. Produces typed DTOs, BaseMethod definitions, a client class, ruff + mypy (strict) config, sensible contract tests, and packaging. Use when the user wants to scaffold, bootstrap, or generate an API client / SDK on top of unihttp.
---

# unihttp client generator

Generate a **runnable, packaged API client** on top of `unihttp` from either an
OpenAPI 3.x specification or a written API description. The output is an
installable Python package with typed models, declarative methods, a client
class, `ruff` + `mypy` (strict) config, and a small set of common-sense tests.

Always write **idiomatic** unihttp code — load the companion `unihttp` skill (or
[../unihttp/SKILL.md](../unihttp/SKILL.md)) for the Wrong/Correct rules. The most
important one: **import from submodules** (`unihttp.method`, `unihttp.markers`,
`unihttp.bind_method`), never from the empty top-level `unihttp` package.

Defaults (override only when the user or spec asks):

- **Serializer:** adaptix + stdlib dataclasses.
- **Backend:** `aiohttp` async (`AiohttpAsyncClient`); use `requests`
  (`RequestsSyncClient`) when the user wants a synchronous client.
- **Layout:** one file per method, model, and enum (see
  [references/package-layout.md](references/package-layout.md)).
- **Tests:** contract tests at the unihttp seam (`build_http_request` /
  `make_response`) — only `pytest` needed, no HTTP-mock library.

Map OpenAPI constructs with [references/openapi-to-unihttp.md](references/openapi-to-unihttp.md).

## Workflow

### 1. Establish the input mode

- **OpenAPI spec** (file path, URL, or pasted document): confirm `openapi` is
  `3.0.x` or `3.1.x`. If it is older, ambiguous, or incomplete, say so before
  generating. Extract: tags / path groups, `operationId`s, parameters
  (path/query/header), request bodies, response schemas + status codes, reusable
  `components.schemas`, and security schemes. Flag hard constructs early:
  `oneOf`, `anyOf`, `allOf`, discriminators, multiple media types, file uploads.
- **API description** (no spec): gather, per endpoint, the method, URL template,
  path/query/header params, request body shape, and the response shape. Ask for
  the missing pieces rather than inventing them.

### 2. Confirm the essentials with the user (only what you cannot infer)

- Package/distribution name and import name.
- Sync or async (default async/aiohttp).
- Auth scheme (header token, bearer, API key, …) if the spec declares one.
- Whether to scaffold a fresh project or add the client into an existing repo.

Keep this short — infer sensible defaults and state them rather than
interrogating.

### 3. Plan the package layout

Mirror unihttp's own conventions: `src/<import_name>/` layout, `hatchling`
build, `ruff.toml` + `mypy.ini`, `py.typed`. Use **one file per symbol**:
`models/<model>.py`, `enums/<enum>.py`, `methods/<operation>.py`, and a single
`client.py`. Re-export the public surface from `__init__.py`. For a very small
API (a handful of endpoints), it is fine to collapse models into one
`models.py` — use judgement, do not over-fragment a 3-endpoint client.

The full tree and file templates are in
[references/package-layout.md](references/package-layout.md).

### 4. Generate DTOs (models and enums)

- One `@dataclass` per schema; one `enum.StrEnum`/`IntEnum` per enumerated type.
- Keep idiomatic snake_case Python fields. Preserve wire names via adaptix
  `name_mapping` in the client's `Retort`, not by renaming attributes.
- Split request and response models when the response adds server-owned fields
  (id, timestamps, computed values).
- Reuse shared schemas across operations instead of duplicating classes.
- Map `nullable` / `oneOf null` to `T | None`; `oneOf`/`anyOf` to `Union`;
  `allOf` to composition or a merged dataclass.

### 5. Generate methods

One `BaseMethod[ResponseType]` per operation, in `methods/<operation>.py`:

- Class name from `operationId` (PascalCase); else `<Verb><Resource>`
  (`GetUser`, `CreateUser`, `ListUsers`).
- `__url__` = the path template, `__method__` = the HTTP verb (uppercase).
- Map parameters to markers (`Path`/`Query`/`Header`), request body to `Body`,
  form to `Form`, file uploads to `File` + `UploadFile`. See the mapping table.
- For paginated list endpoints, model the response envelope as a DTO (not a bare
  `list`) or expose page/offset as optional `Query` fields — see "Pagination" in
  the mapping reference. `datetime`/`date`/`UUID`/`Decimal`/`Enum` fields need no
  special handling (adaptix loads them from their standard string forms).
- The generic argument is the response model. Use `None` ONLY for a genuinely
  empty body (a real `204` with no content); if the endpoint returns an empty
  object `{}` (common for `DELETE`), use `BaseMethod[dict[str, Any]]` — `None`
  raises `TypeLoadError` because `make_response` always deserializes the body.

### 6. Generate the client

A single `*Client` subclass in `client.py`:

- Inherit `AiohttpAsyncClient` (async, default) or `RequestsSyncClient` (sync).
- Bind each operation with `bind_method`.
- Build a `Retort` (extend `DEFAULT_RETORT`) carrying any `name_mapping`, and
  pass `AdaptixDumper(retort)` / `AdaptixLoader(retort)`. The mapping must cover
  the **method** classes (`Body`/`Query` fields), not only response models — for
  an all-camelCase API use one global `name_mapping(map={...})` with no class
  predicate, which renames bodies, query filters, and models at once.
- Accept `base_url` and auth inputs in `__init__`; **default `base_url` from the
  spec's `servers[0].url`** so callers can construct the client with no args.
  Inject auth via a `Header` field on methods or an auth middleware
  (`AsyncMiddleware` for async clients; type `next_handler` as `AsyncHandler`).
- For endpoints needing pre/post logic, write an explicit method using
  `call_method` instead of `bind_method`.

### 7. Handle auth and errors

- Simple token/api-key auth: add it as a header (middleware or per-method
  `Header`). Leave a `TODO` for OAuth/refresh flows rather than inventing them.
- Map documented error status codes to exceptions with
  `AsyncErrorMapperMiddleware` / `SyncErrorMapperMiddleware`, or override
  `handle_error`. Keep a small exceptions module if the API has a real error
  taxonomy.

### 8. Generate packaging

Produce `pyproject.toml` (hatchling, `src` layout), `ruff.toml`, `mypy.ini`,
`py.typed`, `.gitignore`, and a `README.md` with install + quickstart. Runtime
dependency is `unihttp` with the chosen extras, e.g.
`unihttp[aiohttp,adaptix]>=0.2.9`. Dev dependencies for the default tests are just
`ruff`, `mypy`, `pytest`. In `ruff.toml` use `extend-exclude` (not `exclude`) so
ruff keeps ignoring `.venv`. Templates in
[references/package-layout.md](references/package-layout.md).

### 9. Generate common-sense tests

Default to **contract tests** at the unihttp seam — they cover exactly what
generated code introduces and avoid flaky HTTP-mock dependencies:

- Per operation, assert `Method(...).build_http_request(dumper)` produces the
  right `url` / `method` / `query` / `body` (markers wired correctly).
- Per response model, assert
  `Method(...).make_response(HTTPResponse(...), response_loader=loader)` parses
  into the right DTO. Call it by **keyword** (`response_loader=`) — that is how
  `call_method` invokes it, so a method overriding `make_response` with a wrong
  parameter name is caught instead of silently passing a positional test.
- These are synchronous and backend-agnostic — only `pytest` is needed, the same
  for async (aiohttp) and sync (requests) clients. See
  [references/package-layout.md](references/package-layout.md).

Optionally add **one** full-pipeline test through a mocked transport, but treat it
as an extra. Note that `aioresponses` lags new `aiohttp` releases (it breaks on
aiohttp 3.14), so pin a compatible pair, prefer `respx` for httpx clients, or use
a local `pytest-aiohttp` server. Skip property-based / contract fuzzing unless the
user asks.

### 10. Verify before claiming done

Run, from the generated package, and report real output:

```bash
ruff check .
ruff format --check .
mypy
pytest
```

Freshly generated code routinely needs one `ruff check --fix` + `ruff format`
pass before it is clean (import grouping, long `__all__` lines). Run those first,
then the gate. Fix what remains. Do not claim the package is correct until these
pass (or explicitly report what does not and why).

## Output checklist

- `pyproject.toml` (+ `ruff.toml`, `mypy.ini`, `py.typed`) when scaffolding a package.
- A DTO per request/response schema that matters; an enum per enumerated type.
- A `BaseMethod` per operation; a single client binding them.
- A `Retort` carrying wire-name mappings when the API is not snake_case.
- Minimal contract tests (seam-level), or a clear note on why tests were skipped.
- `README.md` with install and a runnable quickstart (using `async with` for
  async clients).
- A short report of `ruff` / `mypy` / `pytest` results.
