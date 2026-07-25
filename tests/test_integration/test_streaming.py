import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from unihttp.clients.aiohttp import AiohttpAsyncClient
from unihttp.clients.httpx import HTTPXAsyncClient, HTTPXSyncClient
from unihttp.clients.httpx2 import HTTPX2AsyncClient, HTTPX2SyncClient
from unihttp.clients.niquests import NiquestsAsyncClient, NiquestsSyncClient
from unihttp.clients.requests import RequestsSyncClient
from unihttp.clients.urllib import UrllibSyncClient
from unihttp.clients.zapros import ZaprosAsyncClient, ZaprosSyncClient
from unihttp.method import StreamMethod

TOTAL_BYTES = 50_000
CHUNK_SIZE = 7000


class DownloadStream(StreamMethod):
    __url__ = "/stream/{total_bytes}"
    __method__ = "GET"

    def __init__(self, total_bytes: int, chunk_size: int = 65536):
        self.total_bytes = total_bytes
        self.__chunk_size__ = chunk_size


ASYNC_CLIENTS = [
    ("aiohttp", AiohttpAsyncClient),
    ("httpx", HTTPXAsyncClient),
    ("httpx2", HTTPX2AsyncClient),
    ("niquests", NiquestsAsyncClient),
    ("zapros", ZaprosAsyncClient),
]

SYNC_CLIENTS = [
    ("httpx", HTTPXSyncClient),
    ("httpx2", HTTPX2SyncClient),
    ("requests", RequestsSyncClient),
    ("niquests", NiquestsSyncClient),
    ("urllib", UrllibSyncClient),
    ("zapros", ZaprosSyncClient),
]


def make_client(client_cls, base_url, dumper, loader):
    dumper.dump.side_effect = lambda method: {
        "path": {"total_bytes": str(method.total_bytes)},
    }
    return client_cls(base_url=base_url, request_dumper=dumper, response_loader=loader)


class _StreamHandler(BaseHTTPRequestHandler):
    """Mirrors tests/server.py's /stream/{total_bytes}: writes `total_bytes`
    in 4096-byte pieces, misaligned with CHUNK_SIZE on purpose."""

    def do_GET(self):
        match = re.fullmatch(r"/stream/(\d+)", self.path)
        if not match:
            self.send_error(404)
            return

        self.send_response(200)
        self.end_headers()

        total = int(match.group(1))
        written = 0
        while written < total:
            piece = min(4096, total - written)
            self.wfile.write(b"x" * piece)
            written += piece

    def log_message(self, format, *args):
        pass


@pytest.fixture
def threaded_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _StreamHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    yield f"http://127.0.0.1:{server.server_port}/"

    server.shutdown()
    thread.join(timeout=5)
    server.server_close()


@pytest.mark.asyncio
@pytest.mark.parametrize("name,client_cls", ASYNC_CLIENTS, ids=[name for name, _ in ASYNC_CLIENTS])
async def test_async_stream_reassembles_full_body(name, client_cls, threaded_server, mock_request_dumper, mock_response_loader):
    client = make_client(client_cls, threaded_server, mock_request_dumper, mock_response_loader)

    total = 0
    received_chunks = []
    async with await client.call_method_stream(DownloadStream(TOTAL_BYTES, CHUNK_SIZE)) as chunks:
        async for chunk in chunks:
            total += len(chunk)
            received_chunks.append(chunk)

    assert total == TOTAL_BYTES
    assert len(received_chunks) > 1

    await client.close()


@pytest.mark.parametrize("name,client_cls", SYNC_CLIENTS, ids=[name for name, _ in SYNC_CLIENTS])
def test_sync_stream_reassembles_full_body(name, client_cls, threaded_server, mock_request_dumper, mock_response_loader):
    client = make_client(client_cls, threaded_server, mock_request_dumper, mock_response_loader)

    total = 0
    received_chunks = []
    with client.call_method_stream(DownloadStream(TOTAL_BYTES, CHUNK_SIZE)) as chunks:
        for chunk in chunks:
            total += len(chunk)
            received_chunks.append(chunk)

    assert total == TOTAL_BYTES
    assert len(received_chunks) > 1

    client.close()
