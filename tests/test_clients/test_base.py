from unittest.mock import Mock

import pytest
from unihttp.clients.base import BaseAsyncClient, BaseSyncClient
from unihttp.http.request import HTTPRequest
from unihttp.http.response import HTTPResponse
from unihttp.http.stream import AsyncChunkStream, ChunkStream
from unihttp.method import BaseMethod, StreamMethod
from unihttp.middlewares.base import AsyncMiddleware, Middleware


class SimpleMethod(BaseMethod[str]):
    __url__ = "/test"
    __method__ = "GET"


class _FakeStreamMethod(StreamMethod):
    __url__ = "/files/{id}"
    __method__ = "GET"


class Tag(Middleware):
    """Records its name in `order` when the chain reaches it."""

    def __init__(self, order, name):
        self.order = order
        self.name = name

    def handle(self, request, next_handler):
        self.order.append(self.name)
        return next_handler(request)


class AsyncTag(AsyncMiddleware):
    def __init__(self, order, name):
        self.order = order
        self.name = name

    async def handle(self, request, next_handler):
        self.order.append(self.name)
        return await next_handler(request)


class Auth(Middleware):
    """setdefault, like a real auth middleware: first one in wins."""

    def __init__(self, token):
        self.token = token

    def handle(self, request, next_handler):
        request.header.setdefault("Auth", self.token)
        return next_handler(request)


class AsyncAuth(AsyncMiddleware):
    def __init__(self, token):
        self.token = token

    async def handle(self, request, next_handler):
        request.header.setdefault("Auth", self.token)
        return await next_handler(request)


class _GenChunkStream(ChunkStream):
    """Test double wiring a plain generator into the ChunkStream contract."""

    def __init__(self, gen, on_close):
        super().__init__()
        self._gen = gen
        self._on_close = on_close

    def _fetch_chunk(self):
        return next(self._gen)

    def _close_response(self):
        self._on_close()


class StreamClient(BaseSyncClient):
    def make_request(self, request):
        raise NotImplementedError

    def stream_make_request(self, request, chunk_size=65536):
        def gen():
            yield b"chunk1"
            yield b"chunk2"

        self.closed = False
        self.last_request = request
        return HTTPResponse(200, {}, _GenChunkStream(gen(), lambda: setattr(self, "closed", True)), {}, None)

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

    def test_error_handling_calls(self, mock_request_dumper, mock_response_loader):
        class ErrorClient(BaseSyncClient):
            def make_request(self, request):
                return HTTPResponse(400, {}, {}, {}, None)

            def handle_error(self, response, method):
                pass

        client = ErrorClient("http://base", mock_request_dumper, mock_response_loader)
        method = SimpleMethod()
        method.on_error = Mock()
        client.handle_error = Mock()

        mock_request_dumper.dump.return_value = {"path": {}, "query": {}, "header": {}, "body": {}}
        mock_response_loader.load.return_value = "proceeded"

        result = client.call_method(method)
        
        # Verify both hooks were called
        method.on_error.assert_called_once()
        client.handle_error.assert_called_once()
        # Verify it still proceeded to load response since no exception was raised
        assert result == "proceeded"

    def test_call_method_stream_full_consumption(self, mock_request_dumper, mock_response_loader):
        client = StreamClient("http://base", mock_request_dumper, mock_response_loader)
        mock_request_dumper.dump.return_value = {"path": {"id": "1"}}

        chunks = []
        with client.call_method_stream(_FakeStreamMethod()) as stream:
            for chunk in stream:
                chunks.append(chunk)

        assert chunks == [b"chunk1", b"chunk2"]
        assert client.closed is True

    def test_call_method_stream_early_break_still_closes(self, mock_request_dumper, mock_response_loader):
        client = StreamClient("http://base", mock_request_dumper, mock_response_loader)
        mock_request_dumper.dump.return_value = {"path": {"id": "1"}}

        with client.call_method_stream(_FakeStreamMethod()) as stream:
            for _chunk in stream:
                break

        assert client.closed is True

    def test_call_method_stream_status_not_ok_calls_on_error(self, mock_request_dumper, mock_response_loader):
        calls = []

        class _StreamMethodWithOnError(StreamMethod):
            __url__ = "/files/{id}"
            __method__ = "GET"

            def on_error(self, response):
                calls.append(response.status_code)

        class _ErrorClient(StreamClient):
            def stream_make_request(self, request, chunk_size=65536):
                self.closed = False
                return HTTPResponse(
                    404, {}, _GenChunkStream(iter(()), lambda: setattr(self, "closed", True)), {}, None
                )

            def handle_error(self, response, method):
                # Never-iterated regression: the caller's `with`/`for` never
                # runs at all because `call_method_stream` raises before
                # returning, so closing cannot rely on the iterator having
                # started.
                raise RuntimeError(f"HTTP {response.status_code}")

        client = _ErrorClient("http://base", mock_request_dumper, mock_response_loader)
        mock_request_dumper.dump.return_value = {"path": {"id": "1"}}

        with pytest.raises(RuntimeError):
            with client.call_method_stream(_StreamMethodWithOnError()) as stream:
                list(stream)

        assert calls == [404]
        # The connection must be released as soon as `call_method_stream` sees
        # the error status, before the caller ever gets a chance to iterate.
        assert client.closed is True

    def test_middleware_layers(self, mock_request_dumper, mock_response_loader):
        order = []
        seen = []

        class _Method(SimpleMethod):
            __middleware__ = (Tag(order, "method"),)

        class _Client(self.MockClient):
            def make_request(self, request):
                seen.append(request.header.get("Auth"))
                return HTTPResponse(200, {}, {}, {}, None)

        client = _Client(
            "http://base", mock_request_dumper, mock_response_loader,
            middleware=[Tag(order, "client")],
        )
        # fresh dicts per call: Auth mutates request.header in place
        mock_request_dumper.dump.side_effect = lambda *a, **k: {"path": {}, "query": {}, "header": {}, "body": {}}
        mock_response_loader.load.return_value = "res"

        client.call_method(_Method(), middleware=[Tag(order, "A"), Auth("token-A")])
        client.call_method(_Method(), middleware=[Tag(order, "B"), Auth("token-B")])
        client.call_method(SimpleMethod())

        # client (outermost) -> method -> per-call, on every call; a plain
        # method and a call without middleware= are unaffected.
        assert order == ["client", "method", "A", "client", "method", "B", "client"]
        # Auth uses setdefault, so a shared client must not leak the first
        # caller's token into the second call.
        assert seen == ["token-A", "token-B", None]

    def test_middleware_layers_stream(self, mock_request_dumper, mock_response_loader):
        order = []
        client = StreamClient(
            "http://base", mock_request_dumper, mock_response_loader,
            middleware=[Tag(order, "client")],
        )
        mock_request_dumper.dump.return_value = {"path": {"id": "1"}}

        class _Method(_FakeStreamMethod):
            __middleware__ = (Tag(order, "method"),)

        with client.call_method_stream(
            _Method(), middleware=[Tag(order, "A")]
        ) as stream:
            list(stream)

        assert order == ["client", "method", "A"]


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

    class _AsyncGenChunkStream(AsyncChunkStream):
        """Test double wiring a plain async generator into the AsyncChunkStream contract."""

        def __init__(self, gen, on_close):
            super().__init__()
            self._gen = gen
            self._on_close = on_close

        async def _fetch_chunk(self):
            return await self._gen.__anext__()

        async def _close_response(self):
            self._on_close()

    class StreamClient(BaseAsyncClient):
        async def make_request(self, request):
            raise NotImplementedError

        async def stream_make_request(self, request, chunk_size=65536):
            async def gen():
                yield b"chunk1"
                yield b"chunk2"

            self.closed = False
            self.last_request = request
            return HTTPResponse(
                200, {}, TestAsyncClient._AsyncGenChunkStream(gen(), lambda: setattr(self, "closed", True)), {}, None
            )

    async def test_call_method_stream_full_consumption(self, mock_request_dumper, mock_response_loader):
        client = self.StreamClient("http://base", mock_request_dumper, mock_response_loader)
        mock_request_dumper.dump.return_value = {"path": {"id": "1"}}

        chunks = []
        async with await client.call_method_stream(_FakeStreamMethod()) as stream:
            async for chunk in stream:
                chunks.append(chunk)

        assert chunks == [b"chunk1", b"chunk2"]
        assert client.closed is True

    async def test_call_method_stream_early_break_still_closes(self, mock_request_dumper, mock_response_loader):
        client = self.StreamClient("http://base", mock_request_dumper, mock_response_loader)
        mock_request_dumper.dump.return_value = {"path": {"id": "1"}}

        async with await client.call_method_stream(_FakeStreamMethod()) as stream:
            async for _chunk in stream:
                break

        assert client.closed is True

    async def test_call_method_stream_status_not_ok_calls_on_error(self, mock_request_dumper, mock_response_loader):
        calls = []

        class _StreamMethodWithOnError(StreamMethod):
            __url__ = "/files/{id}"
            __method__ = "GET"

            def on_error(self, response):
                calls.append(response.status_code)

        async def empty_gen():
            return
            yield  # pragma: no cover - makes this an async generator

        class _ErrorClient(self.StreamClient):
            async def stream_make_request(self, request, chunk_size=65536):
                self.closed = False
                return HTTPResponse(
                    404, {},
                    TestAsyncClient._AsyncGenChunkStream(empty_gen(), lambda: setattr(self, "closed", True)),
                    {}, None,
                )

            def handle_error(self, response, method):
                # Never-iterated regression: the caller's `async with`/`for`
                # never runs at all because `call_method_stream` raises
                # before returning, so closing cannot rely on the async
                # iterator having started.
                raise RuntimeError(f"HTTP {response.status_code}")

        client = _ErrorClient("http://base", mock_request_dumper, mock_response_loader)
        mock_request_dumper.dump.return_value = {"path": {"id": "1"}}

        with pytest.raises(RuntimeError):
            async with await client.call_method_stream(_StreamMethodWithOnError()) as stream:
                async for _chunk in stream:
                    pass

        assert calls == [404]
        # The connection must be released as soon as `call_method_stream` sees
        # the error status, before the caller ever gets a chance to iterate.
        assert client.closed is True

    async def test_middleware_layers(self, mock_request_dumper, mock_response_loader):
        order = []
        hooks = []
        seen = []

        class _Method(SimpleMethod):
            __middleware__ = (AsyncTag(order, "method"),)

        class _Client(self.MockClient):
            async def make_request(self, request):
                seen.append(request.header.get("Auth"))
                return HTTPResponse(200, {}, {}, {}, None)

            def validate_response(self, response, method):
                hooks.append("validate")

        client = _Client(
            "http://base", mock_request_dumper, mock_response_loader,
            middleware=[AsyncTag(order, "client")],
        )
        # fresh dicts per call: AsyncAuth mutates request.header in place
        mock_request_dumper.dump.side_effect = lambda *a, **k: {"path": {}, "query": {}, "header": {}, "body": {}}
        mock_response_loader.load.return_value = "res"

        await client.call_method(
            _Method(), middleware=[AsyncTag(order, "A"), AsyncAuth("token-A")]
        )
        await client.call_method(
            _Method(), middleware=[AsyncTag(order, "B"), AsyncAuth("token-B")]
        )
        await client.call_method(SimpleMethod())

        assert order == ["client", "method", "A", "client", "method", "B", "client"]
        # Auth uses setdefault: a shared client must not leak the first
        # caller's token into the second call.
        assert seen == ["token-A", "token-B", None]
        assert hooks == ["validate"] * 3

    async def test_middleware_layers_stream(self, mock_request_dumper, mock_response_loader):
        order = []
        client = self.StreamClient(
            "http://base", mock_request_dumper, mock_response_loader,
            middleware=[AsyncTag(order, "client")],
        )
        mock_request_dumper.dump.return_value = {"path": {"id": "1"}}

        class _Method(_FakeStreamMethod):
            __middleware__ = (AsyncTag(order, "method"),)

        async with await client.call_method_stream(
            _Method(), middleware=[AsyncTag(order, "A")]
        ) as stream:
            async for _chunk in stream:
                pass

        assert order == ["client", "method", "A"]
