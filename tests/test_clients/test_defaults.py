import pytest
from unihttp.clients.aiohttp import AiohttpAsyncClient
from unihttp.clients.httpx import HTTPXAsyncClient, HTTPXSyncClient
from unihttp.clients.httpx2 import HTTPX2AsyncClient, HTTPX2SyncClient
from unihttp.clients.requests import RequestsSyncClient


@pytest.mark.asyncio
async def test_aiohttp_default_session(mock_request_dumper, mock_response_loader):
    client = AiohttpAsyncClient("http://base", mock_request_dumper, mock_response_loader)
    await client.close()
    assert client._session is not None


@pytest.mark.asyncio
async def test_httpx_async_default_session(mock_request_dumper, mock_response_loader):
    client = HTTPXAsyncClient("http://base", mock_request_dumper, mock_response_loader)
    await client.close()
    assert client._session is not None


def test_httpx_sync_default_session(mock_request_dumper, mock_response_loader):
    client = HTTPXSyncClient("http://base", mock_request_dumper, mock_response_loader)
    client.close()
    assert client._session is not None


@pytest.mark.asyncio
async def test_httpx2_async_default_session(mock_request_dumper, mock_response_loader):
    client = HTTPX2AsyncClient("http://base", mock_request_dumper, mock_response_loader)
    await client.close()
    assert client._session is not None


def test_httpx2_sync_default_session(mock_request_dumper, mock_response_loader):
    client = HTTPX2SyncClient("http://base", mock_request_dumper, mock_response_loader)
    client.close()
    assert client._session is not None


def test_requests_default_session(mock_request_dumper, mock_response_loader):
    client = RequestsSyncClient("http://base", mock_request_dumper, mock_response_loader)
    client.close()
    assert client._session is not None
