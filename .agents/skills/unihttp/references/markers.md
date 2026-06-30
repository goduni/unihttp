# Markers reference

Markers are `Annotated` aliases that tell the serializer where each field of a
`BaseMethod` belongs in the HTTP request. Import them from `unihttp.markers`:

```python
from unihttp.markers import Path, Query, Body, Header, Form, File
```

| Marker   | Wire location                                   | Typical type           |
| -------- | ----------------------------------------------- | ---------------------- |
| `Path`   | `{placeholder}` substituted into `__url__`      | `int`, `str`           |
| `Query`  | URL query string                                | scalars, lists         |
| `Body`   | JSON request body                               | scalars, dataclasses   |
| `Header` | HTTP request header                             | `str`                  |
| `Form`   | `application/x-www-form-urlencoded` body field  | scalars                |
| `File`   | `multipart/form-data` file part                 | `FileType`/`UploadFile`|

Each marker is `Annotated[T, <Marker>()]`, so `Path[int]` is a fully typed field.

## Rules

- **One `Path` field per `{placeholder}`** in `__url__`, names must match, or
  `__url__.format(...)` raises `KeyError`.
- **`Query` fields may have defaults** — `compact: Query[bool] = False`.
- **`Body` is for JSON.** A whole dataclass can be one `Body` field, or several
  scalar `Body` fields are merged into one JSON object.
- **`Body` is mutually exclusive with `Form`/`File`.** The aiohttp/requests
  clients raise `ValueError` if you mix them. For multipart requests, send the
  non-file fields as `Form`.
- **`Header` values are strings.**

## Files and `UploadFile`

`File` fields accept anything in `FileType`
(`bytes | BinaryIO | Path | UploadFile | tuple[...]`). Use `UploadFile` to set a
filename and content type explicitly:

```python
from dataclasses import dataclass

from unihttp.method import BaseMethod
from unihttp.markers import File, Form, Path
from unihttp.http import UploadFile


@dataclass
class UploadAvatar(BaseMethod[Avatar]):
    __url__ = "/users/{id}/avatar"
    __method__ = "POST"

    id: Path[int]
    caption: Form[str]                 # scalar field of the multipart request
    avatar: File[UploadFile]           # the file part


client.upload_avatar(
    id=1,
    caption="me",
    avatar=UploadFile(b"...png bytes...", filename="me.png", content_type="image/png"),
)
```

`UploadFile` signature: `UploadFile(file, filename=None, content_type="application/octet-stream")`
where `file` is `bytes`, an open binary file, or a `pathlib.Path` (its bytes are
read lazily via `to_tuple()`).

## Full example

```python
from dataclasses import dataclass

from unihttp.method import BaseMethod
from unihttp.markers import Path, Query, Body, Header


@dataclass
class UpdateUser(BaseMethod[User]):
    __url__ = "/users/{id}"
    __method__ = "PATCH"

    id: Path[int]                      # /users/{id}
    notify: Query[bool] = True         # ?notify=true
    name: Body[str] = ""               # {"name": ...}
    request_id: Header[str] = ""       # X-Request-Id-style header
```
