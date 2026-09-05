---
title: Stream HTTP response bodies
description: Consume unihttp downloads incrementally, reject failed responses, and close sync or async streams even when reading fails.
---

# Stream HTTP response bodies

Use `StreamMethod` to consume a response without loading the whole body into
memory. The call returns an `HTTPResponse` with status and headers available;
`.data` is a `ChunkStream` or `AsyncChunkStream` of bytes.

## Define a download method

Handle unsuccessful statuses in the method so a failed download cannot silently
look like an empty successful response:

```python
from dataclasses import dataclass

from unihttp.exceptions import HTTPStatusError
from unihttp.http.response import HTTPResponse
from unihttp.markers import Path
from unihttp.method import StreamMethod

--8<-- "examples/response_streaming.py:method"
```

`on_error` runs only for non-2xx responses. `raise_for_status()` raises
`ClientError` for `4xx` and `ServerError` for `5xx`; the final raise also rejects
other unsuccessful statuses, including an unfollowed redirect.

Bind the method with `download_file = bind_method(DownloadFile)` on your sync
`FileClient` or async `AsyncFileClient`. Import `bind_method` from
`unihttp.bind_method`; it chooses the streaming path automatically. Configure
the client as in the [quickstart](../getting-started/quickstart.md) and keep it
open until reading finishes.

## Read and close a stream

For example, calculate a download's SHA-256 checksum one chunk at a time.
These functions take an already configured, open client:

```python
from hashlib import sha256
```

=== "Sync"

    ```python
    --8<-- "examples/response_streaming.py:sync"
    ```

=== "Async"

    ```python
    --8<-- "examples/response_streaming.py:async"
    ```

The stream context manager closes the underlying response when reading finishes,
raises, or exits early. Use it even if you only need the first few chunks.
The functions return a checksum only after the whole stream has been read;
request and read failures propagate to the caller.

Keep the separate `response` variable when you also need `.headers` or
`.status_code`. For file downloads, your consumer can write each chunk to a file;
only publish the completed file after the entire read succeeds. Async consumers
should avoid blocking file I/O on the event loop.

## Choose the chunk size

Pass `__chunk_size__=8192` when calling the bound method or constructing
`DownloadFile(file_id=1, __chunk_size__=8192)`. The default is 65536 bytes.

For an explicit unbound call, use
`client.call_method_stream(DownloadFile(file_id=1))`, awaiting it on an async
client. Do not use the buffered `call_method` for a `StreamMethod`.

## Errors and parsing

There are two places a download can fail: opening the response and consuming
its body. A `try/except` must cover both, not just `client.download_file(...)`.
For the helpers above, catch around the entire `download_checksum(...)` call
(or its awaited async equivalent):

- `HTTPStatusError` covers rejected statuses, including the `ClientError` and
  `ServerError` subclasses raised by this method.
- `NetworkError` and `RequestTimeoutError` can occur while opening or reading.
- Exceptions from your own consumer also propagate; the stream context still
  closes the response.

Import these exceptions from `unihttp.exceptions`. See
[Error handling](errors.md#catch-failures-at-the-call-site) for catch patterns.

### Error bodies are not buffered

Streaming skips `validate_response`, `make_response`, and the response loader.
For any non-2xx status, the client closes the stream **before** calling
`method.on_error` and `client.handle_error`. Those hooks can inspect status and
headers, but cannot read the error body from the closed stream.

The default hooks do not raise: without the explicit handling above, a `404`
can return a stream yielding no chunks. If you need to parse an API's error
body, use a buffered method instead.

### Chunks are not messages

Chunks contain bytes, not complete JSON documents, lines, or SSE events. A chunk
boundary can even split a multi-byte character. Incremental decoding and message
framing belong in your consumer.

### Retries do not resume a download

The [buffered retry recipe](../recipes/retries.md) cannot resume an interrupted
download and should not be attached to this method. A retry strategy needs to
close the previous response and decide whether to restart or resume using a
mechanism supported by the server. Discard partial output unless your consumer
explicitly supports resuming it.
