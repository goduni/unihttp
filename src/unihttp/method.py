from dataclasses import dataclass, field
from types import get_original_bases
from typing import Any, ClassVar, TypeVar, get_args

from unihttp.http.request import HTTPRequest
from unihttp.http.response import HTTPResponse
from unihttp.serialize import RequestDumper, ResponseLoader

ResponseType = TypeVar("ResponseType", bound=Any)


@dataclass
class RequestMethod:
    """Base class for defining API methods.

    Attributes:
        __url__: The URL path pattern (e.g., "/users/{id}").
        __method__: The HTTP method (e.g., "GET").
    """

    __url__: ClassVar[str]
    __method__: ClassVar[str]

    def build_http_request(self, request_dumper: RequestDumper) -> HTTPRequest:
        """Convert this method instance into an HTTPRequest.

        Args:
            request_dumper: The dumper instance to use for serialization.

        Returns:
            HTTPRequest: The constructed HTTP request object.

        Raises:
            ValueError: if more than one of `raw`/`body`/`(form or file)` is set.
        """
        data = request_dumper.dump(self)

        header_data = data.get("header", {})
        path_data = data.get("path", {})
        query_data = data.get("query", {})
        body_data = data.get("body", {})
        file_data = data.get("file", {})
        form_data = data.get("form", {})
        raw_data = data.get("raw", None)

        if raw_data is not None and (body_data or form_data or file_data):
            raise ValueError(
                "Cannot use Raw with Body, Form or File. "
                "Raw is a standalone raw request body."
            )
        if body_data and (form_data or file_data):
            raise ValueError(
                "Cannot use Body with Form or File. "
                "Use Form for fields in multipart requests."
            )

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
            raw=raw_data,
        )

    def on_error(self, response: HTTPResponse) -> None:
        """Handle HTTP status errors for this specific method.

        Override to provide custom error handling for this endpoint.
        Called when response.ok is False.

        Args:
            response: The HTTP response with error status. For `StreamMethod`,
                only `status_code`/`headers` are available — the body is
                never buffered for a streamed response.

        Raises:
            Exception: propagate immediately
        """


@dataclass
class BaseMethod[ResponseType](RequestMethod):
    """Base class for API methods with a buffered, deserialized response.

    Subclasses represent specific API endpoints.
    Type parameter `ResponseType` specifies the expected return type.

    Attributes:
        __returning__: The type class of the response (automatically extracted
                       from generic type).
    """

    __returning__: ClassVar[type]

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        for base in get_original_bases(cls):
            origin = getattr(base, "__origin__", None)

            if origin is not None and issubclass(origin, BaseMethod):
                if args := get_args(base):
                    cls.__returning__ = args[0]
                break

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


@dataclass
class StreamMethod(RequestMethod):
    """Base class for defining streamed-response API methods.

    Subclasses represent endpoints whose response body is read incrementally
    (e.g. file downloads) rather than buffered and parsed. There is no
    `response_loader`/`make_response` step here: the body is never fully
    read, so there is nothing to deserialize.

    Attributes:
        __chunk_size__: Number of bytes to read per chunk.
    """

    __chunk_size__: int = field(default=65536, kw_only=True)
