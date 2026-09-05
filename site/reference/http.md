---
title: HTTP types
description: Request, response, upload, and stream types used by unihttp hooks and middleware.
---

# HTTP types

`HTTPRequest.header` is singular; `HTTPResponse.headers` is plural. Buffered `call_method` returns the loaded body, whereas streaming calls expose `HTTPResponse` directly. These types are available to middleware and response hooks. See [response metadata](../guides/responses.md) for a wrapper example and [streaming](../guides/streaming.md) for cleanup requirements.

::: unihttp.http.request.HTTPRequest

::: unihttp.http.response.HTTPResponse

::: unihttp.http.files.UploadFile

::: unihttp.http.stream.ChunkStream

::: unihttp.http.stream.AsyncChunkStream
