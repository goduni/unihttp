from dataclasses import dataclass
from types import get_original_bases
from typing import Any, ClassVar, TypeVar, get_args

from unihttp.http.request import HTTPRequest
from unihttp.http.response import HTTPResponse
from unihttp.serialize import RequestDumper, ResponseLoader

ResponseType = TypeVar("ResponseType", bound=Any)


@dataclass
class BaseMethod[ResponseType]:
    """Base class for defining API methods.

    Subclasses represent specific API endpoints.
    Type parameter `ResponseType` specifies the expected return type.

    Attributes:
        __url__: The URL path pattern (e.g., "/users/{id}").
        __method__: The HTTP method (e.g., "GET").
        __returning__: The type class of the response (automatically extracted
                       from generic type).
    """
    __url__: ClassVar[str]
    __method__: ClassVar[str]

    __returning__: ClassVar[type]

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        for base in get_original_bases(cls):
            origin = getattr(base, "__origin__", None)

            if origin is not None and issubclass(origin, BaseMethod):
                if args := get_args(base):
                    cls.__returning__ = args[0]
                break

    def build_http_request(self, request_dumper: RequestDumper) -> HTTPRequest:
        """Convert this method instance into an HTTPRequest.

        Args:
            request_dumper: The dumper instance to use for serialization.

        Returns:
            HTTPRequest: The constructed HTTP request object.
        """
        data = request_dumper.dump(self)

        header_data = data.get("header", {})
        path_data = data.get("path", {})
        query_data = data.get("query", {})
        body_data = data.get("body", {})
        file_data = data.get("file", {})
        form_data = data.get("form", {})

        url = self.__url__.format(**path_data)

        return HTTPRequest(
            url=url,
            method=self.__method__,
            header=header_data,
            path=path_data,
            query=query_data,
            body=body_data,
            file=file_data,
            form=form_data,
        )

    def make_response(
            self,
            response: HTTPResponse,
            response_loader: ResponseLoader,
    ) -> ResponseType:
        """Convert an HTTPResponse into the declared ResponseType.

        Args:
            response: The HTTP response object.
            response_loader: The loader instance to use for deserialization.

        Returns:
            ResponseType: The deserialized response object.
        """
        return response_loader.load(response.data, self.__returning__)

    def validate_response(self, response: HTTPResponse) -> None:
        """Validate response BODY before deserialization.

        Override to handle APIs that return errors in body with 200 status.
        Called for ALL responses (including 200 OK).

        Args:
            response: The HTTP response to validate.

        Raises:
            Exception: if response body indicates an error
        """

    def on_error(self, response: HTTPResponse) -> None:
        """Handle HTTP status errors for this specific method.

        Override to provide custom error handling for this endpoint.
        Called when response.ok is False.

        Args:
             response: The HTTP response with error status.

        Raises:
            Exception: propagate immediately
        """
