from unittest.mock import MagicMock, Mock

import httpx2
import pytest
from unihttp.clients.httpx2 import HTTPX2SyncClient, _HTTPX2ChunkStream
from unihttp.exceptions import NetworkError, RequestTimeoutError
from unihttp.http.request import HTTPRequest


@pytest.fixture
def mock_httpx2_client():
    return MagicMock(spec=httpx2.Client)


def test_httpx2_sync_make_request(mock_request_dumper, mock_response_loader, mock_httpx2_client):
    client = HTTPX2SyncClient(
        base_url="http://base",
        request_dumper=mock_request_dumper,
        response_loader=mock_response_loader,
        session=mock_httpx2_client
    )

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Type": "application/json"}
    mock_response.cookies = {}
    mock_response.json.return_value = {"key": "value"}
    mock_response.content = b'{"key": "value"}'
    mock_response.text = '{"key": "value"}'

    built_request = Mock()
    mock_httpx2_client.build_request.return_value = built_request
    mock_httpx2_client.send.return_value = mock_response

    request = HTTPRequest(
        url="/test",
        method="POST",
        header={"Auth": "123"},
        path={},
        query={"q": "1"},
        body={"data": "abc"},
        file={},
        form={}
    )

    response = client.make_request(request)

    mock_httpx2_client.build_request.assert_called_once_with(
        method="POST",
        url="http://base/test",
        headers={"Auth": "123", "Content-Type": "application/json"},
        params={"q": "1"},
        data={},
        files=None,
        content='{"data": "abc"}'
    )
    mock_httpx2_client.send.assert_called_once_with(built_request, stream=False)

    assert response.status_code == 200
    assert response.data == {"key": "value"}


def test_httpx2_sync_close(mock_request_dumper, mock_response_loader, mock_httpx2_client):
    client = HTTPX2SyncClient(
        "http://base",
        mock_request_dumper,
        mock_response_loader,
        session=mock_httpx2_client
    )
    client.close()
    mock_httpx2_client.close.assert_called_once()


def test_httpx2_sync_network_error(mock_request_dumper, mock_response_loader, mock_httpx2_client):
    client = HTTPX2SyncClient("http://base", mock_request_dumper, mock_response_loader, session=mock_httpx2_client)
    mock_httpx2_client.send.side_effect = httpx2.NetworkError("failures")

    request = HTTPRequest(
        url="/test",
        method="GET",
        header={},
        path={},
        query={},
        body={},
        file={},
        form={}
    )

    with pytest.raises(NetworkError):
        client.make_request(request)


def test_httpx2_sync_timeout_error(mock_request_dumper, mock_response_loader, mock_httpx2_client):
    client = HTTPX2SyncClient("http://base", mock_request_dumper, mock_response_loader, session=mock_httpx2_client)
    mock_httpx2_client.send.side_effect = httpx2.TimeoutException("timed out")

    request = HTTPRequest(
        url="/test",
        method="GET",
        header={},
        path={},
        query={},
        body={},
        file={},
        form={}
    )

    with pytest.raises(RequestTimeoutError):
        client.make_request(request)




def test_httpx2_sync_file_list_conversion(mock_request_dumper, mock_response_loader, mock_httpx2_client):
    from unihttp.http import UploadFile

    client = HTTPX2SyncClient(
        base_url="http://base",
        request_dumper=mock_request_dumper,
        response_loader=mock_response_loader,
        session=mock_httpx2_client
    )

    # Mock response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = b'{}'
    mock_response.text = '{}'
    mock_httpx2_client.send.return_value = mock_response

    request = HTTPRequest(
        url="/upload",
        method="POST",
        header={},
        path={},
        query={},
        body=None,
        file={
            "files": [
                UploadFile(b"content1", filename="f1.txt"),
                ("f2.txt", b"content2")
            ],
            "single_upload_file": UploadFile(b"content3", filename="f3.txt"),
            "single_tuple": ("f4.txt", b"content4")
        },
        form={}
    )

    client.make_request(request)

    mock_httpx2_client.build_request.assert_called_once()
    call_kwargs = mock_httpx2_client.build_request.call_args[1]
    files = call_kwargs["files"]

    # Verify order and content
    assert files[0] == ("files", ("f1.txt", b"content1", "application/octet-stream"))
    assert files[1] == ("files", ("f2.txt", b"content2"))
    assert files[2] == ("single_upload_file", ("f3.txt", b"content3", "application/octet-stream"))
    assert files[3] == ("single_tuple", ("f4.txt", b"content4"))


def test_httpx2_sync_raw_body_bytes(mock_request_dumper, mock_response_loader, mock_httpx2_client):
    client = HTTPX2SyncClient("http://base", mock_request_dumper, mock_response_loader, session=mock_httpx2_client)

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {}
    mock_response.cookies = {}
    mock_response.content = b""
    mock_httpx2_client.send.return_value = mock_response

    request = HTTPRequest(
        url="/raw", method="POST", header={}, path={}, query={},
        body={}, file={}, form={}, raw=b"raw-bytes"
    )

    client.make_request(request)

    call_kwargs = mock_httpx2_client.build_request.call_args.kwargs
    assert call_kwargs["content"] == b"raw-bytes"


def test_httpx2_sync_stream_make_request(mock_request_dumper, mock_response_loader):
    session = MagicMock(spec=httpx2.Client)
    built_request = MagicMock()
    session.build_request.return_value = built_request

    response = MagicMock()
    response.status_code = 200
    response.headers = {}
    response.cookies = {}
    response.iter_bytes.return_value = iter([b"a", b"b"])
    session.send.return_value = response

    client = HTTPX2SyncClient("http://base", mock_request_dumper, mock_response_loader, session=session)

    request = HTTPRequest(
        url="/download", method="GET", header={}, path={}, query={},
        body={}, file={}, form={}
    )

    result = client.stream_make_request(request, chunk_size=1234)

    assert result.status_code == 200
    session.send.assert_called_once_with(built_request, stream=True)

    chunks = list(result.data)
    assert chunks == [b"a", b"b"]
    response.iter_bytes.assert_called_once_with(1234)
    response.close.assert_called_once()


def test_httpx2_sync_chunk_stream_mid_stream_error_translated():

    def gen():
        yield b"a"
        raise httpx2.ConnectError("connection lost")

    response = Mock()
    response.iter_bytes.return_value = gen()

    stream = _HTTPX2ChunkStream(response, chunk_size=999)
    assert next(stream) == b"a"
    with pytest.raises(NetworkError):
        next(stream)


def test_httpx2_sync_chunk_stream_mid_stream_timeout_translated():

    def gen():
        yield b"a"
        raise httpx2.ReadTimeout("timed out")

    response = Mock()
    response.iter_bytes.return_value = gen()

    stream = _HTTPX2ChunkStream(response, chunk_size=999)
    assert next(stream) == b"a"
    with pytest.raises(RequestTimeoutError):
        next(stream)
