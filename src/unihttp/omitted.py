from typing import Any, ClassVar, Self, TypeAlias, TypeVar


class SingletonMeta(type):
    _instances: ClassVar[dict[type, Any]] = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class Omitted(metaclass=SingletonMeta):
    def __repr__(self) -> str:
        return "<Omitted>"

    def __bool__(self) -> bool:
        return False

    def __copy__(self) -> Self:
        return self

    def __deepcopy__(self, memo: dict[int, Any]) -> Self:
        return self

    def __reduce__(self) -> tuple[type[Self], tuple[()]]:
        return (type(self), ())


T = TypeVar("T")
Omittable: TypeAlias = T | Omitted  # noqa: UP040
