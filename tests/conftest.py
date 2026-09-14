import socket
import threading
from unittest.mock import Mock

import pytest
from unihttp.serialize import RequestDumper, ResponseLoader


@pytest.fixture
def mock_request_dumper():
    dumper = Mock(spec=RequestDumper)
    dumper.dump.return_value = {}
    return dumper


@pytest.fixture
def mock_response_loader():
    loader = Mock(spec=ResponseLoader)
    loader.load.return_value = "mocked_response"
    return loader


@pytest.fixture
async def integration_server(aiohttp_server):
    from tests.server import make_app
    app = await make_app()
    server = await aiohttp_server(app)
    return server


@pytest.fixture
def raw_server():
    """Start a one-shot TCP server that sends back one raw HTTP response.

    Returns its base URL. Nothing validates the response, so it can be broken
    on purpose (e.g. a body shorter than Content-Length).
    """

    def start(status="200 OK", headers=(), body=b""):
        head = "".join(f"{header}\r\n" for header in headers)
        payload = f"HTTP/1.1 {status}\r\n{head}\r\n".encode() + body
        srv = socket.socket()
        srv.bind(("127.0.0.1", 0))
        srv.listen(1)

        def handle():
            conn, _ = srv.accept()
            with conn, srv:
                conn.recv(65536)
                conn.sendall(payload)

        threading.Thread(target=handle, daemon=True).start()
        return f"http://127.0.0.1:{srv.getsockname()[1]}"

    return start
