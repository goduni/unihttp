# Package layout and templates

The generated client is an installable package that mirrors unihttp's own
conventions: `hatchling` build, `src/` layout, `ruff` + strict `mypy`, `pytest`.
Use **one file per symbol** (method / model / enum), re-exported from
`__init__.py`. For a tiny API (a few endpoints) it is fine to collapse all models
into one `models.py` — use judgement.

## Tree

```
petstore-client/
├── pyproject.toml
├── ruff.toml
├── mypy.ini
├── .gitignore
├── README.md
├── src/
│   └── petstore_client/
│       ├── __init__.py          # re-export client + public models
│       ├── py.typed             # ship type information
│       ├── client.py            # the *Client class
│       ├── models/
│       │   ├── __init__.py
│       │   └── pet.py           # @dataclass Pet
│       ├── enums/
│       │   ├── __init__.py
│       │   └── pet_status.py    # StrEnum PetStatus
│       └── methods/
│           ├── __init__.py
│           ├── get_pet.py       # BaseMethod[Pet]
│           └── create_pet.py
└── tests/
    └── test_pets.py
```

## `pyproject.toml`

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/petstore_client"]

[project]
name = "petstore-client"
version = "0.1.0"
description = "Typed API client for the Petstore API, built on unihttp."
requires-python = ">=3.12"
readme = "README.md"
license = "MIT"
dependencies = [
    "unihttp[aiohttp,adaptix]>=0.2.9",
]

[dependency-groups]
dev = [
    "ruff",
    "mypy",
    "pytest",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

The default tests (below) exercise the request/response **contract** and need
only `pytest` — no HTTP-mock library and no async plugin. For a sync (`requests`)
client, swap the runtime extra to `unihttp[requests,adaptix]`; nothing else
changes. Add `pytest-asyncio` (+ `asyncio_mode = "auto"`) and an HTTP-mock library
only if you also write the optional full-pipeline test.

## `mypy.ini`

Mirror unihttp's strict config. The disabled codes accommodate the dataclass /
descriptor dynamism of `BaseMethod` and `bind_method`.

```ini
[mypy]
files = src/petstore_client
strict = true
python_version = 3.12
ignore_missing_imports = true
warn_unused_ignores = true
show_error_codes = true

disable_error_code =
  attr-defined,
  no-untyped-def,
  no-any-return,
  type-arg,
  no-untyped-call
```

## `ruff.toml`

A sensible strict-but-practical config. Docstring rules are off so generated
DTOs/methods need no docstrings.

```toml
line-length = 90
target-version = "py312"
src = ["src"]
# extend-exclude (not exclude) so ruff keeps its built-in excludes like .venv
extend-exclude = ["tests/"]

[lint]
select = ["E", "F", "I", "B", "C4", "N", "UP", "SIM", "RUF"]
ignore = [
    "N815",    # allow camelCase fields when they must match wire names
    "RUF009",  # `= Omitted()` is a singleton sentinel — safe as a dataclass default
]

[format]
quote-style = "double"
```

> The `RUF009` ignore matters whenever you use the `Omittable` pattern for
> optional fields (`field: Query[Omittable[T]] = Omitted()`): `RUF009` flags the
> `Omitted()` call in a dataclass default, but `Omitted` is a singleton sentinel,
> so it is safe and the warning is a false positive.

> Use `extend-exclude`, not `exclude`. Setting `exclude` **replaces** ruff's
> default exclude list (which contains `.venv`, `.git`, `__pycache__`, …), so a
> bare `exclude = ["tests/"]` makes `ruff check .` lint your whole virtualenv.

## `src/petstore_client/__init__.py`

```python
from petstore_client.client import PetstoreClient
from petstore_client.enums.pet_status import PetStatus
from petstore_client.models.pet import Pet

__all__ = ["Pet", "PetStatus", "PetstoreClient"]
```

`py.typed` is an empty marker file.

## Enums — `src/petstore_client/enums/pet_status.py`

```python
from enum import StrEnum


class PetStatus(StrEnum):
    available = "available"
    pending = "pending"
    sold = "sold"
```

## Models — `src/petstore_client/models/pet.py`

```python
from dataclasses import dataclass

from petstore_client.enums.pet_status import PetStatus


@dataclass
class Pet:
    id: int
    name: str
    status: PetStatus
    tag: str | None = None
```

`models/__init__.py` re-exports for convenience:

```python
from petstore_client.models.pet import Pet

__all__ = ["Pet"]
```

## Methods — `src/petstore_client/methods/get_pet.py`

```python
from dataclasses import dataclass

from unihttp.method import BaseMethod
from unihttp.markers import Path

from petstore_client.models.pet import Pet


@dataclass
class GetPet(BaseMethod[Pet]):
    __url__ = "/pets/{id}"
    __method__ = "GET"

    id: Path[int]
```

`src/petstore_client/methods/create_pet.py`:

```python
from dataclasses import dataclass

from unihttp.method import BaseMethod
from unihttp.markers import Body

from petstore_client.enums.pet_status import PetStatus
from petstore_client.models.pet import Pet


@dataclass
class CreatePet(BaseMethod[Pet]):
    __url__ = "/pets"
    __method__ = "POST"

    name: Body[str]
    status: Body[PetStatus]
```

## Client — `src/petstore_client/client.py`

The client hides the adaptix wiring so SDK users pass only `base_url` (and auth).

```python
from typing import Any

from unihttp.bind_method import bind_method
from unihttp.clients.aiohttp import AiohttpAsyncClient
from unihttp.serializers.adaptix import DEFAULT_RETORT, AdaptixDumper, AdaptixLoader

from petstore_client.methods.create_pet import CreatePet
from petstore_client.methods.get_pet import GetPet


class PetstoreClient(AiohttpAsyncClient):
    get_pet = bind_method(GetPet)
    create_pet = bind_method(CreatePet)

    def __init__(self, base_url: str, **kwargs: Any) -> None:
        super().__init__(
            base_url=base_url,
            request_dumper=AdaptixDumper(DEFAULT_RETORT),
            response_loader=AdaptixLoader(DEFAULT_RETORT),
            **kwargs,
        )
```

When the API uses non-snake_case wire names, build a module-level retort and pass
it instead of `DEFAULT_RETORT`:

```python
from adaptix import name_mapping

# One GLOBAL map (no class predicate) renames these fields on every model AND on
# every method's Body/Query fields — request bodies and query filters included.
# This is the simplest correct approach for an all-camelCase API.
_WIRE_NAMES = {"created_at": "createdAt", "user_id": "userId"}
_RETORT = DEFAULT_RETORT.extend(recipe=[name_mapping(map=_WIRE_NAMES)])
# ... AdaptixDumper(_RETORT) / AdaptixLoader(_RETORT)
```

Map per class (`name_mapping(Pet, map={...})`) only when the same Python field
name must map to different wire names on different classes. Remember the mapping
must cover the **method** classes too (`CreatePet`, `ListPets`, …), not just the
response models — otherwise create/update bodies and query filters keep the
snake_case names.

For a synchronous client, inherit `RequestsSyncClient`
(`from unihttp.clients.requests import RequestsSyncClient`) — everything else is
identical, minus `async`/`await`.

If the client injects its own `middleware` (e.g. an auth or constant-header
middleware), build that list inside `__init__` and pass it explicitly — don't also
forward `**kwargs` blindly, or a caller passing `middleware=` triggers a
duplicate-keyword `TypeError`. That same auth middleware is also where you set a
constant header such as an `Accept` version header, not only `Authorization`.

## Tests — `tests/test_pets.py` (default: contract tests)

The thing that actually varies in generated code is the **contract**: do the
markers build the right request, and does the return type parse the right DTO?
Test that seam directly — `BaseMethod.build_http_request` and
`BaseMethod.make_response` — using the same dumper/loader the client uses. These
tests are synchronous, backend-agnostic, deterministic, and need **only
`pytest`** — no HTTP-mock library, no event loop. They are the same whether the
client is async (aiohttp) or sync (requests).

```python
from unihttp.http.response import HTTPResponse
from unihttp.serializers.adaptix import DEFAULT_RETORT, AdaptixDumper, AdaptixLoader

from petstore_client.enums.pet_status import PetStatus
from petstore_client.methods.create_pet import CreatePet
from petstore_client.methods.get_pet import GetPet
from petstore_client.models.pet import Pet

dumper = AdaptixDumper(DEFAULT_RETORT)
loader = AdaptixLoader(DEFAULT_RETORT)


def test_get_pet_builds_request() -> None:
    request = GetPet(id=1).build_http_request(dumper)
    assert request.method == "GET"
    assert request.url == "/pets/1"


def test_create_pet_builds_body() -> None:
    request = CreatePet(name="Milo", status=PetStatus.pending).build_http_request(dumper)
    assert request.method == "POST"
    assert request.url == "/pets"
    assert request.body == {"name": "Milo", "status": "pending"}


def test_get_pet_parses_response() -> None:
    response = HTTPResponse(
        status_code=200,
        headers={},
        data={"id": 1, "name": "Rex", "status": "available"},
        cookies={},
        raw_response=None,
    )
    # Call make_response by keyword (`response_loader=`) exactly as `call_method`
    # does — so a method that overrides it with a wrong parameter name is caught.
    pet = GetPet(id=1).make_response(response, response_loader=loader)
    assert pet == Pet(id=1, name="Rex", status=PetStatus.available)
```

`HTTPRequest` exposes these assertable buckets: `url`, `method`, `path`, `query`,
`header`, `body`, `form`, `file` (note `header` and `file` are singular). Assert
`request.query` for query params, `request.form` for form fields, and
`request.file` for uploads — a `File[UploadFile]` field is **lowered to a
`(filename, bytes, content_type)` tuple** there, e.g.
`request.file == {"document": ("d.txt", b"...", "text/plain")}`.

### Optional: one full-pipeline test through a mocked transport

If you want to exercise `client.call_method` end to end, mock the HTTP backend.
Be aware that **`aioresponses` lags new `aiohttp` releases** (e.g. it breaks on
aiohttp 3.14 with `ClientResponse.__init__() missing ... 'stream_writer'`), so
pin a compatible pair, or use `respx` for an httpx client, or a local
`pytest-aiohttp` test server. Treat this as an extra, not the baseline — the
contract tests above already cover the generated surface. Example (httpx client +
`respx`):

```python
import httpx
import respx

from petstore_client.client import PetstoreClient  # built on HTTPXAsyncClient


@respx.mock
async def test_get_pet_pipeline() -> None:
    respx.get("https://api.example.com/pets/1").mock(
        return_value=httpx.Response(200, json={"id": 1, "name": "Rex", "status": "available"}),
    )
    async with PetstoreClient(base_url="https://api.example.com") as client:
        pet = await client.get_pet(id=1)
    assert pet.name == "Rex"
```

## `.gitignore`

```gitignore
__pycache__/
*.py[cod]
.venv/
dist/
build/
*.egg-info/
.pytest_cache/
.ruff_cache/
.mypy_cache/
.coverage
```

## README quickstart (async)

````markdown
```python
import asyncio

from petstore_client import PetstoreClient, PetStatus


async def main() -> None:
    async with PetstoreClient(base_url="https://api.example.com") as client:
        pet = await client.create_pet(name="Milo", status=PetStatus.pending)
        print(await client.get_pet(id=pet.id))


asyncio.run(main())
```
````
