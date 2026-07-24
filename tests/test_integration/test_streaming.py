import pytest
from unihttp.clients.aiohttp import AiohttpAsyncClient
from unihttp.method import StreamMethod


class DownloadStream(StreamMethod):
    __url__ = "/stream/{total_bytes}"
    __method__ = "GET"

    def __init__(self, total_bytes: int, chunk_size: int = 65536):
        self.total_bytes = total_bytes
        self.__chunk_size__ = chunk_size


class DownloadStreamError(StreamMethod):
    __url__ = "/stream-error/{total_bytes}"
    __method__ = "GET"

    def __init__(self, total_bytes: int):
        self.total_bytes = total_bytes


@pytest.mark.asyncio
async def test_call_method_stream_reassembles_full_body(integration_server, mock_request_dumper, mock_response_loader):
    mock_request_dumper.dump.side_effect = lambda method: {
        "path": {"total_bytes": str(method.total_bytes)},
    }

    client = AiohttpAsyncClient(
        base_url=str(integration_server.make_url("/")),
        request_dumper=mock_request_dumper,
        response_loader=mock_response_loader,
    )

    total = 0
    received_chunks = []
    # chunk_size=7000 is misaligned with the server's 4096-byte write size,
    # and total_bytes is large enough relative to chunk_size to guarantee
    # several reassembled chunks over loopback (not one single read).
    async with await client.call_method_stream(
        DownloadStream(total_bytes=50_000, chunk_size=7000)
    ) as chunks:
        async for chunk in chunks:
            total += len(chunk)
            received_chunks.append(chunk)

    assert total == 50_000
    assert len(received_chunks) > 1

    await client.close()


@pytest.mark.asyncio
async def test_call_method_stream_early_break_closes_connection(
    integration_server, mock_request_dumper, mock_response_loader
):
    mock_request_dumper.dump.side_effect = lambda method: {
        "path": {"total_bytes": str(method.total_bytes)},
    }

    client = AiohttpAsyncClient(
        base_url=str(integration_server.make_url("/")),
        request_dumper=mock_request_dumper,
        response_loader=mock_response_loader,
    )

    async with await client.call_method_stream(DownloadStream(total_bytes=1_000_000)) as chunks:
        async for chunk in chunks:
            break  # stop after the first chunk, well before the body ends

    # Prove the early `break` + `async with` exit actually released the
    # connection back to the pool immediately, rather than merely relying on
    # `client.close()` (below) to tear down everything regardless. aiohttp's
    # BaseConnector tracks in-flight connections in `_acquired`; it must be
    # empty once the streaming context manager has exited.
    assert len(client._session.connector._acquired) == 0

    await client.close()


@pytest.mark.asyncio
async def test_call_method_stream_error_status_releases_connection(
    integration_server, mock_request_dumper, mock_response_loader
):
    """`handle_error` raising on a non-ok status must not leak the connection.

    Regression test: closing the chunk stream used to rely on the backend's
    generator having been iterated at least once (a generator's own
    `finally` never runs if `.close()`/`.aclose()` is called before the
    first `next()`). `ChunkStream.close()` must release the connection
    directly, regardless of whether the caller ever got to iterate.
    """
    mock_request_dumper.dump.side_effect = lambda method: {
        "path": {"total_bytes": str(method.total_bytes)},
    }

    class _RaisingClient(AiohttpAsyncClient):
        def handle_error(self, response, method):
            raise RuntimeError(f"HTTP {response.status_code}")

    client = _RaisingClient(
        base_url=str(integration_server.make_url("/")),
        request_dumper=mock_request_dumper,
        response_loader=mock_response_loader,
    )

    with pytest.raises(RuntimeError):
        async with await client.call_method_stream(DownloadStreamError(total_bytes=1000)) as chunks:
            async for _chunk in chunks:
                pass

    assert len(client._session.connector._acquired) == 0

    await client.close()
