import json
from unittest.mock import AsyncMock, Mock

import pytest
import httpx
from unihttp.clients.httpx import HTTPXAsyncClient
from unihttp.http.request import HTTPRequest
from unihttp.markers import FormMarker

@pytest.fixture
def mock_client():
    return AsyncMock(spec=httpx.AsyncClient)

@pytest.fixture
def mock_response():
    resp = Mock()
    resp.status_code = 200
    resp.headers = {}
    resp.cookies = {}
    # Default text for json loads
    resp.text = '{"ok": true}'
    resp.content = b'{"ok": true}'
    return resp

@pytest.mark.asyncio
async def test_httpx_json_body_custom_dumps(mock_request_dumper, mock_response_loader, mock_client, mock_response):
    custom_dumps = Mock(return_value='{"custom": "json"}')
    custom_loads = Mock(return_value={"loaded": "custom"})
    
    client = HTTPXAsyncClient(
        "http://base", mock_request_dumper, mock_response_loader, 
        session=mock_client,
        json_dumps=custom_dumps,
        json_loads=custom_loads
    )
    mock_client.request.return_value = mock_response

    request = HTTPRequest(
        url="/json", method="POST", header={}, path={}, query={},
        body={"foo": "bar"}, file={}, form={}
    )

    await client.make_request(request)

    # Verify custom dumper was used
    custom_dumps.assert_called_once_with({"foo": "bar"})
    
    # Verify httpx called with content string and content-type header
    mock_client.request.assert_called_once()
    call_kwargs = mock_client.request.call_args.kwargs
    assert call_kwargs["content"] == '{"custom": "json"}'
    assert call_kwargs["headers"]["Content-Type"] == "application/json"
    assert call_kwargs["data"] == {}

    # Verify custom loader used
    custom_loads.assert_called_once_with('{"ok": true}')

@pytest.mark.asyncio
async def test_httpx_form_data(mock_request_dumper, mock_response_loader, mock_client, mock_response):
    client = HTTPXAsyncClient("http://base", mock_request_dumper, mock_response_loader, session=mock_client)
    mock_client.request.return_value = mock_response

    request = HTTPRequest(
        url="/form", method="POST", header={}, path={}, query={},
        body={}, file={}, form={"field": "value"}
    )

    await client.make_request(request)

    mock_client.request.assert_called_once()
    call_kwargs = mock_client.request.call_args.kwargs
    assert call_kwargs["data"] == {"field": "value"}
    assert call_kwargs["content"] is None
    # No forced content-type for form (httpx handles it) 
    # But if data is dict, httpx sets application/x-www-form-urlencoded

@pytest.mark.asyncio
async def test_httpx_mixed_body_form_error(mock_request_dumper, mock_response_loader, mock_client):
    client = HTTPXAsyncClient("http://base", mock_request_dumper, mock_response_loader, session=mock_client)
    
    request = HTTPRequest(
        url="/mixed", method="POST", header={}, path={}, query={},
        body={"json": "part"}, file={}, form={"form": "part"}
    )

    with pytest.raises(ValueError, match="Cannot use Body with Form or File"):
        await client.make_request(request)

@pytest.mark.asyncio
async def test_httpx_multipart(mock_request_dumper, mock_response_loader, mock_client, mock_response):
    client = HTTPXAsyncClient("http://base", mock_request_dumper, mock_response_loader, session=mock_client)
    mock_client.request.return_value = mock_response

    request = HTTPRequest(
        url="/files", method="POST", header={}, path={}, query={},
        body={}, file={"file": b"bits"}, form={"meta": "data"}
    )

    await client.make_request(request)

    mock_client.request.assert_called_once()
    call_kwargs = mock_client.request.call_args.kwargs
    assert call_kwargs["files"] == [("file", b"bits")]
    assert call_kwargs["data"] == {"meta": "data"}
    assert call_kwargs["content"] is None
