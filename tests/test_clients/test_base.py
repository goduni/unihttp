from unittest.mock import Mock

import pytest
from unihttp.clients.base import BaseAsyncClient, BaseSyncClient
from unihttp.http.request import HTTPRequest
from unihttp.http.response import HTTPResponse
from unihttp.method import BaseMethod
from unihttp.middlewares.base import AsyncMiddleware, Middleware


class SimpleMethod(BaseMethod[str]):
    __url__ = "/test"
    __method__ = "GET"


class TestSyncClient:
    class MockClient(BaseSyncClient):
        def make_request(self, request: HTTPRequest) -> HTTPResponse:
            return HTTPResponse(200, {}, {"data": "ok"}, {}, None)

    def test_call_method_basic(self, mock_request_dumper, mock_response_loader):
        client = self.MockClient("http://base", mock_request_dumper, mock_response_loader)
        method = SimpleMethod()

        # Mock dumper/loader
        mock_request_dumper.dump.return_value = {"path": {}, "query": {}, "header": {}, "body": {}}
        mock_response_loader.load.return_value = "final_result"

        result = client.call_method(method)

        assert result == "final_result"

    def test_middleware_chain(self, mock_request_dumper, mock_response_loader):
        order = []

        class MW1(Middleware):
            def handle(self, request, next_handler):
                order.append("mw1_req")
                resp = next_handler(request)
                order.append("mw1_resp")
                return resp

        class MW2(Middleware):
            def handle(self, request, next_handler):
                order.append("mw2_req")
                resp = next_handler(request)
                order.append("mw2_resp")
                return resp

        client = self.MockClient(
            "http://base", mock_request_dumper, mock_response_loader,
            middleware=[MW1(), MW2()]
        )
        method = SimpleMethod()
        mock_request_dumper.dump.return_value = {"path": {}, "query": {}, "header": {}, "body": {}}
        mock_response_loader.load.return_value = "res"

        client.call_method(method)

        # Check order: MW1 req -> MW2 req -> client -> MW2 resp -> MW1 resp
        assert order == ["mw1_req", "mw2_req", "mw2_resp", "mw1_resp"]

    def test_error_handling_priority(self, mock_request_dumper, mock_response_loader):
        class ErrorClient(BaseSyncClient):
            def make_request(self, request):
                return HTTPResponse(400, {}, {}, {}, None)

            def handle_error(self, response, method):
                return "client_handled"

        client = ErrorClient("http://base", mock_request_dumper, mock_response_loader)
        method = SimpleMethod()
        method.on_error = Mock(return_value="method_handled")

        mock_request_dumper.dump.return_value = {"path": {}, "query": {}, "header": {}, "body": {}}

        # 1. Method handles it
        result = client.call_method(method)
        assert result == "method_handled"

        # 2. Method passes (returns None), Client handles it
        method.on_error = Mock(return_value=None)
        result = client.call_method(method)
        assert result == "client_handled"


@pytest.mark.asyncio
class TestAsyncClient:
    class MockClient(BaseAsyncClient):
        async def make_request(self, request: HTTPRequest) -> HTTPResponse:
            return HTTPResponse(200, {}, {"data": "ok"}, {}, None)

    async def test_call_method_basic(self, mock_request_dumper, mock_response_loader):
        client = self.MockClient("http://base", mock_request_dumper, mock_response_loader)
        method = SimpleMethod()

        mock_request_dumper.dump.return_value = {"path": {}, "query": {}, "header": {}, "body": {}}
        mock_response_loader.load.return_value = "final_result"

        result = await client.call_method(method)

        assert result == "final_result"

    async def test_middleware_chain(self, mock_request_dumper, mock_response_loader):
        order = []

        class MW1(AsyncMiddleware):
            async def handle(self, request, next_handler):
                order.append("mw1_req")
                resp = await next_handler(request)
                order.append("mw1_resp")
                return resp

        class MW2(AsyncMiddleware):
            async def handle(self, request, next_handler):
                order.append("mw2_req")
                resp = await next_handler(request)
                order.append("mw2_resp")
                return resp

        client = self.MockClient(
            "http://base", mock_request_dumper, mock_response_loader,
            middleware=[MW1(), MW2()]
        )
        method = SimpleMethod()
        mock_request_dumper.dump.return_value = {"path": {}, "query": {}, "header": {}, "body": {}}
        mock_response_loader.load.return_value = "res"

        await client.call_method(method)

        assert order == ["mw1_req", "mw2_req", "mw2_resp", "mw1_resp"]
