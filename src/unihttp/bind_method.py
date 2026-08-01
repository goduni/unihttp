import functools
import inspect
from collections.abc import Awaitable, Callable, Sequence
from typing import TYPE_CHECKING, Any, Generic, ParamSpec, TypeVar, Union, overload

from unihttp.http.response import HTTPResponse
from unihttp.http.stream import AsyncChunkStream, ChunkStream
from unihttp.method import BaseMethod, StreamMethod

if TYPE_CHECKING:
    from unihttp.clients.base import BaseAsyncClient, BaseSyncClient
    from unihttp.middlewares.base import AsyncMiddleware, Middleware


MethodParamSpec = ParamSpec("MethodParamSpec")
MethodResultT = TypeVar("MethodResultT")
SyncResultT = TypeVar("SyncResultT")
AsyncResultT = TypeVar("AsyncResultT")


class MethodBinder(Generic[MethodParamSpec, SyncResultT, AsyncResultT]):  # noqa: UP046
    __slots__ = ("_call_name", "_method_tp", "_middleware")

    def __init__(
        self,
        method_tp: Callable[MethodParamSpec, Any],
        call_name: str,
        middleware: Sequence[Union["Middleware", "AsyncMiddleware"]] | None = None,
    ) -> None:
        self._method_tp = method_tp
        self._call_name = call_name
        self._middleware = middleware

    @overload
    def __get__(
        self,
        instance: None,
        owner: type,
    ) -> "MethodBinder[MethodParamSpec, SyncResultT, AsyncResultT]": ...

    @overload
    def __get__(
        self,
        instance: "BaseSyncClient",
        owner: type,
    ) -> Callable[MethodParamSpec, SyncResultT]: ...

    @overload
    def __get__(
        self,
        instance: "BaseAsyncClient",
        owner: type,
    ) -> Callable[MethodParamSpec, Awaitable[AsyncResultT]]: ...

    def __get__(
        self,
        instance: Any,
        owner: type | None = None,
    ) -> Any:
        if instance is None:
            return self

        call_name = self._call_name
        if not hasattr(instance, call_name):
            raise RuntimeError(
                f"`bind_method` is available only for classes with `{call_name}`",
            )

        call = getattr(instance, call_name)
        method_tp = self._method_tp

        if inspect.iscoroutinefunction(call):

            @functools.wraps(method_tp)
            async def async_wrapper(
                *args: MethodParamSpec.args,
                **kwargs: MethodParamSpec.kwargs,
            ) -> Any:
                return await call(method_tp(*args, **kwargs), middleware=self._middleware)

            return async_wrapper

        @functools.wraps(method_tp)
        def sync_wrapper(
            *args: MethodParamSpec.args,
            **kwargs: MethodParamSpec.kwargs,
        ) -> Any:
            return call(method_tp(*args, **kwargs), middleware=self._middleware)

        return sync_wrapper


@overload
def bind_method(  # noqa: UP047
    method_tp: Callable[MethodParamSpec, BaseMethod[MethodResultT]],
    middleware: Sequence[Union["Middleware", "AsyncMiddleware"]] | None = None,
) -> MethodBinder[MethodParamSpec, MethodResultT, MethodResultT]: ...


@overload
def bind_method(  # noqa: UP047
    method_tp: Callable[MethodParamSpec, StreamMethod],
    middleware: Sequence[Union["Middleware", "AsyncMiddleware"]] | None = None,
) -> MethodBinder[
    MethodParamSpec, HTTPResponse[ChunkStream], HTTPResponse[AsyncChunkStream]
]: ...


def bind_method(
    method_tp: Callable[..., Any],
    middleware: Sequence[Union["Middleware", "AsyncMiddleware"]] | None = None,
) -> Any:
    if isinstance(method_tp, type) and issubclass(method_tp, StreamMethod):
        return MethodBinder(method_tp, "call_method_stream", middleware=middleware)
    return MethodBinder(method_tp, "call_method", middleware=middleware)
