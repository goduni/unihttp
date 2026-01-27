from unittest.mock import AsyncMock, MagicMock

import pytest
from unihttp.bind_method import bind_method
from unihttp.method import BaseMethod


class MockMethod(BaseMethod[str]):
    __url__ = "/test"
    __method__ = "GET"


class SyncClient:
    def __init__(self):
        self.call_method = MagicMock(return_value="sync_result")

    method = bind_method(MockMethod)


class AsyncClient:
    def __init__(self):
        self.call_method = AsyncMock(return_value="async_result")

    method = bind_method(MockMethod)


class InvalidClient:
    method = bind_method(MockMethod)


def test_bind_sync():
    client = SyncClient()
    result = client.method()

    assert result == "sync_result"
    client.call_method.assert_called_once()
    assert isinstance(client.call_method.call_args[0][0], MockMethod)


@pytest.mark.asyncio
async def test_bind_async():
    client = AsyncClient()
    result = await client.method()

    assert result == "async_result"
    client.call_method.assert_called_once()
    assert isinstance(client.call_method.call_args[0][0], MockMethod)


def test_bind_class_access():
    # Accessing via class should return the binder itself
    assert isinstance(SyncClient.method, type(bind_method(MockMethod)))


def test_bind_invalid_client():
    client = InvalidClient()
    with pytest.raises(RuntimeError, match="available only for classes with `call_method`"):
        _ = client.method
