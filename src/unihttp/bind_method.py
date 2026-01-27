import functools
import inspect
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, Generic, ParamSpec, TypeVar, cast, overload

from unihttp.method import BaseMethod

if TYPE_CHECKING:
    from unihttp.clients.base import BaseAsyncClient, BaseSyncClient


MethodParamSpec = ParamSpec("MethodParamSpec")
MethodResultT = TypeVar("MethodResultT")


class MethodBinder(Generic[MethodParamSpec, MethodResultT]):  # noqa: UP046
    __slots__ = ("_method_tp",)

    def __init__(
            self,
            method_tp: Callable[MethodParamSpec, BaseMethod[MethodResultT]],
    ) -> None:
        self._method_tp = method_tp

    @overload
    def __get__(
            self,
            instance: None,
            owner: type,
    ) -> "MethodBinder[MethodParamSpec, MethodResultT]":
        ...

    @overload
    def __get__(
            self,
            instance: "BaseSyncClient",
            owner: type,
    ) -> Callable[MethodParamSpec, MethodResultT]:
        ...

    @overload
    def __get__(
            self,
            instance: "BaseAsyncClient",
            owner: type,
    ) -> Callable[MethodParamSpec, Awaitable[MethodResultT]]:
        ...

    def __get__(
            self,
            instance: Any,
            owner: type | None = None,
    ) -> Any:
        if instance is None:
            return self

        if not hasattr(instance, "call_method"):
            raise RuntimeError(
                "`bind_method` is available only for classes with `call_method`",
            )

        call_method = instance.call_method
        method_tp = self._method_tp

        if inspect.iscoroutinefunction(call_method):
            @functools.wraps(method_tp)
            async def async_wrapper(
                    *args: MethodParamSpec.args,
                    **kwargs: MethodParamSpec.kwargs,
            ) -> MethodResultT:
                return cast(
                    MethodResultT,
                    await call_method(method_tp(*args, **kwargs)),
                )

            return async_wrapper

        @functools.wraps(method_tp)
        def sync_wrapper(
                *args: MethodParamSpec.args,
                **kwargs: MethodParamSpec.kwargs,
        ) -> MethodResultT:
            return cast(
                MethodResultT,
                call_method(method_tp(*args, **kwargs)),
            )

        return sync_wrapper


def bind_method(  # noqa: UP047
        method_tp: Callable[MethodParamSpec, BaseMethod[MethodResultT]],
) -> MethodBinder[MethodParamSpec, MethodResultT]:
    return MethodBinder(method_tp)
