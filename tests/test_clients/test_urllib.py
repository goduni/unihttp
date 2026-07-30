import io
import socket
import urllib.error
import urllib.request
from email.message import Message
from unittest.mock import MagicMock

import pytest
from unihttp.clients.urllib import UrllibSyncClient, _UrllibChunkStream
from unihttp.exceptions import NetworkError, RequestTimeoutError
from unihttp.http import UploadFile
from unihttp.http.request import HTTPRequest


class FakeHeaders(Message):
    """A minimal email.message.Message-based headers container."""

    def __init__(self, headers=None, cookies=None):
        super().__init__()
        for key, value in (headers or {}).items():
            self[key] = value
        for cookie in cookies or []:
            self["Set-Cookie"] = cookie


class FakeResponse:
    def __init__(self, status=200, headers=None, body=b"", cookies=None):
        self.status = status
        self.headers = FakeHeaders(headers, cookies)
        self._body = body

    def read(self):
        return self._body


@pytest.fixture
def mock_opener():
    return MagicMock(spec=urllib.request.OpenerDirector)


def make_client(dumper, loader, opener):
    return UrllibSyncClient(
        base_url="http://base",
        request_dumper=dumper,
        response_loader=loader,
        opener=opener,
    )


def test_urllib_make_request(mock_request_dumper, mock_response_loader, mock_opener):
    client = make_client(mock_request_dumper, mock_response_loader, mock_opener)

    mock_opener.open.return_value = FakeResponse(
        status=200,
        headers={"Content-Type": "application/json"},
        body=b'{"key": "value"}',
        cookies=["session=abc; Path=/"],
    )

    request = HTTPRequest(
        url="/test",
        method="POST",
        header={"Auth": "123"},
        path={},
        query={"q": "1"},
        body={"data": "abc"},
        file={},
        form={},
    )

    response = client.make_request(request)

    sent_req = mock_opener.open.call_args[0][0]
    assert sent_req.get_full_url() == "http://base/test?q=1"
    assert sent_req.get_method() == "POST"
    assert sent_req.data == b'{"data": "abc"}'
    assert sent_req.get_header("Content-type") == "application/json"
    assert sent_req.get_header("Auth") == "123"

    assert response.status_code == 200
    assert response.data == {"key": "value"}
    assert response.headers["Content-Type"] == "application/json"
    assert response.cookies == {"session": "abc"}


def test_urllib_context_manager(mock_request_dumper, mock_response_loader, mock_opener):
    with make_client(mock_request_dumper, mock_response_loader, mock_opener) as client:
        assert isinstance(client, UrllibSyncClient)


def test_urllib_network_error(mock_request_dumper, mock_response_loader, mock_opener):
    client = make_client(mock_request_dumper, mock_response_loader, mock_opener)
    mock_opener.open.side_effect = urllib.error.URLError("Connection refused")

    request = HTTPRequest("/url", "GET", {}, {}, {}, {}, {}, {})

    with pytest.raises(NetworkError):
        client.make_request(request)


def test_urllib_timeout_error_from_urlerror(
    mock_request_dumper, mock_response_loader, mock_opener
):
    client = make_client(mock_request_dumper, mock_response_loader, mock_opener)
    mock_opener.open.side_effect = urllib.error.URLError(socket.timeout("timed out"))

    request = HTTPRequest("/url", "GET", {}, {}, {}, {}, {}, {})

    with pytest.raises(RequestTimeoutError):
        client.make_request(request)


def test_urllib_timeout_error_direct(
    mock_request_dumper, mock_response_loader, mock_opener
):
    client = make_client(mock_request_dumper, mock_response_loader, mock_opener)
    mock_opener.open.side_effect = TimeoutError("timed out")

    request = HTTPRequest("/url", "GET", {}, {}, {}, {}, {}, {})

    with pytest.raises(RequestTimeoutError):
        client.make_request(request)


def test_urllib_mid_body_connection_error_translated(
    mock_request_dumper, mock_response_loader, mock_opener
):
    client = make_client(mock_request_dumper, mock_response_loader, mock_opener)

    raw = MagicMock()
    raw.status = 200
    raw.headers.items.return_value = []
    raw.read.side_effect = ConnectionResetError("reset by peer")
    mock_opener.open.return_value = raw

    request = HTTPRequest("/url", "GET", {}, {}, {}, {}, {}, {})

    with pytest.raises(NetworkError):
        client.make_request(request)

    raw.close.assert_called_once()


def test_urllib_mid_body_timeout_error_translated(
    mock_request_dumper, mock_response_loader, mock_opener
):
    client = make_client(mock_request_dumper, mock_response_loader, mock_opener)

    raw = MagicMock()
    raw.status = 200
    raw.headers.items.return_value = []
    raw.read.side_effect = TimeoutError("timed out")
    mock_opener.open.return_value = raw

    request = HTTPRequest("/url", "GET", {}, {}, {}, {}, {}, {})

    with pytest.raises(RequestTimeoutError):
        client.make_request(request)

    raw.close.assert_called_once()


def test_urllib_http_error_is_response(
    mock_request_dumper, mock_response_loader, mock_opener
):
    client = make_client(mock_request_dumper, mock_response_loader, mock_opener)

    http_error = urllib.error.HTTPError(
        url="http://base/test",
        code=404,
        msg="Not Found",
        hdrs=FakeHeaders({"Content-Type": "application/json"}),
        fp=io.BytesIO(b'{"error": "not found"}'),
    )
    mock_opener.open.side_effect = http_error

    request = HTTPRequest("/test", "GET", {}, {}, {}, {}, {}, {})

    response = client.make_request(request)

    assert response.status_code == 404
    assert response.data == {"error": "not found"}
    assert not response.ok
    assert response.is_client_error


def test_urllib_form_only(mock_request_dumper, mock_response_loader, mock_opener):
    client = make_client(mock_request_dumper, mock_response_loader, mock_opener)
    mock_opener.open.return_value = FakeResponse(status=200, body=b"{}")

    request = HTTPRequest(
        url="/form",
        method="POST",
        header={},
        path={},
        query={},
        body=None,
        file=None,
        form={"key": "val"},
    )

    client.make_request(request)

    sent_req = mock_opener.open.call_args[0][0]
    assert sent_req.data == b"key=val"
    assert sent_req.get_header("Content-type") == "application/x-www-form-urlencoded"


def test_urllib_multipart_with_file(
    mock_request_dumper, mock_response_loader, mock_opener
):
    client = make_client(mock_request_dumper, mock_response_loader, mock_opener)
    mock_opener.open.return_value = FakeResponse(status=200, body=b"{}")

    request = HTTPRequest(
        url="/upload",
        method="POST",
        header={},
        path={},
        query={},
        body=None,
        file={"doc": UploadFile(b"file-content", filename="a.txt")},
        form={"caption": "hello"},
    )

    client.make_request(request)

    sent_req = mock_opener.open.call_args[0][0]
    content_type = sent_req.get_header("Content-type")
    assert content_type.startswith("multipart/form-data; boundary=")
    assert b'name="caption"' in sent_req.data
    assert b"hello" in sent_req.data
    assert b'name="doc"; filename="a.txt"' in sent_req.data
    assert b"file-content" in sent_req.data


def test_urllib_non_json_body_falls_back_to_bytes(
    mock_request_dumper, mock_response_loader, mock_opener
):
    client = make_client(mock_request_dumper, mock_response_loader, mock_opener)
    mock_opener.open.return_value = FakeResponse(status=200, body=b"plain text")

    request = HTTPRequest("/text", "GET", {}, {}, {}, None, {}, None)

    response = client.make_request(request)

    assert response.data == b"plain text"


def test_urllib_file_formats(mock_request_dumper, mock_response_loader, mock_opener):
    client = make_client(mock_request_dumper, mock_response_loader, mock_opener)
    mock_opener.open.return_value = FakeResponse(status=200, body=b"{}")

    request = HTTPRequest(
        url="/upload",
        method="POST",
        header={},
        path={},
        query={},
        body=None,
        file={
            "raw": b"bytes-content",
            "stream": io.BytesIO(b"stream-content"),
            "pair": ("pair.txt", b"pair-content"),
            "triple": ("triple.bin", b"triple-content", "application/x-thing"),
            "many": [b"one", ("two.txt", b"two")],
            "text": ("note.txt", "string-content"),
        },
        form=None,
    )

    client.make_request(request)

    data = mock_opener.open.call_args[0][0].data
    assert b'name="raw"' in data
    assert b"bytes-content" in data
    assert b"stream-content" in data
    assert b'filename="pair.txt"' in data
    assert b'filename="triple.bin"' in data
    assert b"application/x-thing" in data
    assert b"one" in data
    assert b'filename="two.txt"' in data
    assert b"string-content" in data


def test_urllib_no_body_get(mock_request_dumper, mock_response_loader, mock_opener):
    client = make_client(mock_request_dumper, mock_response_loader, mock_opener)
    mock_opener.open.return_value = FakeResponse(status=204, body=b"")

    request = HTTPRequest("/ping", "GET", {}, {}, {}, None, {}, None)

    response = client.make_request(request)

    sent_req = mock_opener.open.call_args[0][0]
    assert sent_req.data is None
    assert sent_req.get_method() == "GET"
    assert response.status_code == 204
    assert response.data is None


def test_urllib_raw_body(mock_request_dumper, mock_response_loader):
    fake_response = MagicMock()
    fake_response.status = 200
    fake_response.headers.items.return_value = []
    fake_response.headers.get_all.return_value = []
    fake_response.read.return_value = b"{}"

    opener = MagicMock()
    opener.open.return_value = fake_response

    client = UrllibSyncClient("http://base", mock_request_dumper, mock_response_loader, opener=opener)

    request = HTTPRequest(
        url="/raw", method="POST", header={}, path={}, query={},
        body={}, file={}, form={}, raw=b"raw-payload"
    )
    client.make_request(request)

    sent_request = opener.open.call_args.args[0]
    assert sent_request.data == b"raw-payload"


def test_urllib_stream_make_request(mock_request_dumper, mock_response_loader):
    fake_response = MagicMock()
    fake_response.status = 200
    fake_response.headers.items.return_value = []
    fake_response.headers.get_all.return_value = []
    fake_response.read.side_effect = [b"a", b"b", b""]

    opener = MagicMock()
    opener.open.return_value = fake_response

    client = UrllibSyncClient("http://base", mock_request_dumper, mock_response_loader, opener=opener)

    request = HTTPRequest(
        url="/download", method="GET", header={}, path={}, query={},
        body={}, file={}, form={}
    )
    result = client.stream_make_request(request, chunk_size=5)

    assert result.status_code == 200
    chunks = list(result.data)
    assert chunks == [b"a", b"b"]
    fake_response.read.assert_any_call(5)
    fake_response.close.assert_called_once()


def test_urllib_chunk_stream_closes_without_ever_reading():
    raw = MagicMock()
    raw.read.side_effect = [b"a", b"b", b""]

    stream = _UrllibChunkStream(raw, chunk_size=5)
    stream.close()

    raw.read.assert_not_called()
    raw.close.assert_called_once()

    # Idempotent: closing again, or iterating after close, must not reopen
    # or re-close the connection.
    stream.close()
    assert list(stream) == []
    raw.close.assert_called_once()


def test_urllib_chunk_stream_early_break_closes_once():
    raw = MagicMock()
    raw.read.side_effect = [b"a", b"b", b""]

    stream = _UrllibChunkStream(raw, chunk_size=5)
    for chunk in stream:
        assert chunk == b"a"
        break
    stream.close()

    raw.read.assert_called_once_with(5)
    raw.close.assert_called_once()


def test_urllib_chunk_stream_mid_stream_connection_error_translated():
    raw = MagicMock()
    raw.read.side_effect = [b"a", ConnectionResetError("connection reset")]

    stream = _UrllibChunkStream(raw, chunk_size=5)
    assert next(stream) == b"a"
    with pytest.raises(NetworkError):
        next(stream)


def test_urllib_chunk_stream_mid_stream_timeout_translated():
    raw = MagicMock()
    raw.read.side_effect = [b"a", TimeoutError("timed out")]

    stream = _UrllibChunkStream(raw, chunk_size=5)
    assert next(stream) == b"a"
    with pytest.raises(RequestTimeoutError):
        next(stream)
