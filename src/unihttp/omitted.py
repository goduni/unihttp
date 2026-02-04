from typing import Any, ClassVar, TypeAlias, TypeVar


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


T = TypeVar("T")
Omittable: TypeAlias = T | Omitted  # noqa: UP040
