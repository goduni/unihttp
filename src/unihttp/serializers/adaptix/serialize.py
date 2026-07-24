from typing import Any, TypeVar

from unihttp.http import UploadFile
from unihttp.markers import RawMarker
from unihttp.omitted import Omitted
from unihttp.serialize import RequestDumper, ResponseLoader
from unihttp.serializers.adaptix.marker_tools import for_marker
from unihttp.serializers.adaptix.provider import method_provider

from adaptix import Retort, as_sentinel, dumper
from adaptix._internal.morphing.generic_provider import TypeHintTagsUnwrappingProvider

T = TypeVar("T")

DEFAULT_RETORT = Retort(
    recipe=[
        as_sentinel(Omitted),
        TypeHintTagsUnwrappingProvider(),
        method_provider(),
        dumper(UploadFile, lambda x: x.to_tuple()),
        # bytes dumps to base64 by default, but here it must stay raw.
        dumper(for_marker(RawMarker), lambda x: x),
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
