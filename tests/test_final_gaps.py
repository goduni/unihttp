import asyncio
from unittest.mock import Mock

import pytest
from unihttp.clients.base import BaseAsyncClient, BaseSyncClient
from unihttp.http.request import HTTPRequest
from unihttp.http.response import HTTPResponse
from unihttp.method import BaseMethod
from unihttp.middlewares.error_mapper import DefaultErrorMapperMiddleware
from unihttp.middlewares.retry import AsyncRetryMiddleware


# 1. Base Client Context Managers & Error Handling
@pytest.mark.asyncio
async def test_base_client_context_managers(mock_request_dumper, mock_response_loader):
    class SyncC(BaseSyncClient):
        def make_request(self, req): return HTTPResponse(200, {}, {}, {}, None)

    class AsyncC(BaseAsyncClient):
        async def make_request(self, req): return HTTPResponse(200, {}, {}, {}, None)

    # Sync
    with SyncC("http://b", mock_request_dumper, mock_response_loader) as c:
        pass

    # Async
    async with AsyncC("http://b", mock_request_dumper, mock_response_loader) as c:
        pass


@pytest.mark.asyncio
async def test_async_client_error_handling(mock_request_dumper, mock_response_loader):
    class AsyncC(BaseAsyncClient):
        async def make_request(self, req): return HTTPResponse(400, {}, {}, {}, None)

        def handle_error(self, resp, method): return "client_handled"

    class Method(BaseMethod[str]):
        __url__ = "/"
        __method__ = "GET"

        def on_error(self, resp): return "method_handled"

    client = AsyncC("http://b", mock_request_dumper, mock_response_loader)
    mock_request_dumper.dump.return_value = {}

    # Method handles it
    res = await client.call_method(Method())
    assert res == "method_handled"

    # Client handles it
    m = Method()
    m.on_error = lambda r: None
    res = await client.call_method(m)
    assert res == "client_handled"


# 2. Async Retry Re-raise
@pytest.mark.asyncio
async def test_async_retry_reraise():
    middleware = AsyncRetryMiddleware(exceptions=[ValueError], retries=2)
    handler = Mock(side_effect=TypeError("fail"))

    with pytest.raises(TypeError):
        await middleware.handle(HTTPRequest("/", "GET", {}, {}, {}, {}, {}, {}), handler)


# 3. Error Mapper Unknown Key
def test_error_mapper_unknown_key():
    mapper = DefaultErrorMapperMiddleware({
        "bad_key": ValueError  # type: ignore
    })
    # Should not match string key
    assert not mapper._matches(404, "bad_key")  # type: ignore


def test_base_client_default_handle_error():
    # Test that default handle_error returns None
    from unihttp.clients.base import BaseSyncClient

    class SimpleC(BaseSyncClient):
        def make_request(self, req): return HTTPResponse(400, {}, {}, {}, None)

    mock_dumper = Mock()
    mock_dumper.dump.return_value = {"path": {}, "header": {}, "query": {}, "body": {}, "file": {}}
    client = SimpleC("http://b", mock_dumper, Mock())

    class Method(BaseMethod[str]):
        __url__ = "/"
        __method__ = "GET"

    # Method.on_error default returns None. Client.handle_error default returns None.
    # So call_method should raise Exception (make_response called?)
    # Wait, call_method continues if both return None.
    # It proceeds to make_response.

    mock_loader = Mock()
    mock_loader.load.return_value = "ok"
    client.response_loader = mock_loader

    res = client.call_method(Method())
    assert res == "ok"


@pytest.mark.asyncio
async def test_async_retry_jitter(mocker):
    # Test async jitter execution
    mock_sleep = mocker.patch("asyncio.sleep")
    mock_random = mocker.patch("random.uniform", return_value=0.5)

    handler = Mock()
    f = asyncio.Future()
    f.set_result(HTTPResponse(500, {}, {}, {}, None))
    handler.side_effect = [f, f]  # Retry once

    middleware = AsyncRetryMiddleware(retries=1, backoff=1.0, jitter=True)
    request = HTTPRequest("/", "GET", {}, {}, {}, {}, {}, {})

    try:
        await middleware.handle(request, handler)
    except Exception:
        pass  # It will return response eventually

    # Check sleep called with jitter
    # 1.0 * 2^0 + 0.5 = 1.5
    mock_sleep.assert_called_once_with(1.5)


def test_sync_retry_raise_coverage():
    from unihttp.middlewares.retry import RetryMiddleware
    middleware = RetryMiddleware()  # No exceptions specified
    handler = Mock(side_effect=ValueError("fail"))

    with pytest.raises(ValueError):
        middleware.handle(HTTPRequest("/", "GET", {}, {}, {}, {}, {}, {}), handler)
