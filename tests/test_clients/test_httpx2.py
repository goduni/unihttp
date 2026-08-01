from unittest.mock import AsyncMock, Mock

import httpx2
import pytest
from unihttp.clients.httpx2 import HTTPX2AsyncClient, _HTTPX2AsyncChunkStream
from unihttp.exceptions import NetworkError, RequestTimeoutError
from unihttp.http.request import HTTPRequest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_client():
    return AsyncMock(spec=httpx2.AsyncClient)


@pytest.mark.asyncio
async def test_httpx2_make_request(mock_request_dumper, mock_response_loader, mock_client):
    client = HTTPX2AsyncClient(
        base_url="http://base",
        request_dumper=mock_request_dumper,
        response_loader=mock_response_loader,
        session=mock_client
    )

    # Mock response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Type": "application/json"}
    mock_response.cookies = {}
    mock_response.json.return_value = {"key": "value"}
    mock_response.content = b'{"key": "value"}'
    mock_response.text = '{"key": "value"}'

    built_request = Mock()
    mock_client.build_request.return_value = built_request
    mock_client.send.return_value = mock_response

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

    response = await client.make_request(request)

    # Verify call arguments
    mock_client.build_request.assert_called_once_with(
        method="POST",
        url="http://base/test",
        headers={"Auth": "123", "Content-Type": "application/json"},
        params={"q": "1"},
        data={},
        files=None,
        content='{"data": "abc"}'
    )
    mock_client.send.assert_called_once_with(built_request, stream=False)

    # Verify response mapping
    assert response.status_code == 200
    assert response.data == {"key": "value"}

    assert response.data == {"key": "value"}


@pytest.mark.asyncio
async def test_httpx2_upload_file(mock_request_dumper, mock_response_loader, mock_client):
    from unihttp.http import UploadFile

    client = HTTPX2AsyncClient(
        base_url="http://base",
        request_dumper=mock_request_dumper,
        response_loader=mock_response_loader,
        session=mock_client
    )

    # Mock response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = b'{"status": "ok"}'
    mock_response.text = '{"status": "ok"}'
    mock_client.send.return_value = mock_response

    request = HTTPRequest(
        url="/upload",
        method="POST",
        header={},
        path={},
        query={},
        body=None,
        file={"doc": UploadFile(b"content", filename="test.txt")},
        form={}
    )

    await client.make_request(request)

    mock_client.build_request.assert_called_once_with(
        method="POST",
        url="http://base/upload",
        headers={},
        params={},
        data={},
        files=[("doc", ("test.txt", b"content", "application/octet-stream"))],
        content=None
    )


@pytest.mark.asyncio
async def test_httpx2_close(mock_request_dumper, mock_response_loader, mock_client):
    client = HTTPX2AsyncClient(
        base_url="http://base",
        request_dumper=mock_request_dumper,
        response_loader=mock_response_loader,
        session=mock_client
    )
    await client.close()
    mock_client.aclose.assert_called_once()


@pytest.mark.asyncio
async def test_httpx2_network_error(mock_request_dumper, mock_response_loader, mock_client):
    client = HTTPX2AsyncClient("http://base", mock_request_dumper, mock_response_loader, session=mock_client)
    mock_client.send.side_effect = httpx2.NetworkError("Network error")

    request = HTTPRequest("GET", "url", {}, {}, {}, {}, {}, {})

    with pytest.raises(NetworkError):
        await client.make_request(request)


@pytest.mark.asyncio
async def test_httpx2_timeout_error(mock_request_dumper, mock_response_loader, mock_client):
    client = HTTPX2AsyncClient("http://base", mock_request_dumper, mock_response_loader, session=mock_client)
    mock_client.send.side_effect = httpx2.TimeoutException("Timed out")

    request = HTTPRequest("url", "GET", {}, {}, {}, {}, {}, {})

    with pytest.raises(RequestTimeoutError):
        await client.make_request(request)


@pytest.mark.asyncio
async def test_httpx2_file_list_conversion(mock_request_dumper, mock_response_loader, mock_client):
    from unihttp.http import UploadFile

    client = HTTPX2AsyncClient(
        base_url="http://base",
        request_dumper=mock_request_dumper,
        response_loader=mock_response_loader,
        session=mock_client
    )

    # Mock response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = b'{}'
    mock_response.text = '{}'
    mock_client.send.return_value = mock_response

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

    await client.make_request(request)

    mock_client.build_request.assert_called_once()
    call_kwargs = mock_client.build_request.call_args[1]
    files = call_kwargs["files"]

    # Verify order and content
    assert files[0] == ("files", ("f1.txt", b"content1", "application/octet-stream"))
    assert files[1] == ("files", ("f2.txt", b"content2"))
    assert files[2] == ("single_upload_file", ("f3.txt", b"content3", "application/octet-stream"))
    assert files[3] == ("single_tuple", ("f4.txt", b"content4"))


@pytest.mark.asyncio
async def test_httpx2_async_raw_body_bytes(mock_request_dumper, mock_response_loader, mock_client):
    client = HTTPX2AsyncClient("http://base", mock_request_dumper, mock_response_loader, session=mock_client)

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {}
    mock_response.cookies = {}
    mock_response.content = b""
    mock_client.send.return_value = mock_response

    request = HTTPRequest(
        url="/raw", method="POST", header={}, path={}, query={},
        body={}, file={}, form={}, raw="raw-string"
    )

    await client.make_request(request)

    call_kwargs = mock_client.build_request.call_args.kwargs
    assert call_kwargs["content"] == "raw-string"


@pytest.mark.asyncio
async def test_httpx2_async_stream_make_request(mock_request_dumper, mock_response_loader):

    session = MagicMock(spec=httpx2.AsyncClient)
    built_request = MagicMock()
    session.build_request.return_value = built_request

    async def aiter_bytes(chunk_size):
        for chunk in (b"a", b"b"):
            yield chunk

    response = MagicMock()
    response.status_code = 200
    response.headers = {}
    response.cookies = {}
    response.aiter_bytes = aiter_bytes
    response.aclose = AsyncMock()
    session.send = AsyncMock(return_value=response)

    client = HTTPX2AsyncClient("http://base", mock_request_dumper, mock_response_loader, session=session)

    request = HTTPRequest(
        url="/download", method="GET", header={}, path={}, query={},
        body={}, file={}, form={}
    )

    result = await client.stream_make_request(request, chunk_size=1234)

    assert result.status_code == 200
    session.send.assert_called_once_with(built_request, stream=True)

    chunks = [chunk async for chunk in result.data]
    assert chunks == [b"a", b"b"]
    response.aclose.assert_called_once()


@pytest.mark.asyncio
async def test_httpx2_async_chunk_stream_mid_stream_error_translated():
    async def aiter_bytes(chunk_size):
        yield b"a"
        raise httpx2.ConnectError("connection lost")

    response = Mock()
    response.aiter_bytes = aiter_bytes

    stream = _HTTPX2AsyncChunkStream(response, chunk_size=999)
    assert await anext(stream) == b"a"
    with pytest.raises(NetworkError):
        await anext(stream)


@pytest.mark.asyncio
async def test_httpx2_async_chunk_stream_mid_stream_timeout_translated():

    async def aiter_bytes(chunk_size):
        yield b"a"
        raise httpx2.ReadTimeout("timed out")

    response = Mock()
    response.aiter_bytes = aiter_bytes

    stream = _HTTPX2AsyncChunkStream(response, chunk_size=999)
    assert await anext(stream) == b"a"
    with pytest.raises(RequestTimeoutError):
        await anext(stream)
