# Streaming responses

Use `StreamMethod` for downloads or other bodies that must be read incrementally.
Use `BaseMethod[T]` for buffered responses loaded into a model. Streaming skips
`validate_response`, `make_response`, and the response loader, although the
client constructor still requires its serializer arguments.

## Define and bind a method

```python
from dataclasses import dataclass

from unihttp.exceptions import HTTPStatusError
from unihttp.http.response import HTTPResponse
from unihttp.markers import Path
from unihttp.method import StreamMethod


@dataclass
class DownloadFile(StreamMethod):
    __url__ = "/files/{file_id}"
    __method__ = "GET"

    file_id: Path[int]

    def on_error(self, response: HTTPResponse) -> None:
        response.raise_for_status()
        raise HTTPStatusError("Download requires a successful response", response)
```

Inside the client, use `download_file = bind_method(DownloadFile)` with
`bind_method` imported from `unihttp.bind_method`. It chooses
`call_method_stream` automatically. For explicit calls, pass the method to
`call_method_stream`, not `call_method`.

The result is `HTTPResponse[ChunkStream]` for sync clients and, after awaiting,
`HTTPResponse[AsyncChunkStream]` for async clients. Status and headers are
available before the body is read. Pass `__chunk_size__=8192` when constructing
the method or calling its binding; the default is 65536 bytes.

## Consume and close

Keep the client open until reading finishes. For an already configured client:

```python
response = client.download_file(file_id=1)
with response.data as stream:
    for chunk in stream:
        consume(chunk)
```

Async equivalent:

```python
response = await client.download_file(file_id=1)
async with response.data as stream:
    async for chunk in stream:
        await consume(chunk)
```

The stream context closes the response on success, an exception, or an early
break. If managing it manually, call `close()` or await `aclose()` in `finally`.
Chunks are arbitrary byte segments; use incremental decoding and framing for
text, JSON lines, or SSE. Avoid blocking file I/O in an async consumer.

## Errors and retries

- Cover both the opening call and iteration with any `try/except`: network
  failures and timeouts can happen during either stage. Backend error mappings
  also apply while reading chunks.
- For a non-2xx response, unihttp closes the stream before calling `on_error`
  and `handle_error`. Hooks can inspect status and headers, but cannot read the
  closed body. The example rejects unsuccessful statuses, including unfollowed
  redirects; default hooks would allow a closed, empty stream to be returned.
- Use a buffered method if the API's error body must be deserialized.
- The ordinary retry middleware wraps opening the response, not later stream
  consumption. It cannot resume downloads. A download retry policy must close
  the previous response and explicitly restart or use server-supported resume;
  discard partial output unless the consumer supports resuming it.
