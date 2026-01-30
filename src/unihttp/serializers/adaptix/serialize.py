from typing import Any, TypeVar

from unihttp.http import UploadFile
from unihttp.serialize import RequestDumper, ResponseLoader
from unihttp.serializers.adaptix.fixed_tp_tags_unwrapping import (
    fixed_type_hint_tags_unwrapping_provider,
)
from unihttp.serializers.adaptix.provider import method_provider

from adaptix import Retort, dumper

T = TypeVar("T")

DEFAULT_RETORT = Retort(
    recipe=[
        fixed_type_hint_tags_unwrapping_provider(),
        method_provider(),
        dumper(UploadFile, lambda x: x.to_tuple()),
    ]
)


class AdaptixDumper(RequestDumper):
    def __init__(self, retort: Retort):
        self.retort = retort

    def dump(self, obj: Any) -> Any:
        return self.retort.dump(obj)


class AdaptixLoader(ResponseLoader):
    def __init__(self, retort: Retort):
        self.retort = retort

    def load(self, data: Any, tp: type[T]) -> T:
        return self.retort.load(data, tp)
