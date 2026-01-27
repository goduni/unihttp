from typing import Any, Protocol, TypeVar

T = TypeVar("T")


class RequestDumper(Protocol):
    def dump(self, obj: Any) -> Any: ...


class ResponseLoader(Protocol):
    def load(self, data: Any, tp: type[T]) -> T: ...
