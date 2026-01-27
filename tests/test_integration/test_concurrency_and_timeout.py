import asyncio
import time

import pytest
from unihttp.clients.aiohttp import AiohttpAsyncClient
from unihttp.clients.httpx import HTTPXAsyncClient
from unihttp.exceptions import RequestTimeoutError
from unihttp.method import BaseMethod
from unihttp.serialize import RequestDumper, ResponseLoader


class SimpleDumper(RequestDumper):
    def dump(self, method):
        path = {}
        if hasattr(method, "seconds"):
            path["seconds"] = method.seconds

        return {
            "path": path,
            "query": {},
            "header": {},
            "body": {},
            "file": {}
        }


class SimpleLoader(ResponseLoader):
    def load(self, data, response_type):
        return data


@pytest.fixture
def dumper(): return SimpleDumper()


@pytest.fixture
def loader(): return SimpleLoader()


class EchoMethod(BaseMethod[dict]):
    __url__ = "/echo"
    __method__ = "GET"


@pytest.mark.asyncio
async def test_concurrency_aiohttp(integration_server, dumper, loader):
    base_url = str(integration_server.make_url("/"))

    # Run 100 concurrent requests
    count = 100

    async with AiohttpAsyncClient(base_url, dumper, loader) as client:
        method = EchoMethod()

        tasks = [client.call_method(method) for _ in range(count)]
        results = await asyncio.gather(*tasks)

        assert len(results) == count
        # Verify structure
        for r in results:
            assert r["url"].endswith("/echo")


@pytest.mark.asyncio
async def test_concurrency_httpx(integration_server, dumper, loader):
    base_url = str(integration_server.make_url("/"))
    count = 50

    async with HTTPXAsyncClient(base_url, dumper, loader) as client:
        method = EchoMethod()

        tasks = [client.call_method(method) for _ in range(count)]
        results = await asyncio.gather(*tasks)

        assert len(results) == count


# Timeout tests
class SleepMethod(BaseMethod[dict]):
    __url__ = "/sleep/{seconds}"
    __method__ = "GET"

    def __init__(self, seconds):
        self.seconds = seconds


@pytest.mark.asyncio
async def test_real_timeout_aiohttp(integration_server, dumper, loader):
    base_url = str(integration_server.make_url("/"))

    import aiohttp

    # Client timeout 0.5s, server sleeps 1.0s
    timeout = aiohttp.ClientTimeout(total=0.5)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with AiohttpAsyncClient(base_url, dumper, loader, session=session) as client:
            method = SleepMethod(1.0)

            start = time.time()
            with pytest.raises(RequestTimeoutError):
                await client.call_method(method)
            duration = time.time() - start

            # It should fail roughly around 0.5s, definitely < 1.0s
            assert duration < 0.9


@pytest.mark.asyncio
async def test_real_timeout_httpx(integration_server, dumper, loader):
    base_url = str(integration_server.make_url("/"))

    import httpx

    async with httpx.AsyncClient(timeout=0.5) as session:
        async with HTTPXAsyncClient(base_url, dumper, loader, session=session) as client:
            method = SleepMethod(1.0)

            with pytest.raises(RequestTimeoutError):
                await client.call_method(method)


# We can also test "client timeout 2s, server sleep 0.5s" -> Success


@pytest.mark.asyncio
async def test_timeout_success(integration_server, dumper, loader):
    base_url = str(integration_server.make_url("/"))
    import aiohttp

    # Timeout > Sleep
    timeout = aiohttp.ClientTimeout(total=1.0)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with AiohttpAsyncClient(base_url, dumper, loader, session=session) as client:
            method = SleepMethod(0.1)
            await client.call_method(method)
