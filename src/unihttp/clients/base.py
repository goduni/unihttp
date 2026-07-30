import functools
import json
from collections.abc import Callable, Sequence
from typing import Any

from unihttp.http.request import HTTPRequest
from unihttp.http.response import HTTPResponse
from unihttp.http.stream import AsyncChunkStream, ChunkStream
from unihttp.method import BaseMethod, ResponseType, StreamMethod
from unihttp.middlewares.base import AsyncHandler, AsyncMiddleware, Handler, Middleware
from unihttp.serialize import RequestDumper, ResponseLoader


class BaseClient:
    """Base client class providing common functionality for both sync and async clients.

    Attributes:
        base_url: The base URL for all requests.
        request_dumper: Component to serialize method objects into HTTP requests.
        response_loader: Component to deserialize HTTP responses into method return types.
        json_dumps: Function to serialize objects to JSON strings.
        json_loads: Function to deserialize JSON strings to objects.
    """

    def __init__(
        self,
        base_url: str,
        request_dumper: RequestDumper,
        response_loader: ResponseLoader,
        json_dumps: Callable[[Any], str] = json.dumps,
        json_loads: Callable[[str | bytes | bytearray], Any] = json.loads,
    ):
        self.base_url = base_url
        self.request_dumper = request_dumper
        self.response_loader = response_loader
        self.json_dumps = json_dumps
        self.json_loads = json_loads

    def validate_response(self, response: HTTPResponse, method: BaseMethod) -> None:
        """Validate response BODY for all methods.

        Override to handle APIs that return errors in body with 200 status.
        Called for ALL responses, BEFORE method.validate_response.

        Args:
            response: The HTTP response to validate.
            method: The method instance that triggered the request.

        Raises:
            Exception: if response body indicates an error.
        """

    def handle_error(
        self, response: HTTPResponse, method: BaseMethod | StreamMethod
    ) -> None:
        """Handle HTTP status errors for all methods.

        Override to provide shared error handling for all API methods.
        Called when response.ok is False, AFTER method.on_error.

        Args:
             response: The HTTP response with error status.
             method: The method instance that triggered the request. Either a
                `BaseMethod` (from `call_method`) or a `StreamMethod` (from
                `call_method_stream`).

        Raises:
            Exception: if response indicates an error that should stop processing.
        """


class BaseSyncClient(BaseClient):
    """Base class for synchronous HTTP clients."""

    def __init__(
        self,
        base_url: str,
        request_dumper: RequestDumper,
        response_loader: ResponseLoader,
        middleware: list[Middleware] | None = None,
        json_dumps: Callable[[Any], str] = json.dumps,
        json_loads: Callable[[str | bytes | bytearray], dict | list] = json.loads,
    ):
        super().__init__(
            base_url=base_url,
            request_dumper=request_dumper,
            response_loader=response_loader,
            json_dumps=json_dumps,
            json_loads=json_loads,
        )
        self.middleware = middleware or []

    def _chain_middleware(
        self,
        handler: Handler,
        call_middleware: Sequence[Middleware] = (),
    ) -> Handler:
        for middleware in reversed([*self.middleware, *call_middleware]):
            handler = functools.partial(middleware.handle, next_handler=handler)
        return handler

    def call_method(
        self,
        method: BaseMethod[ResponseType],
        *,
        middleware: Sequence[Middleware] | None = None,
    ) -> ResponseType:
        """Execute an API method synchronously.

        Pipeline:
        1. Serialize method to HTTPRequest.
        2. Apply middlewares.
        3. Execute request (make_request), validate and handle errors.
        4. Deserialize response to ResponseType.

        Args:
            method: The API method instance to execute.
            middleware: Extra middleware for this call only. Chain order is
                outermost-first: client `self.middleware`, then these.

        Returns:
             The deserialized response data as defined by the method's return type.
        """
        http_request = method.build_http_request(request_dumper=self.request_dumper)

        def _send(request: HTTPRequest) -> HTTPResponse:
            response = self.make_request(request)

            # Body validation (for APIs with ok: false in 200)
            self.validate_response(response, method)
            method.validate_response(response)

            # HTTP status error handling
            if not response.ok:
                method.on_error(response)
                self.handle_error(response, method)

            return response

        http_response = self._chain_middleware(_send, middleware or ())(http_request)

        return method.make_response(http_response, response_loader=self.response_loader)

    def make_request(self, request: HTTPRequest) -> HTTPResponse:
        """Perform the actual HTTP request.

        Must be implemented by concrete client subclasses.

        Args:
            request: The unified HTTP request object.

        Returns:
            HTTPResponse: The unified HTTP response object.
        """
        raise NotImplementedError

    def stream_make_request(
        self, request: HTTPRequest, chunk_size: int = 65536
    ) -> HTTPResponse[ChunkStream]:
        """Perform the actual streaming HTTP request.

        Must be implemented by concrete client subclasses.

        Args:
            request: The unified HTTP request object.
            chunk_size: Number of bytes to read per chunk.

        Returns:
            HTTPResponse: status/headers available immediately, `.data` is
            an unconsumed `ChunkStream`.
        """
        raise NotImplementedError

    def call_method_stream(
        self,
        method: StreamMethod,
        *,
        middleware: Sequence[Middleware] | None = None,
    ) -> ChunkStream:
        """Execute a streaming API method synchronously.

        Pipeline mirrors `call_method`, but the terminal handler streams the
        body instead of buffering it, and there is no response_loader step.

        Args:
            method: The stream method instance to execute.
                `method.__chunk_size__` controls how many bytes are read per
                chunk.
            middleware: Extra middleware for this call only. Chain order is
                outermost-first: client `self.middleware`, then these.

        Returns:
            A `ChunkStream` of `bytes` chunks. Use as a context manager
            (`with client.call_method_stream(method) as stream:`) — it
            closes the underlying connection on exit, even if the caller
            stops iterating early.
        """
        request = method.build_http_request(request_dumper=self.request_dumper)

        def _send(request_: HTTPRequest) -> HTTPResponse[ChunkStream]:
            response_ = self.stream_make_request(
                request_, chunk_size=method.__chunk_size__
            )

            if not response_.ok:
                # ChunkStream.close() is a direct call, not tied to whether
                # iteration ever started (unlike closing a bare generator).
                response_.data.close()
                method.on_error(response_)
                self.handle_error(response_, method)

            return response_

        return self._chain_middleware(_send, middleware or ())(request).data

    def close(self) -> None:
        """Close the client and release resources."""

    def __enter__(self) -> "BaseSyncClient":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()


class BaseAsyncClient(BaseClient):
    """Base class for asynchronous HTTP clients."""

    def __init__(
        self,
        base_url: str,
        request_dumper: RequestDumper,
        response_loader: ResponseLoader,
        middleware: list[AsyncMiddleware] | None = None,
        json_dumps: Callable[[Any], str] = json.dumps,
        json_loads: Callable[[str | bytes | bytearray], Any] = json.loads,
    ):
        super().__init__(
            base_url=base_url,
            request_dumper=request_dumper,
            response_loader=response_loader,
            json_dumps=json_dumps,
            json_loads=json_loads,
        )
        self.middleware = middleware or []

    def _chain_middleware(
        self,
        handler: AsyncHandler,
        call_middleware: Sequence[AsyncMiddleware] = (),
    ) -> AsyncHandler:
        for middleware in reversed([*self.middleware, *call_middleware]):
            handler = functools.partial(middleware.handle, next_handler=handler)
        return handler

    async def call_method(
        self,
        method: BaseMethod[ResponseType],
        *,
        middleware: Sequence[AsyncMiddleware] | None = None,
    ) -> ResponseType:
        """Execute an API method asynchronously.

        Pipeline:
        1. Serialize method to HTTPRequest.
        2. Apply middlewares.
        3. Execute request (make_request), validate and handle errors.
        4. Deserialize response to ResponseType.

        Args:
            method: The API method instance to execute.
            middleware: Extra middleware for this call only. Chain order is
                outermost-first: client `self.middleware`, then these.

        Returns:
             The deserialized response data as defined by the method's return type.
        """
        http_request = method.build_http_request(request_dumper=self.request_dumper)

        async def _send(request: HTTPRequest) -> HTTPResponse:
            response = await self.make_request(request)

            # Body validation (for APIs with ok: false in 200)
            self.validate_response(response, method)
            method.validate_response(response)

            # HTTP status error handling
            if not response.ok:
                method.on_error(response)
                self.handle_error(response, method)

            return response

        http_response = await self._chain_middleware(_send, middleware or ())(
            http_request
        )

        return method.make_response(http_response, response_loader=self.response_loader)

    async def make_request(self, request: HTTPRequest) -> HTTPResponse:
        """Perform the actual HTTP request asynchronously.

        Must be implemented by concrete client subclasses.

        Args:
            request: The unified HTTP request object.

        Returns:
            HTTPResponse: The unified HTTP response object.
        """
        raise NotImplementedError

    async def stream_make_request(
        self, request: HTTPRequest, chunk_size: int = 65536
    ) -> HTTPResponse[AsyncChunkStream]:
        """Perform the actual streaming HTTP request asynchronously.

        Must be implemented by concrete client subclasses.

        Args:
            request: The unified HTTP request object.
            chunk_size: Number of bytes to read per chunk.

        Returns:
            HTTPResponse: status/headers available immediately, `.data` is
            an unconsumed `AsyncChunkStream`.
        """
        raise NotImplementedError

    async def call_method_stream(
        self,
        method: StreamMethod,
        *,
        middleware: Sequence[AsyncMiddleware] | None = None,
    ) -> AsyncChunkStream:
        """Execute a streaming API method asynchronously.

        Pipeline mirrors `call_method`, but the terminal handler streams the
        body instead of buffering it, and there is no response_loader step.

        Args:
            method: The stream method instance to execute.
                `method.__chunk_size__` controls how many bytes are read per
                chunk.
            middleware: Extra middleware for this call only. Chain order is
                outermost-first: client `self.middleware`, then these.

        Returns:
            An `AsyncChunkStream` of `bytes` chunks. Use as a context
            manager (`async with await client.call_method_stream(method) as
            stream:`) — it closes the underlying connection on exit, even
            if the caller stops iterating early.
        """
        request = method.build_http_request(request_dumper=self.request_dumper)

        async def _send(request_: HTTPRequest) -> HTTPResponse[AsyncChunkStream]:
            response_ = await self.stream_make_request(
                request_, chunk_size=method.__chunk_size__
            )

            if not response_.ok:
                # AsyncChunkStream.aclose() is a direct call, not tied to
                # whether iteration ever started (unlike aclosing a bare
                # async generator).
                await response_.data.aclose()
                method.on_error(response_)
                self.handle_error(response_, method)

            return response_

        response = await self._chain_middleware(_send, middleware or ())(request)
        return response.data

    async def close(self) -> None:
        """Close the client and release resources asynchronously."""

    async def __aenter__(self) -> "BaseAsyncClient":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()
