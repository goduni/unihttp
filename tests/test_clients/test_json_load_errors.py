import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from unihttp.http.request import HTTPRequest
from unihttp.http.response import HTTPResponse

from unihttp.clients.requests import RequestsSyncClient
from unihttp.clients.httpx import HTTPXSyncClient, HTTPXAsyncClient
from unihttp.clients.aiohttp import AiohttpAsyncClient
from unihttp.clients.niquests import NiquestsSyncClient, NiquestsAsyncClient

@pytest.fixture
def mock_request():
    return HTTPRequest("/", "GET", {}, {}, {}, {}, {}, {})

def test_requests_json_error(mock_request, mock_request_dumper, mock_response_loader):
    mock_session = Mock()
    mock_response = Mock()
    mock_response.content = b"not json"
    mock_response.status_code = 200
    mock_response.headers = {}
    mock_response.cookies = {}
    mock_session.request.return_value = mock_response
    
    client = RequestsSyncClient("http://base", mock_request_dumper, mock_response_loader, session=mock_session)
    response = client.make_request(mock_request)
    assert response.data == b"not json"

def test_httpx_sync_json_error(mock_request, mock_request_dumper, mock_response_loader):
    mock_session = Mock()
    mock_response = Mock()
    mock_response.content = b"not json"
    mock_response.text = "not json"
    mock_response.status_code = 200
    mock_response.headers = {}
    mock_response.cookies = {}
    mock_session.request.return_value = mock_response
    
    client = HTTPXSyncClient("http://base", mock_request_dumper, mock_response_loader, session=mock_session)
    response = client.make_request(mock_request)
    assert response.data == "not json"

@pytest.mark.asyncio
async def test_httpx_async_json_error(mock_request, mock_request_dumper, mock_response_loader):
    mock_session = AsyncMock()
    mock_response = Mock()
    mock_response.content = b"not json"
    mock_response.text = "not json"
    mock_response.status_code = 200
    mock_response.headers = {}
    mock_response.cookies = {}
    mock_session.request.return_value = mock_response
    
    client = HTTPXAsyncClient("http://base", mock_request_dumper, mock_response_loader, session=mock_session)
    response = await client.make_request(mock_request)
    assert response.data == "not json"

@pytest.mark.asyncio
async def test_aiohttp_json_error(mock_request, mock_request_dumper, mock_response_loader):
    mock_response = AsyncMock()
    mock_response.read.return_value = b"not json"
    mock_response.status = 200
    mock_response.headers = {}
    mock_response.cookies = {}
    
    # aiohttp uses context manager
    mock_session = MagicMock() # Use MagicMock for context manager
    mock_session.request.return_value.__aenter__ = AsyncMock(return_value=mock_response)
    mock_session.request.return_value.__aexit__ = AsyncMock()
    
    client = AiohttpAsyncClient("http://base", mock_request_dumper, mock_response_loader, session=mock_session)
    response = await client.make_request(mock_request)
    assert response.data == b"not json"

def test_niquests_sync_json_error(mock_request, mock_request_dumper, mock_response_loader):
    mock_session = Mock()
    mock_response = Mock()
    mock_response.content = b"not json"
    mock_response.status_code = 200
    mock_response.headers = {}
    mock_response.cookies = {}
    mock_session.request.return_value = mock_response
    
    client = NiquestsSyncClient("http://base", mock_request_dumper, mock_response_loader, session=mock_session)
    response = client.make_request(mock_request)
    assert response.data == b"not json"

@pytest.mark.asyncio
async def test_niquests_async_json_error(mock_request, mock_request_dumper, mock_response_loader):
    mock_session = AsyncMock()
    mock_response = Mock()
    mock_response.content = b"not json"
    mock_response.status_code = 200
    mock_response.headers = {}
    mock_response.cookies = {}
    mock_session.request.return_value = mock_response
    
    client = NiquestsAsyncClient("http://base", mock_request_dumper, mock_response_loader, session=mock_session)
    response = await client.make_request(mock_request)
    assert response.data == b"not json"
