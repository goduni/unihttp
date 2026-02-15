import functools
import json
from collections.abc import Callable
from typing import Any

from unihttp.http.request import HTTPRequest
from unihttp.http.response import HTTPResponse
from unihttp.method import BaseMethod, ResponseType
from unihttp.middlewares.base import AsyncMiddleware, Middleware
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

    def handle_error(self, response: HTTPResponse, method: BaseMethod) -> None:
        """Handle HTTP status errors for all methods.

        Override to provide shared error handling for all API methods.
        Called when response.ok is False, AFTER method.on_error.

        Args:
             response: The HTTP response with error status.
             method: The method instance that triggered the request.

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

    def call_method(self, method: BaseMethod[ResponseType]) -> ResponseType:
        """Execute an API method synchronously.

        Pipeline:
        1. Serialize method to HTTPRequest.
        2. Apply middlewares.
        3. Execute request (make_request), validate and handle errors.
        4. Deserialize response to ResponseType.

        Args:
            method: The API method instance to execute.

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

        handler = _send
        for middleware in reversed(self.middleware):
            handler = functools.partial(middleware.handle, next_handler=handler)

        http_response = handler(http_request)

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

    async def call_method(self, method: BaseMethod[ResponseType]) -> ResponseType:
        """Execute an API method asynchronously.

        Pipeline:
        1. Serialize method to HTTPRequest.
        2. Apply middlewares.
        3. Execute request (make_request), validate and handle errors.
        4. Deserialize response to ResponseType.

        Args:
            method: The API method instance to execute.

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

        handler = _send
        for middleware in reversed(self.middleware):
            handler = functools.partial(middleware.handle, next_handler=handler)

        http_response = await handler(http_request)

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

    async def close(self) -> None:
        """Close the client and release resources asynchronously."""

    async def __aenter__(self) -> "BaseAsyncClient":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()
