# Reuse existing dumper/loader logic or simple implementations?
# We should use real dumper logic to verify it works, but for now we can mock
# the internal serialization to focus on CLIENT transport.
# Actually, let's make a simple "PassThrough" dumper/loader for integration.
import json

import pytest
from unihttp.clients.aiohttp import AiohttpAsyncClient
from unihttp.clients.httpx import HTTPXAsyncClient
from unihttp.clients.requests import RequestsSyncClient
from unihttp.method import BaseMethod
from unihttp.serialize import RequestDumper, ResponseLoader


class PassThroughDumper(RequestDumper):
    def dump(self, method):
        body = getattr(method, "body", {})
        headers = getattr(method, "headers", {})

        # Determine content type
        if "Content-Type" not in headers:
            headers["Content-Type"] = "application/json"

        # Serialize body if JSON
        if headers["Content-Type"] == "application/json" and isinstance(body, dict):
             # We pass dict as body to client. Client handles serialization.
             pass

        return {
            "path": {},
            "query": {},
            "header": headers,
            "body": body,
            "file": {}
        }


class PassThroughLoader(ResponseLoader):
    def load(self, data, response_type):
        return data


@pytest.fixture
def real_dumper(): return PassThroughDumper()


@pytest.fixture
def real_loader(): return PassThroughLoader()


class EchoMethod(BaseMethod[dict]):
    __url__ = "/echo"
    __method__ = "POST"

    def __init__(self, body=None, headers=None):
        self.body = body or {}
        self.headers = headers or {}


@pytest.mark.asyncio
async def test_aiohttp_real_echo(integration_server, real_dumper, real_loader):
    base_url = str(integration_server.make_url("/"))

    async with AiohttpAsyncClient(base_url, real_dumper, real_loader) as client:
        method = EchoMethod(body={"hello": "world"}, headers={"X-Test": "aiohttp"})
        result = await client.call_method(method)

        assert result["body"] == {"hello": "world"}
        assert result["headers"]["X-Test"] == "aiohttp"


@pytest.mark.asyncio
async def test_httpx_async_real_echo(integration_server, real_dumper, real_loader):
    base_url = str(integration_server.make_url("/"))

    async with HTTPXAsyncClient(base_url, real_dumper, real_loader) as client:
        method = EchoMethod(body={"foo": "bar"}, headers={"X-Test": "httpx"})
        result = await client.call_method(method)

        assert result["body"] == {"foo": "bar"}
        assert result["headers"]["X-Test"] == "httpx"


@pytest.mark.skip(reason="Sync client blocks the event loop of the async server fixture")
def test_requests_real_echo(integration_server, real_dumper, real_loader):
    base_url = str(integration_server.make_url("/"))

    with RequestsSyncClient(base_url, real_dumper, real_loader) as client:
        method = EchoMethod(body={"sync": "true"}, headers={"X-Test": "requests"})
        result = client.call_method(method)

        assert result["body"] == {"sync": "true"}
        assert result["headers"]["X-Test"] == "requests"
