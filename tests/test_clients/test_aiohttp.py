from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest
from unihttp.clients.aiohttp import AiohttpAsyncClient
from unihttp.exceptions import NetworkError, RequestTimeoutError
from unihttp.http.request import HTTPRequest


@pytest.fixture
def mock_session():
    return MagicMock(spec=aiohttp.ClientSession)


@pytest.mark.asyncio
async def test_aiohttp_make_request(mock_request_dumper, mock_response_loader, mock_session):
    client = AiohttpAsyncClient(
        base_url="http://base",
        request_dumper=mock_request_dumper,
        response_loader=mock_response_loader,
        session=mock_session
    )

    # Mock response
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.headers = {"Content-Type": "application/json"}
    mock_response.cookies = {}
    mock_response.json.return_value = {"key": "value"}
    mock_response.read.return_value = b'{"key": "value"}'
    mock_response.__aenter__.return_value = mock_response
    mock_response.__aexit__.return_value = None

    mock_session.request.return_value = mock_response

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
    mock_session.request.assert_called_once_with(
        method="POST",
        url="http://base/test",
        headers={"Auth": "123", "Content-Type": "application/json"},
        params={"q": "1"},
        data='{"data": "abc"}',  # AiohttpClient passes body as data
    )

    # Verify response mapping
    assert response.status_code == 200
    assert response.data == {"key": "value"}
    assert response.headers == {"Content-Type": "application/json"}


@pytest.mark.asyncio
async def test_aiohttp_close(mock_request_dumper, mock_response_loader, mock_session):
    # Mock close to be awaitable
    mock_session.close = AsyncMock()

    client = AiohttpAsyncClient(
        base_url="http://base",
        request_dumper=mock_request_dumper,
        response_loader=mock_response_loader,
        session=mock_session
    )
    await client.close()
    mock_session.close.assert_called_once()


@pytest.mark.asyncio
async def test_aiohttp_network_error(mock_request_dumper, mock_response_loader, mock_session):
    client = AiohttpAsyncClient("http://base", mock_request_dumper, mock_response_loader, session=mock_session)
    mock_session.request.side_effect = aiohttp.ClientConnectionError("Connection Refused")

    request = HTTPRequest("url", "GET", {}, {}, {}, {}, {}, {})

    with pytest.raises(NetworkError):
        await client.make_request(request)


@pytest.mark.asyncio
async def test_aiohttp_timeout_error(mock_request_dumper, mock_response_loader, mock_session):
    client = AiohttpAsyncClient("http://base", mock_request_dumper, mock_response_loader, session=mock_session)
    mock_session.request.side_effect = TimeoutError()

    request = HTTPRequest("url", "GET", {}, {}, {}, {}, {}, {})

    with pytest.raises(RequestTimeoutError):
        await client.make_request(request)


@pytest.mark.asyncio
async def test_aiohttp_upload_file(mock_request_dumper, mock_response_loader, mock_session):
    from unittest.mock import patch

    with patch("unihttp.clients.aiohttp.FormData") as MockFormData:
        mock_form = MockFormData.return_value

        client = AiohttpAsyncClient("http://base", mock_request_dumper, mock_response_loader, session=mock_session)

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {}
        mock_response.cookies = {}
        mock_response.json.return_value = {}
        mock_response.read.return_value = b"{}"
        mock_response.__aenter__.return_value = mock_response
        mock_response.__aexit__.return_value = None
        mock_session.request.return_value = mock_response

        request = HTTPRequest(
            url="/upload",
            method="POST",
            header={},
            path={},
            query={},
            body={},
            file={"file1": ("f1.txt", b"content"), "file2": b"raw"},
            form={"key": "val"}
        )

        await client.make_request(request)

        # Verify FormData usage
        assert mock_form.add_field.call_count == 3  # key, file1, file2

        # Check calls
        calls = mock_form.add_field.call_args_list
        # Body field
        assert any(c[0][0] == "key" and c[0][1] == "val" for c in calls)
        # File fields
        assert any(c[0][0] == "file1" and c[0][1] == b"content" and c[1].get("filename") == "f1.txt" for c in calls)
        assert any(c[0][0] == "file2" and c[0][1] == b"raw" for c in calls)

        # Verify request called with data=form
        mock_session.request.assert_called_once()
        assert mock_session.request.call_args[1]["data"] == mock_form


@pytest.mark.asyncio
async def test_aiohttp_upload_complex(mock_request_dumper, mock_response_loader, mock_session):
    from unittest.mock import patch
    with patch("unihttp.clients.aiohttp.FormData") as MockFormData:
        mock_form = MockFormData.return_value
        client = AiohttpAsyncClient("http://base", mock_request_dumper, mock_response_loader, session=mock_session)

        # Setup mock response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {}
        mock_response.cookies = {}
        mock_response.json.return_value = {}
        mock_response.read.return_value = b"{}"
        mock_response.__aenter__.return_value = mock_response
        mock_response.__aexit__.return_value = None
        mock_session.request.return_value = mock_response

        request = HTTPRequest("/upload", "POST", {}, {}, {}, {},
                              file={"f1": ("f.txt", b"data", "text/plain")},
                              form={}
                              )
        await client.make_request(request)

        calls = mock_form.add_field.call_args_list
        assert any(c[0][0] == "f1" and c[0][1] == b"data" and c[1].get("content_type") == "text/plain" for c in calls)


@pytest.mark.asyncio
async def test_aiohttp_body_and_form_error(mock_request_dumper, mock_response_loader, mock_session):
    client = AiohttpAsyncClient(
        base_url="http://base",
        request_dumper=mock_request_dumper,
        response_loader=mock_response_loader,
        session=mock_session
    )

    request = HTTPRequest(
        url="/test",
        method="POST",
        header={},
        path={},
        query={},
        body={"some": "body"},
        file={},
        form={"some": "form"}
    )

    with pytest.raises(ValueError, match="Cannot use Body with Form or File"):
        await client.make_request(request)


@pytest.mark.asyncio
async def test_aiohttp_upload_file_object(mock_request_dumper, mock_response_loader, mock_session):
    from unittest.mock import patch
    from unihttp.http import UploadFile

    with patch("unihttp.clients.aiohttp.FormData") as MockFormData:
        mock_form = MockFormData.return_value
        client = AiohttpAsyncClient("http://base", mock_request_dumper, mock_response_loader, session=mock_session)

        # Setup mock response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {}
        mock_response.cookies = {}
        mock_response.json.return_value = {}
        mock_response.read.return_value = b"{}"
        mock_response.__aenter__.return_value = mock_response
        mock_response.__aexit__.return_value = None
        mock_session.request.return_value = mock_response

        request = HTTPRequest(
            url="/upload",
            method="POST",
            header={},
            path={},
            query={},
            body=None,
            form={},
            file={"f1": UploadFile(b"data", filename="test.txt", content_type="text/plain")}
        )

        await client.make_request(request)

        # Check call
        calls = mock_form.add_field.call_args_list
        assert any(
            c[0][0] == "f1" and
            c[0][1] == b"data" and
            c[1].get("filename") == "test.txt" and
            c[1].get("content_type") == "text/plain"
            for c in calls
        )
