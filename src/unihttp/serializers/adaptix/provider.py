from typing import Any

from unihttp.method import BaseMethod

from adaptix import Provider, bound
from adaptix._internal.morphing.name_layout.component import (
    BuiltinExtraMoveAndPoliciesMaker,
    BuiltinSievesMaker,
)
from adaptix._internal.morphing.name_layout.provider import BuiltinNameLayoutProvider
from adaptix._internal.provider.loc_stack_filtering import OriginSubclassLSC

from .marker_tools import DefaultMarkerFieldPathMaker, MarkerFieldPathMaker


class _MethodProvider(BuiltinNameLayoutProvider):
    def __init__(
            self,
            marker_path_maker: MarkerFieldPathMaker,
    ) -> None:
        super().__init__(
            sieves_maker=BuiltinSievesMaker(),
            structure_maker=marker_path_maker,
            extra_move_maker=BuiltinExtraMoveAndPoliciesMaker(),
            extra_policies_maker=BuiltinExtraMoveAndPoliciesMaker(),
        )


def method_provider(
        method_tp: type[BaseMethod[Any]] | None = None,
        marker_path_maker: MarkerFieldPathMaker | None = None,
) -> Provider:
    if method_tp is None:
        method_tp = BaseMethod

    if marker_path_maker is None:
        marker_path_maker = DefaultMarkerFieldPathMaker()

    return bound(
        OriginSubclassLSC(method_tp),
        _MethodProvider(marker_path_maker),
    )
