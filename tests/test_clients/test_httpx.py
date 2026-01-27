from unittest.mock import AsyncMock, Mock

import httpx
import pytest
from unihttp.clients.httpx import HTTPXAsyncClient
from unihttp.exceptions import NetworkError, RequestTimeoutError
from unihttp.http.request import HTTPRequest


@pytest.fixture
def mock_client():
    return AsyncMock(spec=httpx.AsyncClient)


@pytest.mark.asyncio
async def test_httpx_make_request(mock_request_dumper, mock_response_loader, mock_client):
    client = HTTPXAsyncClient(
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

    mock_client.request.return_value = mock_response

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
    mock_client.request.assert_called_once_with(
        method="POST",
        url="http://base/test",
        headers={"Auth": "123", "Content-Type": "application/json"},
        params={"q": "1"},
        data={},
        files=None,
        content='{"data": "abc"}'
    )

    # Verify response mapping
    assert response.status_code == 200
    assert response.data == {"key": "value"}

    assert response.data == {"key": "value"}


@pytest.mark.asyncio
async def test_httpx_upload_file(mock_request_dumper, mock_response_loader, mock_client):
    from unihttp.http import UploadFile
    
    client = HTTPXAsyncClient(
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
    mock_client.request.return_value = mock_response

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

    mock_client.request.assert_called_once_with(
        method="POST",
        url="http://base/upload",
        headers={},
        params={},
        data={},
        files=[("doc", ("test.txt", b"content", "application/octet-stream"))],
        content=None
    )
@pytest.mark.asyncio
async def test_httpx_close(mock_request_dumper, mock_response_loader, mock_client):
    client = HTTPXAsyncClient(
        base_url="http://base",
        request_dumper=mock_request_dumper,
        response_loader=mock_response_loader,
        session=mock_client
    )
    await client.close()
    mock_client.aclose.assert_called_once()


@pytest.mark.asyncio
async def test_httpx_network_error(mock_request_dumper, mock_response_loader, mock_client):
    client = HTTPXAsyncClient("http://base", mock_request_dumper, mock_response_loader, session=mock_client)
    mock_client.request.side_effect = httpx.NetworkError("Network error")

    request = HTTPRequest("GET", "url", {}, {}, {}, {}, {}, {})

    with pytest.raises(NetworkError):
        await client.make_request(request)


@pytest.mark.asyncio
async def test_httpx_timeout_error(mock_request_dumper, mock_response_loader, mock_client):
    client = HTTPXAsyncClient("http://base", mock_request_dumper, mock_response_loader, session=mock_client)
    mock_client.request.side_effect = httpx.TimeoutException("Timed out")

    request = HTTPRequest("url", "GET", {}, {}, {}, {}, {}, {})

    with pytest.raises(RequestTimeoutError):
        await client.make_request(request)


@pytest.mark.asyncio
async def test_httpx_body_and_form_error(mock_request_dumper, mock_response_loader, mock_client):
    client = HTTPXAsyncClient(
        base_url="http://base",
        request_dumper=mock_request_dumper,
        response_loader=mock_response_loader,
        session=mock_client
    )

    request = HTTPRequest(
        url="/test",
        method="POST",
        header={},
        path={},
        query={},
        body={"some": "body"},
        file=None,
        form={"some": "form"}
    )

    with pytest.raises(ValueError, match="Cannot use Body with Form or File"):
        await client.make_request(request)


@pytest.mark.asyncio
async def test_httpx_file_list_conversion(mock_request_dumper, mock_response_loader, mock_client):
    from unihttp.http import UploadFile

    client = HTTPXAsyncClient(
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
    mock_client.request.return_value = mock_response

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

    mock_client.request.assert_called_once()
    call_kwargs = mock_client.request.call_args[1]
    files = call_kwargs["files"]

    # Verify order and content
    assert files[0] == ("files", ("f1.txt", b"content1", "application/octet-stream"))
    assert files[1] == ("files", ("f2.txt", b"content2"))
    assert files[2] == ("single_upload_file", ("f3.txt", b"content3", "application/octet-stream"))
    assert files[3] == ("single_tuple", ("f4.txt", b"content4"))
